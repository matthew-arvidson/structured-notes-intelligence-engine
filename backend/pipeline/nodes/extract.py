"""
Extract node: structured field extraction from retrieved chunks.

Three modes controlled by risk_tier (set in triage node):
  full  — full UEQSN schema (~40 fields), called for HIGH tier
  core  — core identity + risk fields (~15 fields), called for MEDIUM tier
  meta  — basic identity only (~6 fields), called for LOW tier

Phase 2: Implement LLM extraction using EXTRACT_PROMPT / EXTRACT_CORE_PROMPT / EXTRACT_META_PROMPT.
Phase 1: Stub.

Input state keys:  retrieved_chunks
Output state keys: extracted_fields
"""

import logging
from backend.pipeline.state import NoteAnalysisState

logger = logging.getLogger(__name__)


def run(state: NoteAnalysisState, mode: str = "full") -> dict:
    """
    Extract structured fields from retrieved chunks.

    TODO (Phase 2):
      - Concatenate retrieved_chunks texts into a prompt context window
      - Select prompt based on mode (EXTRACT_PROMPT / EXTRACT_CORE_PROMPT / EXTRACT_META_PROMPT)
      - Call LLM with structured output (Pydantic model or json_mode)
      - Parse and validate the returned JSON against UEQSN_schema.json
      - Handle partial extraction gracefully — log missing fields, don't raise
    """
    logger.info(f"[extract] Phase 1 stub — mode={mode}")
    return {
        "extracted_fields": {
            "_stub": True,
            "_mode": mode,
            "_chunks_available": len(state.get("retrieved_chunks", [])),
        }
    }
