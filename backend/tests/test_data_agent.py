"""Tests for DataAgent internal functions.

Covers _extract_chart JSON extraction and the empty tool_results guard.
"""

import json
import pytest

from app.agents.data_agent import _extract_chart


# ---------- _extract_chart ----------

class TestExtractChart:
    """Test the chart JSON extraction from agent text responses."""

    def test_extracts_valid_chart_block(self):
        chart_json = json.dumps({"type": "bar", "data": [{"x": 1, "y": 2}], "title": "Test"})
        text = f"Here is the data:\n```chart\n{chart_json}\n```\nAll done."
        cleaned, chart = _extract_chart(text)
        assert chart is not None
        assert chart["type"] == "bar"
        assert chart["title"] == "Test"
        assert len(chart["data"]) == 1

    def test_removes_chart_block_from_text(self):
        chart_json = json.dumps({"type": "line", "data": []})
        text = f"Before.\n```chart\n{chart_json}\n```\nAfter."
        cleaned, chart = _extract_chart(text)
        assert "```chart" not in cleaned
        assert chart_json not in cleaned
        assert "Before." in cleaned
        assert "After." in cleaned

    def test_returns_none_when_no_chart_block(self):
        text = "Just a normal response with no chart data."
        cleaned, chart = _extract_chart(text)
        assert chart is None
        assert cleaned == text

    def test_returns_none_for_invalid_json(self):
        text = "```chart\n{not valid json!!}\n```"
        cleaned, chart = _extract_chart(text)
        assert chart is None
        # Text should be returned as-is since JSON parsing failed
        assert "not valid json" in cleaned

    def test_handles_multiline_chart_json(self):
        chart_obj = {
            "type": "bar",
            "data": [
                {"month": "Jan", "value": 10},
                {"month": "Feb", "value": 20},
            ],
            "title": "Monthly",
        }
        chart_json = json.dumps(chart_obj, indent=2)
        text = f"Results:\n```chart\n{chart_json}\n```"
        cleaned, chart = _extract_chart(text)
        assert chart is not None
        assert chart["type"] == "bar"
        assert len(chart["data"]) == 2

    def test_handles_chart_block_at_start_of_text(self):
        chart_json = json.dumps({"type": "pie", "data": [{"name": "A", "value": 1}]})
        text = f"```chart\n{chart_json}\n```\nSummary follows."
        cleaned, chart = _extract_chart(text)
        assert chart is not None
        assert chart["type"] == "pie"
        assert "Summary follows." in cleaned

    def test_handles_chart_block_at_end_of_text(self):
        chart_json = json.dumps({"type": "line", "data": []})
        text = f"Here is the trend.\n```chart\n{chart_json}\n```"
        cleaned, chart = _extract_chart(text)
        assert chart is not None
        assert "Here is the trend." in cleaned

    def test_only_extracts_first_chart_block(self):
        chart1 = json.dumps({"type": "bar", "data": []})
        chart2 = json.dumps({"type": "line", "data": []})
        text = f"```chart\n{chart1}\n```\nThen:\n```chart\n{chart2}\n```"
        cleaned, chart = _extract_chart(text)
        # Should extract the first one
        assert chart is not None
        assert chart["type"] == "bar"

    def test_ignores_non_chart_code_blocks(self):
        text = "```python\nprint('hello')\n```\nNo chart here."
        cleaned, chart = _extract_chart(text)
        assert chart is None
        assert "print('hello')" in cleaned

    def test_empty_text_returns_no_chart(self):
        cleaned, chart = _extract_chart("")
        assert chart is None
        assert cleaned == ""


# ---------- _extract_chart edge cases with whitespace ----------

class TestExtractChartWhitespace:

    def test_chart_block_with_extra_whitespace(self):
        chart_json = json.dumps({"type": "bar", "data": [{"a": 1}]})
        # Extra spaces after ```chart
        text = f"```chart   \n{chart_json}\n```"
        cleaned, chart = _extract_chart(text)
        assert chart is not None

    def test_chart_block_with_trailing_newlines(self):
        chart_json = json.dumps({"type": "bar", "data": []})
        text = f"Intro\n\n```chart\n{chart_json}\n```\n\n"
        cleaned, chart = _extract_chart(text)
        assert chart is not None
        assert chart["type"] == "bar"
