"""
CRUD operations for Azure PostgreSQL.

Design: typed column updates only — no dynamic SQL from LLM-provided keys.
All writes go through explicit ORM fields. The raw extracted JSON is stored
as-is in extracted_fields_json for auditability and schema flexibility.
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

    On re-ingestion of the same CUSIP:
      - Core fields and JSON payload are updated in place
      - Risk findings and baseline deviations are deleted and re-inserted
        (simpler than diffing them)
    """
    engine = get_engine()

    # Helper to safely parse a float from extracted fields
    def _float(key: str) -> float | None:
        val = extracted_fields.get(key)
        if val is None:
            return None
        try:
            return float(str(val).replace("%", "").strip())
        except (ValueError, TypeError):
            return None

    def _bool(key: str) -> bool:
        val = extracted_fields.get(key)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "yes", "1")
        return False

    with Session(engine) as session:
        # Check for existing record
        note = session.query(StructuredNote).filter_by(cusip=cusip).first()

        if note is None:
            note = StructuredNote(cusip=cusip)
            session.add(note)
            logger.info(f"[crud] Creating new record for CUSIP={cusip}")
        else:
            logger.info(f"[crud] Updating existing record id={note.id} for CUSIP={cusip}")

        # Update typed identity columns
        note.isin             = extracted_fields.get("ISIN") or extracted_fields.get("SecurityIdentifier", {}).get("ISIN") if isinstance(extracted_fields.get("SecurityIdentifier"), dict) else extracted_fields.get("ISIN")
        note.issuer           = extracted_fields.get("Issuer")
        note.guarantor        = extracted_fields.get("Guarantor")
        note.trade_date       = extracted_fields.get("TradeDate")
        note.settlement_date  = extracted_fields.get("SettlementDate")
        note.maturity_date    = extracted_fields.get("MaturityDate")

        # Classification
        note.note_type        = note_type
        note.structure_tags   = json.dumps(structure_tags)
        note.risk_tier        = risk_tier

        # Key risk fields — typed for dashboard filtering
        note.barrier_level             = _float("BarrierLevel")
        note.principal_protection_pct  = _float("PrincipalProtectionPercentage")
        note.has_worst_of              = "Worst-of" in structure_tags or _bool("WorstOf")
        note.has_memory_coupon         = "Memory Feature" in structure_tags or _bool("CouponMemory")

        # Full extraction payload (for audit and future schema evolution)
        note.extracted_fields_json = json.dumps(extracted_fields)

        # Source metadata
        note.source_file    = source_file
        note.source_url     = source_url
        note.chunks_stored  = chunks_stored

        # Flush to get the primary key before inserting related rows
        session.flush()
        note_id = note.id

        # Replace risk findings
        session.query(NoteRiskFinding).filter_by(note_id=note_id).delete()
        for finding in risk_findings:
            session.add(NoteRiskFinding(
                note_id       = note_id,
                term          = finding.get("term", ""),
                category      = finding.get("category", ""),
                severity      = finding.get("severity", "medium"),
                note_text     = finding.get("note", ""),
                excerpt       = finding.get("excerpt", ""),
                source_section= finding.get("section", ""),
            ))

        # Replace baseline deviations
        session.query(NoteBaselineDeviation).filter_by(note_id=note_id).delete()
        for dev in baseline_deviations:
            session.add(NoteBaselineDeviation(
                note_id  = note_id,
                field    = dev.get("field", ""),
                expected = str(dev.get("expected", "")),
                actual   = str(dev.get("actual", "")),
                severity = dev.get("severity", "medium"),
            ))

        session.commit()
        logger.info(f"[crud] Committed note id={note_id} with {len(risk_findings)} findings")
        return note_id


def get_note_by_cusip(cusip: str) -> StructuredNote | None:
    """Fetch a single note by CUSIP (no relationships loaded). Returns None if not found."""
    engine = get_engine()
    with Session(engine) as session:
        return session.query(StructuredNote).filter_by(cusip=cusip).first()


def get_note_detail(cusip: str) -> dict | None:
    """
    Fetch a note with all related records serialized within the session.

    Returns a fully-serialized dict so callers don't need an open session.
    Includes risk_findings and baseline_deviations from the DB.
    """
    engine = get_engine()
    with Session(engine) as session:
        note = session.query(StructuredNote).filter_by(cusip=cusip).first()
        if note is None:
            return None

        findings = session.query(NoteRiskFinding).filter_by(note_id=note.id).all()
        deviations = session.query(NoteBaselineDeviation).filter_by(note_id=note.id).all()

        extracted_fields = {}
        if note.extracted_fields_json:
            try:
                extracted_fields = json.loads(note.extracted_fields_json)
            except json.JSONDecodeError:
                pass

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
            "extracted_fields":         extracted_fields,
            "risk_findings": [
                {
                    "term":           f.term,
                    "category":       f.category,
                    "severity":       f.severity,
                    "note":           f.note_text,
                    "excerpt":        f.excerpt,
                    "source_section": f.source_section,
                }
                for f in findings
            ],
            "baseline_deviations": [
                {
                    "field":    d.field,
                    "expected": d.expected,
                    "actual":   d.actual,
                    "severity": d.severity,
                }
                for d in deviations
            ],
        }


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
