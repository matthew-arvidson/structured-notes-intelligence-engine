"""
Confidence node: per-field confidence scoring + conflict detection + source attribution.

Implements Prompts_v2 steps 3 (CONFIDENCE_PROMPT) and 4 (CONFLICTS_PROMPT),
plus an in-pipeline RAG step (Step 3b) that fetches the most relevant contract
excerpt for every low-confidence field so analysts can audit against the source.

Input state keys:  extracted_fields, structure_tags, tag_confidence, cusip
Output state keys: confidence_scores, conflicts
"""

import json
import logging
from backend.pipeline.state import NoteAnalysisState
from backend.tools.llm_client import get_chat_llm, get_embeddings
from backend.tools.chroma_client import get_collection
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

        # LLM occasionally wraps the object in an array — unwrap if so
        if isinstance(confidence_scores, list):
            confidence_scores = confidence_scores[0] if confidence_scores and isinstance(confidence_scores[0], dict) else {}

        # Normalise: accept both legacy {field: int} and new {field: {score, reason}}
        # Convert legacy flat-int format to the enriched format so storage is always consistent
        normalised: dict[str, dict] = {}
        for field, val in confidence_scores.items():
            if isinstance(val, dict) and "score" in val:
                normalised[field] = {"score": int(val["score"]), "reason": val.get("reason", "")}
            elif isinstance(val, (int, float)):
                normalised[field] = {"score": int(val), "reason": ""}
        confidence_scores = normalised

        low_confidence = [f for f, v in confidence_scores.items() if v.get("score", 100) < 90]
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

    # ── Step 3b: Source Attribution via RAG ───────────────────────────────────
    # For every scored field, run a targeted embedding query against the CUSIP's
    # own chunks and attach the best-matching excerpt + metadata so analysts can
    # trace any extracted value back to the exact contract language.
    cusip = state.get("cusip", "")
    if cusip and confidence_scores:
        try:
            embed_fn = get_embeddings()
            collection = get_collection()

            for field, entry in confidence_scores.items():
                extracted_val = str(fields.get(field, ""))[:200]
                query = f"{field}: {extracted_val}" if extracted_val else field

                vector = embed_fn.embed_query(query)
                results = collection.query(
                    query_embeddings=[vector],
                    n_results=1,
                    where={"cusip": cusip},
                    include=["documents", "metadatas"],
                )

                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]

                if docs and metas:
                    entry["source_section"] = metas[0].get("section", "")
                    entry["source_page"] = metas[0].get("page", "")
                    entry["source_excerpt"] = docs[0]

            logger.info(f"[confidence] Source attribution complete for CUSIP={cusip}")
        except Exception as exc:
            logger.warning(f"[confidence] Source attribution failed (non-fatal): {exc}")

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
