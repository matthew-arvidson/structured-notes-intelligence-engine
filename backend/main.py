"""
FastAPI entry point for the Structured Notes Intelligence Engine.

Run:
    uvicorn backend.main:app --reload --port 3001

Phase 1: Health check + basic structure.
Phase 2: Add /api/ingest and /api/notes routes.
Phase 4: Add /api/query (semantic search) and /api/notes/{cusip}/report.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import ALLOWED_ORIGINS, LOG_LEVEL
from backend.tools.chroma_client import health_check as chroma_health

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Structured Notes Intelligence Engine starting up...")
    # Phase 2: add db.crud.create_tables() here
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Structured Notes Intelligence Engine",
    description="RAG-powered structured note analysis with LangGraph orchestration.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,        # set True only if session cookies are needed
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["system"])
async def health():
    """Ping ChromaDB and return service status."""
    chroma_status = chroma_health()
    return {
        "service": "structured-notes-intelligence-engine",
        "status": "ok" if chroma_status["status"] == "ok" else "degraded",
        "chromadb": chroma_status,
    }


# ─── Placeholder routes (Phase 2+) ────────────────────────────────────────────

@app.get("/api/notes", tags=["notes"])
async def list_notes():
    """Phase 2: List / filter structured notes from Azure SQL."""
    return {"message": "Not yet implemented — Phase 2"}


@app.get("/api/notes/{cusip}", tags=["notes"])
async def get_note(cusip: str):
    """Phase 2: Get a single note by CUSIP."""
    return {"message": f"Not yet implemented — Phase 2", "cusip": cusip}


@app.post("/api/ingest/upload", tags=["ingest"])
async def ingest_upload():
    """Phase 2: Upload a PDF term sheet and run the analysis pipeline."""
    return {"message": "Not yet implemented — Phase 2"}


@app.post("/api/ingest/url", tags=["ingest"])
async def ingest_url():
    """Phase 2: Scrape a URL and run the analysis pipeline."""
    return {"message": "Not yet implemented — Phase 2"}


@app.post("/api/query", tags=["search"])
async def semantic_query():
    """Phase 4: Natural language → ChromaDB semantic search across all notes."""
    return {"message": "Not yet implemented — Phase 4"}


@app.get("/api/notes/{cusip}/report", tags=["notes"])
async def get_report(cusip: str):
    """Phase 4: Retrieve the analyst report for a note."""
    return {"message": "Not yet implemented — Phase 4", "cusip": cusip}


@app.get("/api/audit/{cusip}", tags=["audit"])
async def audit_note(cusip: str):
    """Phase 4: Booking system vs Azure SQL reconciliation."""
    return {"message": "Not yet implemented — Phase 4", "cusip": cusip}
