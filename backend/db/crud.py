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
from backend.db.models import Base, StructuredNote, NoteRiskFinding, NoteBaselineDeviation, NoteConflict, FieldReview

logger = logging.getLogger(__name__)


def create_tables() -> None:
    """Create all tables if they don't exist. Call once at startup."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("Database tables verified / created.")


def run_migrations() -> None:
    """
    Apply additive schema changes that create_all cannot handle on existing tables.
    Each statement is idempotent — safe to run on every startup.
    """
    import sqlalchemy
    engine = get_engine()
    migrations = [
        "ALTER TABLE structured_notes ADD COLUMN IF NOT EXISTS confidence_scores_json TEXT",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(sqlalchemy.text(sql))
                conn.commit()
                logger.info(f"[migration] Applied: {sql}")
            except Exception as exc:
                logger.warning(f"[migration] Skipped: {exc}")


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
    confidence_scores: dict | None = None,
    conflicts: list[dict] | None = None,
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
        def _field(*keys: str):
            """Try multiple key paths, including nested IssuerDetails, returning first non-null value."""
            for key in keys:
                if "." in key:
                    parts = key.split(".", 1)
                    parent = extracted_fields.get(parts[0])
                    if isinstance(parent, dict):
                        val = parent.get(parts[1])
                        if val not in (None, "", "null"):
                            return val
                else:
                    val = extracted_fields.get(key)
                    if val not in (None, "", "null"):
                        return val
            return None

        note.isin             = _field("ISIN", "IssuerDetails.ISIN", "SecurityIdentifier.ISIN",
                                       "Other.SecurityIdentifier.ISIN")
        note.issuer           = _field("Issuer", "IssuerDetails.Issuer")
        note.guarantor        = _field("Guarantor", "IssuerDetails.Guarantor")
        note.trade_date       = _field("TradeDate", "IssuerDetails.TradeDate")
        note.settlement_date  = _field("SettlementDate", "IssuerDetails.SettlementDate")
        note.maturity_date    = _field("MaturityDate", "IssuerDetails.MaturityDate")

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
        note.extracted_fields_json  = json.dumps(extracted_fields)
        note.confidence_scores_json = json.dumps(confidence_scores) if confidence_scores else None

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

        # Replace conflicts
        session.query(NoteConflict).filter_by(note_id=note_id).delete()
        for conflict in (conflicts or []):
            fields_involved = conflict.get("fields_involved", [])
            session.add(NoteConflict(
                note_id        = note_id,
                issue          = conflict.get("issue", ""),
                fields_involved= json.dumps(fields_involved) if isinstance(fields_involved, list) else fields_involved,
                severity       = conflict.get("severity", "medium"),
                recommendation = conflict.get("recommendation", ""),
            ))

        session.commit()
        logger.info(f"[crud] Committed note id={note_id} with {len(risk_findings)} findings")
        return note_id


def get_note_by_cusip(cusip: str) -> StructuredNote | None:
    """Fetch a single note by CUSIP (no relationships loaded). Returns None if not found."""
    engine = get_engine()
    with Session(engine) as session:
        return session.query(StructuredNote).filter_by(cusip=cusip).first()


def upsert_field_review(cusip: str, field: str, state: str | None) -> bool:
    """
    Set or clear the analyst review state for a single extracted field.

    state='accepted' — analyst confirmed the extraction is correct
    state='flagged'  — analyst flagged for further review
    state=None       — clears the review (back to unreviewed)

    Returns False if the note CUSIP is not found.
    """
    engine = get_engine()
    with Session(engine) as session:
        note = session.query(StructuredNote).filter_by(cusip=cusip).first()
        if note is None:
            return False

        review = session.query(FieldReview).filter_by(note_id=note.id, field=field).first()

        if state is None:
            if review:
                session.delete(review)
        else:
            if review:
                review.state = state
            else:
                session.add(FieldReview(note_id=note.id, field=field, state=state))

        session.commit()
        logger.info(f"[crud] Field review: CUSIP={cusip} field={field} state={state}")
        return True


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
        conflicts = session.query(NoteConflict).filter_by(note_id=note.id).all()
        reviews = session.query(FieldReview).filter_by(note_id=note.id).all()

        extracted_fields = {}
        if note.extracted_fields_json:
            try:
                extracted_fields = json.loads(note.extracted_fields_json)
            except json.JSONDecodeError:
                pass

        confidence_scores = {}
        if note.confidence_scores_json:
            try:
                confidence_scores = json.loads(note.confidence_scores_json)
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
            "confidence_scores":         confidence_scores,
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
            "conflicts": [
                {
                    "issue":           c.issue,
                    "fields_involved": json.loads(c.fields_involved) if c.fields_involved else [],
                    "severity":        c.severity,
                    "recommendation":  c.recommendation,
                }
                for c in conflicts
            ],
            "field_reviews": {r.field: r.state for r in reviews},
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
