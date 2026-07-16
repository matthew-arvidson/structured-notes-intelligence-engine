"""
Flag risks node: rule-based risk term scanning.

Runs BEFORE any LLM call — deterministic, auditable, zero hallucination risk.
Uses the risk_terms dictionary in backend/domain/risk_terms.py.

Input state keys:  retrieved_chunks, extracted_fields
Output state keys: risk_findings
"""

import logging
from backend.pipeline.state import NoteAnalysisState
from backend.domain.risk_terms import flag_risk_terms

logger = logging.getLogger(__name__)


def run(state: NoteAnalysisState) -> dict:
    """
    Scan all retrieved chunks for known risk terms and consolidate findings.

    Deduplicates by term across chunks — a term flagged in multiple chunks
    appears once with the first matching excerpt.
    """
    chunks = state.get("retrieved_chunks", [])
    seen_terms: set[str] = set()
    all_findings: list[dict] = []

    for chunk in chunks:
        text = chunk.get("text", "")
        section = chunk.get("metadata", {}).get("section", "")
        findings = flag_risk_terms(text=text, section=section)

        for f in findings:
            if f.term not in seen_terms:
                seen_terms.add(f.term)
                all_findings.append(
                    {
                        "term": f.term,
                        "category": f.category,
                        "severity": f.severity,
                        "note": f.note,
                        "excerpt": f.excerpt,
                        "source_section": section,
                    }
                )

    high_count = sum(1 for f in all_findings if f["severity"] == "high")
    logger.info(
        f"[flag_risks] {len(all_findings)} findings "
        f"({high_count} high severity) for CUSIP={state.get('cusip')}"
    )

    return {"risk_findings": all_findings}
