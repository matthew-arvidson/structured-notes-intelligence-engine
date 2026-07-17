"""
Confidence node: per-field confidence scoring + conflict detection.

Implements Prompts_v2 steps 3 (CONFIDENCE_PROMPT) and 4 (CONFLICTS_PROMPT).
Two sequential LLM calls — both are non-fatal if they fail.

Input state keys:  extracted_fields, structure_tags, tag_confidence
Output state keys: confidence_scores, conflicts
"""

import json
import logging
from backend.pipeline.state import NoteAnalysisState
from backend.tools.llm_client import get_chat_llm
from backend.domain.prompts import CONFIDENCE_PROMPT, CONFLICTS_PROMPT

logger = logging.getLogger(__name__)


def _call_llm(prompt: str) -> str:
    """Make a single LLM call and return the raw content string."""
    llm = get_chat_llm()
    response = llm.invoke([
        {"role": "system", "content": "You are a structured product analyst. Return only valid JSON, no commentary."},
        {"role": "user", "content": prompt},
    ])
    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


def run(state: NoteAnalysisState) -> dict:
    """
    Score per-field confidence and detect structural conflicts.

    Step 3 (CONFIDENCE_PROMPT): returns {field: score} for all non-null fields.
    Step 4 (CONFLICTS_PROMPT): returns [{issue, fields_involved, severity}].

    Both calls are independent — if one fails the other still runs.
    Low-confidence fields (< 90) are logged for analyst review.
    """
    errors: list[str] = list(state.get("errors", []))
    fields = state.get("extracted_fields", {})
    tags = state.get("structure_tags", [])

    if not fields:
        logger.info("[confidence] No extracted fields — skipping")
        return {"confidence_scores": {}, "conflicts": [], "errors": errors}

    # Only include non-null fields to keep the prompt lean
    non_null = {k: v for k, v in fields.items() if v is not None}
    fields_json = json.dumps(non_null, indent=2)
    tags_str = ", ".join(tags) if tags else "Unknown"

    # ── Step 3: Confidence Scoring ────────────────────────────────────────────
    confidence_scores: dict[str, int] = {}
    try:
        prompt = CONFIDENCE_PROMPT.format(
            extracted_features_json=fields_json,
            structure_tags=tags_str,
        )
        raw = _call_llm(prompt)
        confidence_scores = json.loads(raw)

        low_confidence = [f for f, s in confidence_scores.items() if isinstance(s, int) and s < 90]
        if low_confidence:
            logger.warning(f"[confidence] Low-confidence fields (<90): {low_confidence}")

        logger.info(f"[confidence] Scored {len(confidence_scores)} fields for CUSIP={state.get('cusip')}")

    except json.JSONDecodeError as exc:
        msg = f"confidence: CONFIDENCE_PROMPT returned invalid JSON — {exc}"
        logger.error(msg)
        errors.append(msg)
    except Exception as exc:
        msg = f"confidence: CONFIDENCE_PROMPT failed — {exc}"
        logger.exception(msg)
        errors.append(msg)

    # ── Step 4: Conflict Detection ────────────────────────────────────────────
    conflicts: list[dict] = []
    try:
        prompt = CONFLICTS_PROMPT.format(
            extracted_features_json=fields_json,
            structure_tags=tags_str,
            confidence_scores_json=json.dumps(confidence_scores),
        )
        raw = _call_llm(prompt)
        conflicts = json.loads(raw)

        if not isinstance(conflicts, list):
            conflicts = []

        high_conflicts = [c for c in conflicts if c.get("severity") == "high"]
        if high_conflicts:
            logger.warning(f"[confidence] {len(high_conflicts)} HIGH severity conflicts detected")

        logger.info(f"[confidence] {len(conflicts)} conflicts for CUSIP={state.get('cusip')}")

    except json.JSONDecodeError as exc:
        msg = f"confidence: CONFLICTS_PROMPT returned invalid JSON — {exc}"
        logger.error(msg)
        errors.append(msg)
    except Exception as exc:
        msg = f"confidence: CONFLICTS_PROMPT failed — {exc}"
        logger.exception(msg)
        errors.append(msg)

    return {
        "confidence_scores": confidence_scores,
        "conflicts": conflicts,
        "errors": errors,
    }
