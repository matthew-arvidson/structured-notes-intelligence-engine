"""
Confidence node: per-field confidence scoring + conflict detection.

Implements Prompts_v2 steps 3 (CONFIDENCE_PROMPT) and 4 (CONFLICTS_PROMPT).
This is the step that was designed in structured-notes-final but never wired.

Phase 3: Implement LLM confidence + conflict detection.
Phase 1: Stub.

Input state keys:  extracted_fields, structure_tags, tag_confidence
Output state keys: confidence_scores, conflicts
"""

import logging
from backend.pipeline.state import NoteAnalysisState

logger = logging.getLogger(__name__)


def run(state: NoteAnalysisState) -> dict:
    """
    Score confidence for each extracted field and detect structural conflicts.

    TODO (Phase 3):
      - Call LLM with CONFIDENCE_PROMPT → dict of field: score
      - Call LLM with CONFLICTS_PROMPT → list of conflict dicts
      - Flag any field scoring < 90 in errors for analyst review
    """
    logger.info("[confidence] Phase 1 stub")
    return {
        "confidence_scores": {},
        "conflicts": [],
    }
