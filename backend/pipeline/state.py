"""
LangGraph state definition for the note analysis pipeline.

NoteAnalysisState is the single TypedDict that flows through every node in
the graph. Each node reads what it needs and writes its results back into
the same dict. LangGraph merges state updates automatically.

Design notes
------------
- All fields are Optional so nodes can be skipped cleanly without key errors.
- `errors` accumulates non-fatal issues (e.g. a field that failed to extract)
  so the pipeline can continue and flag issues in the final report rather than
  raising mid-graph.
- `risk_tier` drives routing: "high" → full analysis, "medium" → flags only,
  "low" → metadata extraction only.
"""

from typing import Optional, TypedDict


class NoteAnalysisState(TypedDict, total=False):
    # ── Input ─────────────────────────────────────────────────────────────────
    cusip: str                          # primary identifier for this note
    pdf_path: Optional[str]            # local path to the uploaded PDF
    source_url: Optional[str]          # original URL (if URL-scraped)

    # ── Ingestion (nodes: ingest) ─────────────────────────────────────────────
    chunks_stored: int                  # number of chunks upserted to ChromaDB
    source_file: Optional[str]         # filename of the ingested PDF

    # ── Retrieval (node: retrieve) ────────────────────────────────────────────
    retrieved_chunks: list[dict]        # top-k chunks from ChromaDB query
                                        # each dict: {text, metadata, distance}

    # ── Triage (node: triage) ────────────────────────────────────────────────
    note_type: Optional[str]           # e.g. "Phoenix", "RCN", "AutoCallable"
    structure_tags: list[str]          # multi-tag classification
    tag_confidence: dict[str, int]     # tag → confidence score 0-100
    risk_tier: str                      # "high" | "medium" | "low"

    # ── Extraction (node: extract) ───────────────────────────────────────────
    extracted_fields: dict              # UEQSN schema fields, depth varies by tier

    # ── Risk Flagging (node: flag_risks) ─────────────────────────────────────
    risk_findings: list[dict]           # [{term, category, severity, excerpt}]

    # ── Baseline Comparison (node: compare_baseline) ─────────────────────────
    baseline_deviations: list[dict]     # [{field, expected, actual, severity}]
    matches_baseline: bool

    # ── Confidence & Conflicts (node: confidence) ─────────────────────────────
    confidence_scores: dict[str, int]  # field → score 0-100
    conflicts: list[dict]               # [{issue, fields_involved, severity}]

    # ── Persistence (node: persist) ───────────────────────────────────────────
    db_record_id: Optional[int]        # Azure SQL primary key after upsert

    # ── Report (node: generate_report) ────────────────────────────────────────
    report_markdown: Optional[str]     # full analyst report text
    report_path: Optional[str]         # path to saved .md file (if written)

    # ── Cross-cutting ─────────────────────────────────────────────────────────
    errors: list[str]                   # non-fatal errors accumulated across nodes
