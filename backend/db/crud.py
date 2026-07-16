"""
CRUD operations for Azure SQL.

Design: typed column updates only — no dynamic SQL from LLM-provided keys.
All writes go through explicit ORM fields. The raw extracted JSON is stored
as-is in extracted_fields_json for auditability.

Phase 2: Implement and test upsert_note.
Phase 1: Stub functions defined.
"""

import json
import logging
from sqlalchemy.orm import Session
from backend.db.engine import get_engine
from backend.db.models import Base, StructuredNote, NoteRiskFinding, NoteBaselineDeviation

logger = logging.getLogger(__name__)


def create_tables() -> None:
    """Create all tables if they don't exist. Call once at startup."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("Database tables verified / created.")


def upsert_note(
    cusip: str,
    extracted_fields: dict,
    risk_findings: list[dict],
    baseline_deviations: list[dict],
    structure_tags: list[str],
    risk_tier: str,
    note_type: str,
    source_file: str = "",
    source_url: str = "",
    chunks_stored: int = 0,
) -> int:
    """
    Upsert a structured note and its related records.
    Returns the database primary key.

    TODO (Phase 2):
      - Open a session via get_engine()
      - Check for existing record by CUSIP
      - Update typed columns from extracted_fields (CUSIP, Issuer, dates, BarrierLevel, etc.)
      - Delete and re-insert NoteRiskFinding and NoteBaselineDeviation rows
      - Commit and return the record id
    """
    logger.info(f"[crud] upsert_note stub — CUSIP={cusip}")
    return -1   # placeholder


def get_note_by_cusip(cusip: str) -> StructuredNote | None:
    """Fetch a single note by CUSIP. Returns None if not found."""
    engine = get_engine()
    with Session(engine) as session:
        return session.query(StructuredNote).filter_by(cusip=cusip).first()


def list_notes(
    issuer: str | None = None,
    settlement_date: str | None = None,
    risk_tier: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[StructuredNote]:
    """List notes with optional filters. Used by the dashboard API."""
    engine = get_engine()
    with Session(engine) as session:
        q = session.query(StructuredNote)
        if issuer:
            q = q.filter(StructuredNote.issuer.ilike(f"%{issuer}%"))
        if settlement_date:
            q = q.filter(StructuredNote.settlement_date == settlement_date)
        if risk_tier:
            q = q.filter(StructuredNote.risk_tier == risk_tier)
        return q.order_by(StructuredNote.updated_at.desc()).offset(offset).limit(limit).all()
