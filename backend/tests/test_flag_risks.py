"""
Unit tests for the rule-based risk term flagging.

These tests require NO mocking and NO API keys — pure Python logic.
Run first to validate the risk dictionary works before touching the LLM layer.

    pytest backend/tests/test_flag_risks.py -v
"""

import pytest
from backend.domain.risk_terms import flag_risk_terms, RiskFinding


class TestFlagRiskTerms:

    def test_no_findings_on_clean_text(self):
        text = "The note matures on the final valuation date at par."
        findings = flag_risk_terms(text)
        assert findings == []

    def test_knock_in_flagged_as_high(self):
        text = "The investor is exposed to a knock-in barrier set at 70% of the initial price."
        findings = flag_risk_terms(text)
        terms = [f.term for f in findings]
        assert "knock-in" in terms
        high_findings = [f for f in findings if f.term == "knock-in"]
        assert high_findings[0].severity == "high"

    def test_worst_of_flagged_as_high(self):
        text = "Redemption is linked to the worst-of performance across three underlying stocks."
        findings = flag_risk_terms(text)
        terms = [f.term for f in findings]
        assert "worst-of" in terms

    def test_principal_at_risk_flagged(self):
        text = "The principal at risk is the full notional amount if the barrier is breached."
        findings = flag_risk_terms(text)
        terms = [f.term for f in findings]
        assert "principal at risk" in terms

    def test_autocall_flagged_as_medium(self):
        text = "The note includes an autocall feature with monthly observation dates starting Month 6."
        findings = flag_risk_terms(text)
        terms = [f.term for f in findings]
        assert "autocall" in terms
        autocall = next(f for f in findings if f.term == "autocall")
        assert autocall.severity == "medium"

    def test_deduplication(self):
        # Same term appearing twice should produce one finding
        text = "knock-in barrier applies. The knock-in level is set at 60%."
        findings = flag_risk_terms(text)
        knock_in_findings = [f for f in findings if f.term == "knock-in"]
        assert len(knock_in_findings) == 1

    def test_high_severity_sorted_first(self):
        text = (
            "The note has an autocall feature. "
            "The worst-of basket introduces correlation risk. "
            "A knock-in barrier is set at 65%."
        )
        findings = flag_risk_terms(text)
        assert len(findings) > 0
        assert findings[0].severity == "high"

    def test_excerpt_populated(self):
        text = "The investor faces equity delivery risk if the barrier is breached at maturity."
        findings = flag_risk_terms(text)
        equity_findings = [f for f in findings if "equity delivery" in f.term]
        assert len(equity_findings) > 0
        assert len(equity_findings[0].excerpt) > 0

    def test_case_insensitive(self):
        text = "This note features a KNOCK-IN barrier and WORST-OF basket mechanics."
        findings = flag_risk_terms(text)
        terms = [f.term for f in findings]
        assert "knock-in" in terms
        assert "worst-of" in terms

    def test_section_parameter_accepted(self):
        text = "Downside exposure is limited to barrier breach scenarios."
        findings = flag_risk_terms(text, section="barrier")
        assert isinstance(findings, list)

    def test_multiple_categories_returned(self):
        text = (
            "The basket worst-of note pays a contingent coupon above the barrier level. "
            "Principal at risk if knock-in occurs. Unsecured obligation of the issuer."
        )
        findings = flag_risk_terms(text)
        categories = {f.category for f in findings}
        assert len(categories) >= 3
