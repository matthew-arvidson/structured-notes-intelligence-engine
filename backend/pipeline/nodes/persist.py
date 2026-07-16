"""
Persist node: upsert extracted fields to Azure SQL.

Phase 2: Implement SQLAlchemy upsert using db/crud.py.
Phase 1: Stub.

Input state keys:  cusip, extracted_fields, risk_findings, structure_tags,
                   confidence_scores, baseline_deviations, source_file
Output state keys: db_record_id
"""

import logging
from backend.pipeline.state import NoteAnalysisState

logger = logging.getLogger(__name__)


def run(state: NoteAnalysisState) -> dict:
    """
    Persist the analysis results to Azure SQL.

    TODO (Phase 2):
      - Use db/crud.upsert_note() to write extracted_fields to StructuredNotes table
      - Write risk_findings to a NoteRiskFindings table
      - Write baseline_deviations to a NoteBaselineDeviations table
      - Write confidence_scores + conflicts to NoteConfidence table
      - Return the Azure SQL primary key as db_record_id
    """
    logger.info(f"[persist] Phase 1 stub — CUSIP={state.get('cusip')}")
    return {"db_record_id": None}
