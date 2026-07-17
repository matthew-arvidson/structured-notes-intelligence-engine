"""
Compare baseline node: check extracted fields against firm-standard baseline.

Pure rule-based — no LLM required. Fast and fully auditable.
Rules are loaded from backend/domain/standard_baseline.json.

Input state keys:  extracted_fields, structure_tags
Output state keys: baseline_deviations, matches_baseline
"""

import json
import logging
import os
from backend.pipeline.state import NoteAnalysisState

logger = logging.getLogger(__name__)

_BASELINE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "domain", "standard_baseline.json"
)


def _load_baseline() -> dict:
    with open(_BASELINE_PATH, "r") as f:
        return json.load(f)


def _parse_pct(value) -> float | None:
    """
    Parse a percentage-like value into a 0-1 float.
    Handles: "20.00%", "0.20", 20.0, None.
    """
    if value is None:
        return None
    try:
        s = str(value).replace("%", "").strip()
        n = float(s)
        # Values like 20.0 are percentages (20%), not decimals (0.20)
        return n / 100.0 if n > 1.0 else n
    except (ValueError, TypeError):
        return None


def run(state: NoteAnalysisState) -> dict:
    """
    Compare extracted fields against firm-standard baseline rules.

    Returns a list of deviation dicts and a matches_baseline boolean.
    Deviations are informational — the pipeline always continues.
    """
    fields = state.get("extracted_fields", {})
    tags = set(state.get("structure_tags", []))
    deviations: list[dict] = []

    if not fields:
        logger.info("[compare_baseline] No extracted fields — skipping checks")
        return {"baseline_deviations": [], "matches_baseline": True}

    try:
        baseline = _load_baseline()
    except Exception as exc:
        logger.error(f"[compare_baseline] Could not load baseline: {exc}")
        return {"baseline_deviations": [], "matches_baseline": True}

    # ── Rule 1: BarrierLevel >= 60% minimum ───────────────────────────────────
    barrier_raw = fields.get("BarrierLevel")
    barrier = _parse_pct(barrier_raw)
    min_barrier = baseline.get("BarrierLogic", {}).get("BarrierLevel_minimum_acceptable", 0.60)

    if barrier is not None and barrier < min_barrier:
        deviations.append({
            "field":    "BarrierLevel",
            "expected": f">= {min_barrier * 100:.0f}%",
            "actual":   f"{barrier * 100:.2f}%",
            "severity": "high",
            "note":     "Barrier below firm minimum — requires senior analyst sign-off",
        })
    elif barrier is None and "Worst-of" in tags:
        deviations.append({
            "field":    "BarrierLevel",
            "expected": "Present (Worst-of structure)",
            "actual":   "null",
            "severity": "medium",
            "note":     "Worst-of structure without a barrier level — verify with source",
        })

    # ── Rule 2: CouponMemory preferred for contingent coupon structures ────────
    is_contingent = (
        fields.get("CouponType") in ("Contingent", "contingent")
        or "Contingent Coupon" in tags
        or "Memory Feature" in tags
    )
    memory_preferred = baseline.get("CouponStructure", {}).get("CouponMemory_preferred", True)

    if is_contingent and memory_preferred:
        coupon_memory = fields.get("CouponMemory")
        if not coupon_memory or str(coupon_memory).lower() in ("null", "none", "false", ""):
            deviations.append({
                "field":    "CouponMemory",
                "expected": "True (preferred for contingent coupon structures)",
                "actual":   str(coupon_memory),
                "severity": "low",
                "note":     "Memory feature absent — requires justification",
            })

    # ── Rule 3: CallSettlementLag <= 5 business days ──────────────────────────
    max_lag = baseline.get("CallLogic", {}).get("CallSettlementLag_maximum_days", 5)
    lag_raw = fields.get("CallSettlementLag")
    if lag_raw is not None:
        try:
            lag = int(str(lag_raw).split()[0])  # handles "3 business days"
            if lag > max_lag:
                deviations.append({
                    "field":    "CallSettlementLag",
                    "expected": f"<= {max_lag} business days",
                    "actual":   str(lag_raw),
                    "severity": "medium",
                    "note":     "Settlement lag exceeds limit — operations review required",
                })
        except (ValueError, TypeError):
            pass

    # ── Rule 4: Required fields present ──────────────────────────────────────
    # Only apply required-field checks to standard EQ barrier structures.
    # Warrants, single asset meta-only notes, and non-standard products skip this.
    _EXEMPT_TYPES = {"Vanilla Warrant", "Digital Warrant", "Single Asset", "Unknown"}
    note_type = state.get("note_type", "") or ""
    skip_required_checks = note_type in _EXEMPT_TYPES or risk_tier == "low"

    req = baseline.get("RequiredFields", {})

    def _check_required(field_path: str, label: str = "") -> bool:
        """Check a dot-notated field path against extracted_fields."""
        parts = field_path.split(".")
        key = parts[-1]
        val = fields.get(key)
        # Also check nested under the parent key (e.g. SecurityIdentifier.CUSIP)
        if val is None and len(parts) > 1:
            parent = fields.get(parts[-2])
            if isinstance(parent, dict):
                val = parent.get(key)
        return val is not None and str(val).lower() not in ("null", "none", "")

    for field_path in req.get("always_required", []):
        if skip_required_checks:
            break
        if not _check_required(field_path):
            key = field_path.split(".")[-1]
            deviations.append({
                "field":    key,
                "expected": "Present",
                "actual":   "null",
                "severity": "medium",
                "note":     "Required field missing from extraction",
            })

    if is_contingent and not skip_required_checks:
        for field_path in req.get("required_if_contingent_coupon", []):
            if not _check_required(field_path):
                key = field_path.split(".")[-1]
                deviations.append({
                    "field":    key,
                    "expected": "Present (contingent coupon structure)",
                    "actual":   "null",
                    "severity": "medium",
                    "note":     "Required for contingent coupon — missing from extraction",
                })

    is_autocallable = any(t in tags for t in ("Auto-callable", "AutoCallable", "Autocallable"))
    if is_autocallable and not skip_required_checks:
        for field_path in req.get("required_if_autocallable", []):
            if not _check_required(field_path):
                key = field_path.split(".")[-1]
                deviations.append({
                    "field":    key,
                    "expected": "Present (autocallable structure)",
                    "actual":   "null",
                    "severity": "medium",
                    "note":     "Required for autocallable — missing from extraction",
                })

    # matches_baseline = no HIGH severity deviations
    matches = not any(d["severity"] == "high" for d in deviations)

    logger.info(
        f"[compare_baseline] {len(deviations)} deviations "
        f"(matches_baseline={matches}) for CUSIP={state.get('cusip')}"
    )
    return {
        "baseline_deviations": deviations,
        "matches_baseline": matches,
    }
