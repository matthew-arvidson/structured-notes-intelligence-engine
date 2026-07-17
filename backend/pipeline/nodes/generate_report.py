"""
Generate report node: analyst markdown report.

Implements Prompts_v2 step 6 (REPORT_PROMPT).
Final node in the pipeline — produces a human-readable markdown report with
confidence icons, conflict review, and a plain-language summary.

Input state keys:  extracted_fields, structure_tags, tag_confidence,
                   confidence_scores, conflicts, baseline_deviations, risk_findings, cusip
Output state keys: report_markdown, report_path
"""

import json
import logging
import os
from backend.pipeline.state import NoteAnalysisState
from backend.tools.llm_client import get_chat_llm
from backend.domain.prompts import REPORT_PROMPT

logger = logging.getLogger(__name__)

_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "output")


def _ensure_output_dir() -> str:
    path = os.path.abspath(_OUTPUT_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def _risk_findings_summary(findings: list[dict]) -> str:
    """Format risk findings as a compact markdown section to append to the report."""
    if not findings:
        return ""
    lines = ["\n### Risk Term Findings\n", "| Term | Category | Severity | Section |", "|---|---|---|---|"]
    for f in findings:
        lines.append(f"| {f.get('term','')} | {f.get('category','')} | {f.get('severity','')} | {f.get('source_section','')} |")
    return "\n".join(lines)


def _baseline_summary(deviations: list[dict]) -> str:
    """Format baseline deviations as a compact markdown section."""
    if not deviations:
        return ""
    lines = ["\n### Baseline Deviation Summary\n", "| Field | Expected | Actual | Severity |", "|---|---|---|---|"]
    for d in deviations:
        lines.append(f"| {d.get('field','')} | {d.get('expected','')} | {d.get('actual','')} | {d.get('severity','')} |")
    return "\n".join(lines)


def run(state: NoteAnalysisState) -> dict:
    """
    Generate the analyst report markdown via the REPORT_PROMPT LLM call.

    Uses temperature=0.2 for slight narrative flexibility while keeping
    tables and field references deterministic.

    Output is written to output/{cusip}_report.md and also returned in state.
    Non-fatal: if generation fails, a minimal fallback report is returned.
    """
    cusip = state.get("cusip", "unknown")
    errors: list[str] = list(state.get("errors", []))

    fields = state.get("extracted_fields", {})
    tags = state.get("structure_tags", [])
    tag_confidence = state.get("tag_confidence", {})
    confidence_scores = state.get("confidence_scores", {})
    conflicts = state.get("conflicts", [])
    risk_findings = state.get("risk_findings", [])
    baseline_deviations = state.get("baseline_deviations", [])

    # Build the structure_tags_json combining tags + tag confidence for the prompt
    tags_with_confidence = [
        {"tag": t, "confidence": tag_confidence.get(t, 100)}
        for t in tags
    ]

    try:
        prompt = REPORT_PROMPT.format(
            extracted_features_json=json.dumps(fields, indent=2),
            structure_tags_json=json.dumps(tags_with_confidence, indent=2),
            confidence_scores_json=json.dumps(confidence_scores, indent=2),
            conflicts_json=json.dumps(conflicts, indent=2),
        )

        llm = get_chat_llm(temperature=0.2)
        response = llm.invoke([
            {"role": "system", "content": "You are a senior equity structured note analyst. Generate a formal, concise analyst report in markdown."},
            {"role": "user", "content": prompt},
        ])
        report_md = response.content.strip()

        # Append deterministic sections that don't need LLM
        report_md += _risk_findings_summary(risk_findings)
        report_md += _baseline_summary(baseline_deviations)

        logger.info(f"[generate_report] Report generated for CUSIP={cusip} ({len(report_md)} chars)")

    except Exception as exc:
        msg = f"generate_report: LLM call failed — {exc}"
        logger.exception(msg)
        errors.append(msg)
        # Minimal fallback so the pipeline always returns something useful
        report_md = (
            f"# Structured Note Analyst Report\n\n"
            f"**CUSIP**: {cusip}  \n"
            f"**Note Type**: {state.get('note_type', 'Unknown')}  \n"
            f"**Risk Tier**: {state.get('risk_tier', 'unknown')}  \n"
            f"**Structure Tags**: {', '.join(tags)}\n\n"
            f"_Report narrative unavailable — LLM generation failed._\n"
        )
        report_md += _risk_findings_summary(risk_findings)
        report_md += _baseline_summary(baseline_deviations)

    # Write to disk
    report_path: str | None = None
    try:
        out_dir = _ensure_output_dir()
        safe_cusip = "".join(c for c in cusip if c.isalnum() or c in "-_")
        report_path = os.path.join(out_dir, f"{safe_cusip}_report.md")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write(report_md)
        logger.info(f"[generate_report] Report written to {report_path}")
    except Exception as exc:
        msg = f"generate_report: could not write report file — {exc}"
        logger.warning(msg)
        errors.append(msg)

    return {
        "report_markdown": report_md,
        "report_path": report_path,
        "errors": errors,
    }
