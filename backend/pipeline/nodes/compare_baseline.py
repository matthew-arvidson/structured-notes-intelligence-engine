"""
Compare baseline node: check extracted fields against firm-standard baseline.

Uses standard_baseline.json — no LLM required for the rule-based checks.
LLM comparison may be added in Phase 3 for qualitative deviations.

Phase 2: Implement rule-based checks from standard_baseline.json.
Phase 1: Stub.

Input state keys:  extracted_fields
Output state keys: baseline_deviations, matches_baseline
"""

import logging
from backend.pipeline.state import NoteAnalysisState

logger = logging.getLogger(__name__)


def run(state: NoteAnalysisState) -> dict:
    """
    Compare extracted fields against firm baseline.

    TODO (Phase 2/3):
      - Load standard_baseline.json
      - Check BarrierLevel >= 0.60 (minimum acceptable)
      - Check required fields are present for the identified structure type
      - Check CallSettlementLag <= 5 business days
      - Flag CouponMemory absence for contingent coupon notes
      - Return list of {field, expected, actual, severity} deviation dicts
    """
    logger.info("[compare_baseline] Phase 1 stub")
    return {
        "baseline_deviations": [],
        "matches_baseline": True,
    }
