"""
Generate report node: analyst markdown report.

Implements Prompts_v2 step 6 (REPORT_PROMPT).
This is the final node in the pipeline — produces a human-readable report
with confidence icons, structure tag rationale, and conflict review.

Phase 4: Implement LLM report generation.
Phase 1: Stub.

Input state keys:  extracted_fields, structure_tags, tag_confidence,
                   confidence_scores, conflicts, baseline_deviations, risk_findings
Output state keys: report_markdown, report_path
"""

import logging
from backend.pipeline.state import NoteAnalysisState

logger = logging.getLogger(__name__)


def run(state: NoteAnalysisState) -> dict:
    """
    Generate the analyst report markdown.

    TODO (Phase 4):
      - Format all state fields into REPORT_PROMPT template
      - Call LLM with temperature=0.2 (slight creativity for narrative sections)
      - Write output to output/{cusip}_report.md
      - Return report_markdown (string) and report_path (file path)
    """
    cusip = state.get("cusip", "unknown")
    logger.info(f"[generate_report] Phase 1 stub — CUSIP={cusip}")

    stub_report = f"# Structured Note Analyst Report\n\n**CUSIP**: {cusip}\n\n_Report generation not yet implemented (Phase 4)._"
    return {
        "report_markdown": stub_report,
        "report_path": None,
    }
