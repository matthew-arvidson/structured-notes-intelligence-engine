"""
Triage node: classify note type + assign risk tier.

Phase 2: Implement LLM classification using CLASSIFY_PROMPT.
Phase 1: Stub that returns a placeholder until Phase 2.

Input state keys:  retrieved_chunks
Output state keys: note_type, structure_tags, tag_confidence, risk_tier
"""

import logging
from backend.pipeline.state import NoteAnalysisState

logger = logging.getLogger(__name__)


def run(state: NoteAnalysisState) -> dict:
    """
    Classify the note type and assign a risk tier.

    Risk tier logic (Phase 2 implementation):
      HIGH   — Worst-of basket, barrier < 60%, knock-in, equity delivery risk
      MEDIUM — Single-asset barrier, contingent coupon, autocallable
      LOW    — Principal protected, fixed coupon, no barrier

    TODO (Phase 2):
      - Embed retrieved chunk text and call CLASSIFY_PROMPT via LLM
      - Parse structure_tags + tag_confidence_scores from JSON response
      - Apply risk tier rules based on tags and extracted BarrierLevel
    """
    logger.info("[triage] Phase 1 stub — returns 'high' tier for all notes")
    return {
        "note_type": "Unknown",
        "structure_tags": [],
        "tag_confidence": {},
        "risk_tier": "high",    # default to HIGH in Phase 1 (safe — runs full pipeline)
    }
