"""
Triage node: classify note type + assign risk tier.

Calls the LLM with CLASSIFY_PROMPT on the retrieved chunk text to produce
structure_tags + tag_confidence, then derives risk_tier from the tags using
deterministic rules (no LLM involved in tier assignment).

Input state keys:  retrieved_chunks
Output state keys: note_type, structure_tags, tag_confidence, risk_tier
"""

import json
import logging
from backend.pipeline.state import NoteAnalysisState
from backend.tools.llm_client import get_chat_llm
from backend.domain.prompts import CLASSIFY_PROMPT

logger = logging.getLogger(__name__)

# Tags that drive HIGH risk tier (any match → high)
_HIGH_TAGS = {
    "Worst-of", "Knock-In", "Principal-at-Risk", "Equity Delivery",
    "Worst-of Basket",
}

# Tags that drive MEDIUM tier if no HIGH tag is present
_MEDIUM_TAGS = {
    "Auto-callable", "AutoCallable", "Contingent Coupon", "Memory Feature",
    "Barrier", "Reverse Convertible",
}


def _derive_risk_tier(tags: list[str]) -> str:
    """Deterministic risk tier from classification tags — no LLM involved."""
    tag_set = {t.strip() for t in tags}
    if tag_set & _HIGH_TAGS:
        return "high"
    if tag_set & _MEDIUM_TAGS:
        return "medium"
    return "low"


def run(state: NoteAnalysisState) -> dict:
    """
    Classify the note type and assign a risk tier.

    Uses retrieved_chunks as context for the LLM. The CLASSIFY_PROMPT is
    designed to work on both raw text and pre-extracted features — we pass
    the raw chunk text since extraction hasn't happened yet.
    """
    errors: list[str] = list(state.get("errors", []))
    chunks = state.get("retrieved_chunks", [])

    if not chunks:
        logger.warning("[triage] No retrieved chunks — defaulting to HIGH tier")
        errors.append("triage: no chunks available, defaulted to high tier")
        return {
            "note_type": "Unknown",
            "structure_tags": [],
            "tag_confidence": {},
            "risk_tier": "high",
            "errors": errors,
        }

    # Build context from top chunks (cap at ~4000 chars to stay within tokens)
    context = "\n\n---\n\n".join(c.get("text", "") for c in chunks[:8])
    context = context[:4000]

    prompt = CLASSIFY_PROMPT.format(extracted_features_json=context)

    try:
        llm = get_chat_llm()
        response = llm.invoke([
            {"role": "system", "content": "You are a structured product analyst specializing in equity-linked notes."},
            {"role": "user", "content": prompt},
        ])
        raw = response.content.strip()

        # Strip markdown code fences if the model wraps in ```json
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)
        tags = result.get("structure_tags", [])
        confidence = result.get("tag_confidence_scores", {})

        risk_tier = _derive_risk_tier(tags)
        note_type = tags[0] if tags else "Unknown"

        logger.info(f"[triage] note_type={note_type} risk_tier={risk_tier} tags={tags}")
        return {
            "note_type": note_type,
            "structure_tags": tags,
            "tag_confidence": confidence,
            "risk_tier": risk_tier,
            "errors": errors,
        }

    except json.JSONDecodeError as exc:
        msg = f"triage: LLM returned invalid JSON — {exc}"
        logger.error(msg)
        errors.append(msg)
    except Exception as exc:
        msg = f"triage: unexpected error — {exc}"
        logger.exception(msg)
        errors.append(msg)

    # Safe fallback: HIGH tier means the full pipeline runs
    return {
        "note_type": "Unknown",
        "structure_tags": [],
        "tag_confidence": {},
        "risk_tier": "high",
        "errors": errors,
    }
