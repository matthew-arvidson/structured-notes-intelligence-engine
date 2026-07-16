"""
Rule-based risk term dictionary for structured notes.

Each entry maps a searchable term (lowercase substring) to a risk descriptor.
This runs BEFORE any LLM call — fast, auditable, zero hallucination risk.

Categories
----------
barrier      - downside protection thresholds
worst_of     - multi-asset exposure increasing correlation risk
autocall     - early redemption triggers
coupon       - contingent payment conditions
principal    - principal protection / at-risk language
credit       - issuer / guarantor credit exposure
leverage     - amplified loss features

Severity
--------
high    - material risk requiring analyst attention
medium  - notable feature; document and monitor
low     - informational; standard boilerplate

Usage
-----
    from backend.domain.risk_terms import flag_risk_terms
    findings = flag_risk_terms(text="...", section="barrier")
"""

from dataclasses import dataclass


@dataclass
class RiskFinding:
    term: str
    category: str
    severity: str           # "high" | "medium" | "low"
    note: str
    excerpt: str = ""       # populated by flag_risk_terms with surrounding context


# ─── Risk term dictionary ──────────────────────────────────────────────────────
# Format: "search_term": (category, severity, analyst_note)

RISK_TERMS: dict[str, tuple[str, str, str]] = {
    # Barrier / downside
    "knock-in":            ("barrier",   "high",   "Knock-in barrier — investor bears full downside if breached"),
    "knock in":            ("barrier",   "high",   "Knock-in barrier — investor bears full downside if breached"),
    "principal at risk":   ("principal", "high",   "Principal is not protected; full loss possible"),
    "no principal protection": ("principal", "high", "No capital guarantee at maturity"),
    "barrier breach":      ("barrier",   "high",   "Explicit breach language — triggers loss of protection"),
    "barrier level":       ("barrier",   "medium", "Barrier present — verify level relative to starting value"),
    "downside exposure":   ("barrier",   "medium", "Document downside exposure terms"),
    "equity delivery":     ("barrier",   "high",   "Physical settlement risk — investor may receive depreciated shares"),
    "delivery of shares":  ("barrier",   "high",   "Physical delivery on loss — may receive shares below par"),

    # Worst-of / basket
    "worst-of":            ("worst_of",  "high",   "Worst-of basket — correlated downside across all underlyings"),
    "worst of":            ("worst_of",  "high",   "Worst-of basket — correlated downside across all underlyings"),
    "least performing":    ("worst_of",  "high",   "Performance linked to worst underlying in basket"),
    "basket":              ("worst_of",  "medium", "Multi-asset basket — verify weighting and worst-of logic"),

    # Autocall / call risk
    "autocall":            ("autocall",  "medium", "Autocall feature — early redemption possible; limits upside"),
    "auto-call":           ("autocall",  "medium", "Autocall feature — early redemption possible; limits upside"),
    "issuer callable":     ("autocall",  "medium", "Issuer call right — redemption at issuer discretion"),
    "callable":            ("autocall",  "low",    "Call feature present — review call schedule and conditions"),
    "step-up call":        ("autocall",  "medium", "Step-up autocall — trigger level changes over time"),
    "call trigger":        ("autocall",  "medium", "Verify call trigger level and observation schedule"),

    # Coupon conditions
    "contingent coupon":   ("coupon",    "medium", "Coupon is conditional — not guaranteed each period"),
    "memory feature":      ("coupon",    "medium", "Missed coupons may be recovered — track accumulation logic"),
    "memory coupon":       ("coupon",    "medium", "Memory coupon — verify recovery condition and cap"),
    "no coupon":           ("coupon",    "medium", "Zero-coupon structure — verify redemption logic carefully"),
    "range accrual":       ("coupon",    "medium", "Range accrual — coupon depends on underlying staying in band"),

    # Principal / protection
    "principal protected": ("principal", "low",    "PPN structure — confirm protection percentage and conditions"),
    "100% principal":      ("principal", "low",    "Full principal protection claimed — verify guarantor credit"),
    "partial protection":  ("principal", "medium", "Partial principal protection — quantify unprotected portion"),

    # Credit risk
    "credit risk":         ("credit",    "medium", "Credit risk to issuer / guarantor — check ratings"),
    "issuer default":      ("credit",    "high",   "Explicit default language — note is unsecured obligation"),
    "guarantor":           ("credit",    "medium", "Guarantor present — verify guarantee terms and rating"),
    "unsecured":           ("credit",    "medium", "Unsecured obligation — subordination risk in default"),
    "credit-linked":       ("credit",    "high",   "Credit-linked note — exposure to reference entity default"),

    # Leverage / amplified loss
    "leveraged":           ("leverage",  "high",   "Levered structure — losses may exceed initial investment"),
    "2x exposure":         ("leverage",  "high",   "2x leverage — amplified loss on downside"),
    "participation rate":  ("leverage",  "medium", "Verify participation rate — sub-100% caps upside"),
}


def flag_risk_terms(text: str, section: str = "") -> list[RiskFinding]:
    """
    Scan text for known risk terms and return a list of RiskFinding objects.

    Args:
        text: clause or section text to scan (case-insensitive)
        section: optional label for the source section (stored in finding)

    Returns:
        List of RiskFinding instances, de-duplicated by term.
    """
    text_lower = text.lower()
    seen_terms: set[str] = set()
    findings: list[RiskFinding] = []

    for term, (category, severity, note) in RISK_TERMS.items():
        if term in text_lower and term not in seen_terms:
            seen_terms.add(term)
            excerpt = _extract_excerpt(text_lower, term)
            findings.append(
                RiskFinding(
                    term=term,
                    category=category,
                    severity=severity,
                    note=note,
                    excerpt=excerpt,
                )
            )

    # Sort: high first, then medium, then low
    severity_order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: severity_order.get(f.severity, 3))
    return findings


def _extract_excerpt(text: str, term: str, window: int = 120) -> str:
    """Return up to `window` characters surrounding the first match of `term`."""
    idx = text.find(term)
    if idx == -1:
        return ""
    start = max(0, idx - window // 2)
    end = min(len(text), idx + len(term) + window // 2)
    excerpt = text[start:end].strip()
    if start > 0:
        excerpt = "…" + excerpt
    if end < len(text):
        excerpt = excerpt + "…"
    return excerpt
