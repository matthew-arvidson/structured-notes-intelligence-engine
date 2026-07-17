"""
Persist node: upsert extracted fields to PostgreSQL via crud.upsert_note.

Input state keys:  cusip, extracted_fields, risk_findings, structure_tags,
                   risk_tier, note_type, baseline_deviations, source_file,
                   source_url, chunks_stored
Output state keys: db_record_id
"""

import logging
from backend.pipeline.state import NoteAnalysisState
from backend.db import crud

logger = logging.getLogger(__name__)


def run(state: NoteAnalysisState) -> dict:
    """
    Persist the analysis results to PostgreSQL.

    Non-fatal: if the DB write fails the pipeline state still contains all
    extracted data, so the report can still be generated. The error is logged
    and appended to state.errors.
    """
    errors: list[str] = list(state.get("errors", []))
    cusip = state.get("cusip", "")

    if not cusip:
        errors.append("persist: no CUSIP in state — skipping DB write")
        return {"db_record_id": None, "errors": errors}

    try:
        record_id = crud.upsert_note(
            cusip               = cusip,
            extracted_fields    = state.get("extracted_fields", {}),
            risk_findings       = state.get("risk_findings", []),
            baseline_deviations = state.get("baseline_deviations", []),
            structure_tags      = state.get("structure_tags", []),
            risk_tier           = state.get("risk_tier", "high"),
            note_type           = state.get("note_type", "Unknown"),
            source_file         = state.get("source_file", ""),
            source_url          = state.get("source_url", ""),
            chunks_stored       = state.get("chunks_stored", 0),
        )
        logger.info(f"[persist] Saved CUSIP={cusip} → db_record_id={record_id}")
        return {"db_record_id": record_id, "errors": errors}

    except Exception as exc:
        msg = f"persist: DB write failed for CUSIP={cusip} — {exc}"
        logger.exception(msg)
        errors.append(msg)
        return {"db_record_id": None, "errors": errors}
