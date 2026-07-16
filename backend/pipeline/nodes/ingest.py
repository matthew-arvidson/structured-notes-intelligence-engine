"""
Ingest node: PDF → chunks → embeddings → ChromaDB upsert.

Phase 1: Fully implemented.
This is the foundation of the RAG pipeline — must work before any other node.

Input state keys:  cusip, pdf_path (or source_url)
Output state keys: chunks_stored, source_file, errors (appended)
"""

import logging
from backend.pipeline.state import NoteAnalysisState
from backend.tools.pdf_parser import parse_pdf
from backend.tools.embedder import embed_chunks
from backend.tools.chroma_client import get_collection, delete_by_cusip

logger = logging.getLogger(__name__)


def run(state: NoteAnalysisState) -> dict:
    """
    Parse a term sheet PDF, embed the chunks, and upsert to ChromaDB.

    Re-ingestion of the same CUSIP is idempotent — existing chunks are
    replaced (delete then upsert) so the collection stays clean.
    """
    cusip = state["cusip"]
    pdf_path = state.get("pdf_path", "")
    errors: list[str] = list(state.get("errors", []))

    if not pdf_path:
        errors.append("ingest: no pdf_path provided in state")
        return {"chunks_stored": 0, "errors": errors}

    try:
        # Parse PDF into section-aware chunks
        logger.info(f"[ingest] Parsing PDF for CUSIP={cusip}: {pdf_path}")
        chunks = parse_pdf(pdf_path)
        logger.info(f"[ingest] {len(chunks)} chunks extracted")

        # Remove any previous version of this note from ChromaDB
        removed = delete_by_cusip(cusip)
        if removed:
            logger.info(f"[ingest] Removed {removed} stale chunks for CUSIP={cusip}")

        # Embed and upsert
        records = embed_chunks(
            chunks=chunks,
            cusip=cusip,
            issuer=state.get("extracted_fields", {}).get("Issuer", ""),
            settlement_date=state.get("extracted_fields", {}).get("SettlementDate", ""),
        )

        collection = get_collection()
        collection.upsert(
            ids=[r["id"] for r in records],
            embeddings=[r["embedding"] for r in records],
            documents=[r["document"] for r in records],
            metadatas=[r["metadata"] for r in records],
        )

        source_file = chunks[0].source_file if chunks else ""
        logger.info(f"[ingest] Upserted {len(records)} chunks to ChromaDB")
        return {
            "chunks_stored": len(records),
            "source_file": source_file,
            "errors": errors,
        }

    except FileNotFoundError as exc:
        msg = f"ingest: {exc}"
        logger.error(msg)
        errors.append(msg)
        return {"chunks_stored": 0, "errors": errors}

    except Exception as exc:
        msg = f"ingest: unexpected error — {exc}"
        logger.exception(msg)
        errors.append(msg)
        return {"chunks_stored": 0, "errors": errors}
