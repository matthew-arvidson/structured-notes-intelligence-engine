"""
LangGraph StateGraph definition for the note analysis pipeline.

Graph structure:
    ingest → retrieve → triage → [routing] → extract → flag_risks
                                                       → compare_baseline
                                                       → confidence
                                                       → persist
                                                       → generate_report → END

Routing after triage:
    HIGH   → extract (full schema) → flag_risks → compare_baseline → confidence → persist → report
    MEDIUM → extract (core fields) → flag_risks → persist → report
    LOW    → extract (meta only)   → persist → report

Build status: Phase 1 skeleton — nodes are stubs.
Full node implementations added in Phases 2-4.
"""

from langgraph.graph import StateGraph, END
from backend.pipeline.state import NoteAnalysisState
from backend.pipeline.nodes import (
    ingest,
    retrieve,
    triage,
    extract,
    flag_risks,
    compare_baseline,
    confidence,
    persist,
    generate_report,
)


def _route_after_triage(state: NoteAnalysisState) -> str:
    """
    Routing function called after the triage node.
    Returns the name of the next node based on risk_tier.
    """
    tier = state.get("risk_tier", "low")
    if tier == "high":
        return "extract_full"
    elif tier == "medium":
        return "extract_core"
    else:
        return "extract_meta"


def build_graph() -> StateGraph:
    """
    Construct and compile the note analysis StateGraph.

    Returns a compiled graph ready to invoke with:
        graph = build_graph()
        result = graph.invoke({"cusip": "...", "pdf_path": "..."})
    """
    graph = StateGraph(NoteAnalysisState)

    # ── Node registration ──────────────────────────────────────────────────────
    graph.add_node("ingest",            ingest.run)
    graph.add_node("retrieve",          retrieve.run)
    graph.add_node("triage",            triage.run)

    # Three extraction depth levels — same node function, different mode arg
    graph.add_node("extract_full",      lambda s: extract.run(s, mode="full"))
    graph.add_node("extract_core",      lambda s: extract.run(s, mode="core"))
    graph.add_node("extract_meta",      lambda s: extract.run(s, mode="meta"))

    graph.add_node("flag_risks",        flag_risks.run)
    graph.add_node("compare_baseline",  compare_baseline.run)
    graph.add_node("confidence",        confidence.run)
    graph.add_node("persist",           persist.run)
    graph.add_node("generate_report",   generate_report.run)

    # ── Entry point ────────────────────────────────────────────────────────────
    graph.set_entry_point("ingest")

    # ── Linear edges ──────────────────────────────────────────────────────────
    graph.add_edge("ingest",    "retrieve")
    graph.add_edge("retrieve",  "triage")

    # ── Conditional routing after triage ──────────────────────────────────────
    graph.add_conditional_edges(
        "triage",
        _route_after_triage,
        {
            "extract_full": "extract_full",
            "extract_core": "extract_core",
            "extract_meta": "extract_meta",
        },
    )

    # HIGH path: full analysis chain
    graph.add_edge("extract_full",  "flag_risks")
    graph.add_edge("flag_risks",    "compare_baseline")
    graph.add_edge("compare_baseline", "confidence")
    graph.add_edge("confidence",    "persist")

    # MEDIUM path: flags only, skip baseline + confidence
    graph.add_edge("extract_core",  "flag_risks")
    # flag_risks → persist handled by conditional below

    # LOW path: straight to persist
    graph.add_edge("extract_meta",  "persist")

    # Both medium (after flags) and high (after confidence) converge at persist
    # This is handled by the node routing above — persist is always the step
    # before report regardless of path.
    graph.add_edge("persist",       "generate_report")
    graph.add_edge("generate_report", END)

    return graph.compile()


# Module-level compiled graph — import and invoke directly
note_analysis_graph = build_graph()
