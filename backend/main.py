"""
FastAPI entry point for the Structured Notes Intelligence Engine.

Run:
    uvicorn backend.main:app --reload --port 3001
"""

import logging
import json
import tempfile
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.config import ALLOWED_ORIGINS, LOG_LEVEL
from backend.tools.chroma_client import health_check as chroma_health
from backend.db.engine import ping as db_ping
from backend.db import crud
from backend.pipeline.graph import note_analysis_graph

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: ensure DB tables exist."""
    logger.info("Structured Notes Intelligence Engine starting up...")
    try:
        crud.create_tables()
        logger.info("Database tables ready.")
    except Exception as exc:
        logger.error(f"Startup DB table creation failed: {exc}")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Structured Notes Intelligence Engine",
    description="RAG-powered structured note analysis with LangGraph orchestration.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["system"])
async def health():
    """Ping ChromaDB and PostgreSQL, return service status."""
    chroma_status = chroma_health()
    db_ok = db_ping()
    overall = "ok" if chroma_status["status"] == "ok" and db_ok else "degraded"
    return {
        "service": "structured-notes-intelligence-engine",
        "status": overall,
        "chromadb": chroma_status,
        "database": {"status": "ok" if db_ok else "error"},
    }


# ─── Ingest ───────────────────────────────────────────────────────────────────

@app.post("/api/ingest/upload", tags=["ingest"])
async def ingest_upload(
    file: UploadFile = File(...),
    cusip: str = Form(...),
):
    """
    Upload a PDF term sheet and run the full analysis pipeline.

    Returns the pipeline result including extracted fields, risk findings,
    and the database record ID.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Save upload to a temp file so the pipeline can read it from disk
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        logger.info(f"[ingest] Running pipeline for CUSIP={cusip} file={file.filename}")
        result = note_analysis_graph.invoke({
            "cusip": cusip,
            "pdf_path": tmp_path,
            "errors": [],
        })
    finally:
        os.unlink(tmp_path)

    confidence_scores = result.get("confidence_scores", {})
    low_confidence = [f for f, s in confidence_scores.items() if isinstance(s, (int, float)) and s < 90]

    return {
        "cusip":               cusip,
        "status":              "ok" if not result.get("errors") else "completed_with_errors",
        "note_type":           result.get("note_type"),
        "risk_tier":           result.get("risk_tier"),
        "structure_tags":      result.get("structure_tags", []),
        "chunks_stored":       result.get("chunks_stored", 0),
        "db_record_id":        result.get("db_record_id"),
        "fields_extracted":    len(result.get("extracted_fields", {})),
        "risk_findings":       len(result.get("risk_findings", [])),
        "baseline_deviations": result.get("baseline_deviations", []),
        "matches_baseline":    result.get("matches_baseline", True),
        "conflicts":           result.get("conflicts", []),
        "low_confidence_fields": low_confidence,
        "report_path":         result.get("report_path"),
        "errors":              result.get("errors", []),
    }


@app.post("/api/ingest/url", tags=["ingest"])
async def ingest_url():
    """Phase 4: Scrape a URL and run the analysis pipeline."""
    return {"message": "Not yet implemented — Phase 4"}


# ─── Notes ────────────────────────────────────────────────────────────────────

@app.get("/api/notes", tags=["notes"])
async def list_notes(
    issuer: str | None = Query(default=None),
    settlement_date: str | None = Query(default=None),
    risk_tier: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
):
    """List structured notes with optional filters."""
    notes = crud.list_notes(
        issuer=issuer,
        settlement_date=settlement_date,
        risk_tier=risk_tier,
        limit=limit,
        offset=offset,
    )
    return {
        "count": len(notes),
        "notes": [_note_to_dict(n) for n in notes],
    }


@app.get("/api/notes/{cusip}", tags=["notes"])
async def get_note(cusip: str):
    """Get a single note by CUSIP including extracted fields, risk findings, and baseline deviations."""
    detail = crud.get_note_detail(cusip)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Note with CUSIP {cusip} not found.")
    return detail


# ─── Semantic search + audit (Phase 4) ────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    cusip: str | None = None
    n_results: int = 5


@app.post("/api/query", tags=["search"])
async def semantic_query(request: QueryRequest):
    """
    Natural language query across all ingested notes via RAG.

    Body: {"question": "...", "cusip": "optional filter", "n_results": 5}

    Embeds the question, retrieves top-k chunks from ChromaDB,
    then asks the LLM to answer using only the retrieved context.
    Returns the answer + source citations so every claim is traceable.
    """
    from backend.tools.chroma_client import get_collection
    from backend.tools.llm_client import get_chat_llm
    from langchain_openai import AzureOpenAIEmbeddings
    from backend.config import (
        AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY,
        AZURE_OPENAI_API_VERSION, AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    )

    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="'question' field is required.")

    cusip_filter = request.cusip
    n_results = min(request.n_results, 20)

    # ── Embed the question ────────────────────────────────────────────────────
    embedder = AzureOpenAIEmbeddings(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    )
    query_embedding = embedder.embed_query(question)

    # ── Retrieve from ChromaDB ────────────────────────────────────────────────
    collection = get_collection()
    where = {"cusip": cusip_filter} if cusip_filter else None
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not docs:
        return {
            "question": question,
            "answer": "No relevant content found in the ingested notes.",
            "sources": [],
        }

    # ── Build context block ───────────────────────────────────────────────────
    context_parts = []
    sources = []
    for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances), start=1):
        cusip = meta.get("cusip", "unknown")
        section = meta.get("section", "")
        page = meta.get("page", "")
        context_parts.append(f"[{i}] CUSIP={cusip} | Section={section} | Page={page}\n{doc}")
        sources.append({
            "rank":      i,
            "cusip":     cusip,
            "section":   section,
            "page":      page,
            "relevance": round(1 - float(dist), 3),
            "excerpt":   doc[:200],
        })

    context = "\n\n---\n\n".join(context_parts)

    # ── LLM answer ────────────────────────────────────────────────────────────
    system_msg = (
        "You are a structured product analyst. Answer the user's question using ONLY "
        "the retrieved term sheet excerpts below. Cite your sources using [1], [2] etc. "
        "If the answer cannot be found in the context, say so explicitly. "
        "Be concise and precise — this is for internal analyst use."
    )
    user_msg = f"Question: {question}\n\nContext:\n{context}"

    llm = get_chat_llm()
    response = llm.invoke([
        {"role": "system", "content": system_msg},
        {"role": "user",   "content": user_msg},
    ])

    return {
        "question": question,
        "answer":   response.content.strip(),
        "sources":  sources,
    }


@app.get("/api/notes/{cusip}/report", tags=["notes"])
async def get_report(cusip: str):
    """Return the markdown analyst report for a note, reading from disk if available."""
    from pathlib import Path
    detail = crud.get_note_detail(cusip)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Note with CUSIP {cusip} not found.")

    # Look for a pre-generated report on disk
    safe_cusip = "".join(c for c in cusip if c.isalnum() or c in "-_")
    report_path = Path(__file__).parent.parent / "output" / f"{safe_cusip}_report.md"
    if report_path.exists():
        return {"cusip": cusip, "report": report_path.read_text(encoding="utf-8")}

    return {"cusip": cusip, "report": None, "message": "Report not yet generated — ingest the note to produce one."}


@app.get("/api/audit/{cusip}", tags=["audit"])
async def audit_note(cusip: str):
    """Phase 4: Booking system vs PostgreSQL reconciliation."""
    return {"message": "Not yet implemented — Phase 4", "cusip": cusip}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _note_to_dict(note) -> dict:
    """Serialize a StructuredNote ORM object to a JSON-safe dict."""
    return {
        "id":                       note.id,
        "cusip":                    note.cusip,
        "isin":                     note.isin,
        "issuer":                   note.issuer,
        "guarantor":                note.guarantor,
        "trade_date":               note.trade_date,
        "settlement_date":          note.settlement_date,
        "maturity_date":            note.maturity_date,
        "note_type":                note.note_type,
        "structure_tags":           note.get_structure_tags(),
        "risk_tier":                note.risk_tier,
        "barrier_level":            note.barrier_level,
        "principal_protection_pct": note.principal_protection_pct,
        "has_worst_of":             note.has_worst_of,
        "has_memory_coupon":        note.has_memory_coupon,
        "source_file":              note.source_file,
        "chunks_stored":            note.chunks_stored,
        "created_at":               note.created_at.isoformat() if note.created_at else None,
        "updated_at":               note.updated_at.isoformat() if note.updated_at else None,
    }
