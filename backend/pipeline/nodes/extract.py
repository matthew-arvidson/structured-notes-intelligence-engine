"""
Extract node: structured field extraction from retrieved chunks.

Three modes controlled by risk_tier (set in triage node):
  full  — full UEQSN schema (~40 fields), HIGH tier
  core  — core identity + risk fields (~15 fields), MEDIUM tier
  meta  — basic identity only (~6 fields), LOW tier

The appropriate prompt is selected automatically from the mode parameter
which is set at graph-build time via the lambda wrappers in graph.py.

Input state keys:  retrieved_chunks
Output state keys: extracted_fields
"""

import json
import logging
from backend.pipeline.state import NoteAnalysisState
from backend.tools.llm_client import get_chat_llm
from backend.domain.prompts import EXTRACT_PROMPT, EXTRACT_CORE_PROMPT, EXTRACT_META_PROMPT

logger = logging.getLogger(__name__)

_PROMPT_BY_MODE = {
    "full": EXTRACT_PROMPT,
    "core": EXTRACT_CORE_PROMPT,
    "meta": EXTRACT_META_PROMPT,
}

# Token budget per mode — more context for full extraction
_CONTEXT_CHARS = {
    "full": 8000,
    "core": 5000,
    "meta": 3000,
}


def run(state: NoteAnalysisState, mode: str = "full") -> dict:
    """
    Extract structured fields from retrieved chunks using the appropriate prompt.

    Errors are non-fatal: if JSON parsing fails, returns whatever was extracted
    with an error note appended to state.errors so the pipeline continues.
    """
    errors: list[str] = list(state.get("errors", []))
    chunks = state.get("retrieved_chunks", [])

    if not chunks:
        logger.warning(f"[extract] No chunks available for mode={mode}")
        errors.append(f"extract: no chunks to extract from (mode={mode})")
        return {"extracted_fields": {}, "errors": errors}

    prompt_template = _PROMPT_BY_MODE.get(mode, EXTRACT_PROMPT)
    char_limit = _CONTEXT_CHARS.get(mode, 6000)

    # Build context from chunks — use more chunks for full extraction
    context = "\n\n---\n\n".join(c.get("text", "") for c in chunks)
    context = context[:char_limit]

    prompt = prompt_template.format(text=context)

    try:
        llm = get_chat_llm()
        response = llm.invoke([
            {"role": "system", "content": "You are a structured product analyst. Return only valid JSON, no commentary."},
            {"role": "user", "content": prompt},
        ])
        raw = response.content.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        extracted = json.loads(raw)
        logger.info(f"[extract] mode={mode} — {len(extracted)} fields extracted for CUSIP={state.get('cusip')}")
        return {"extracted_fields": extracted, "errors": errors}

    except json.JSONDecodeError as exc:
        msg = f"extract: LLM returned invalid JSON (mode={mode}) — {exc}"
        logger.error(f"{msg} | raw={raw[:200]}")
        errors.append(msg)
        return {"extracted_fields": {}, "errors": errors}

    except Exception as exc:
        msg = f"extract: unexpected error (mode={mode}) — {exc}"
        logger.exception(msg)
        errors.append(msg)
        return {"extracted_fields": {}, "errors": errors}
