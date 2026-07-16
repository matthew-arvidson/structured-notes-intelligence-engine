"""
Tests for the triage node.

Phase 1: Only tests the stub behavior.
Phase 2: Add tests with mocked LLM responses once the node is implemented.

    pytest backend/tests/test_triage.py -v
"""

import pytest
from backend.pipeline.nodes.triage import run
from backend.pipeline.state import NoteAnalysisState


class TestTriageStub:

    def test_returns_required_keys(self):
        state: NoteAnalysisState = {
            "cusip": "TEST12345",
            "retrieved_chunks": [],
            "errors": [],
        }
        result = run(state)
        assert "note_type" in result
        assert "structure_tags" in result
        assert "tag_confidence" in result
        assert "risk_tier" in result

    def test_risk_tier_is_valid_value(self):
        state: NoteAnalysisState = {
            "cusip": "TEST12345",
            "retrieved_chunks": [],
            "errors": [],
        }
        result = run(state)
        assert result["risk_tier"] in {"high", "medium", "low"}

    def test_structure_tags_is_list(self):
        state: NoteAnalysisState = {
            "cusip": "TEST12345",
            "retrieved_chunks": [],
            "errors": [],
        }
        result = run(state)
        assert isinstance(result["structure_tags"], list)

    def test_tag_confidence_is_dict(self):
        state: NoteAnalysisState = {
            "cusip": "TEST12345",
            "retrieved_chunks": [],
            "errors": [],
        }
        result = run(state)
        assert isinstance(result["tag_confidence"], dict)


# TODO (Phase 2): Add tests like these once the LLM path is implemented:
#
# @pytest.mark.asyncio
# async def test_phoenix_classification(mock_llm):
#     mock_llm.return_value = '{"structure_tags": ["Phoenix", "Contingent Coupon"], ...}'
#     state = {"cusip": "...", "retrieved_chunks": [{"text": "phoenix note..."}]}
#     result = run(state)
#     assert "Phoenix" in result["structure_tags"]
#     assert result["risk_tier"] == "high"
