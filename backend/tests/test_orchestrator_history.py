"""Tests for OrchestratorAgent._text_history method.

Covers merging consecutive same-role messages, skipping empty content,
and extracting text from ContentBlock objects.
"""

import pytest
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock


# We need to mock settings before importing OrchestratorAgent
# because it reads settings.anthropic_api_key at class init time.
with patch("app.config.settings") as mock_settings:
    mock_settings.anthropic_api_key = "test-key"
    mock_settings.on24_client_id = "10710"
    from app.agents.orchestrator import OrchestratorAgent


def _make_agent() -> OrchestratorAgent:
    """Create an OrchestratorAgent with mocked dependencies."""
    with patch("app.agents.orchestrator.settings") as ms, \
         patch("anthropic.AsyncAnthropic"):
        ms.anthropic_api_key = "test-key"
        ms.on24_client_id = "10710"
        agent = OrchestratorAgent()
    return agent


# ---------- Basic text extraction ----------

class TestTextHistory:

    def test_simple_string_content(self):
        agent = _make_agent()
        agent.conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        result = agent._text_history()
        assert len(result) == 2
        assert result[0] == {"role": "user", "content": "Hello"}
        assert result[1] == {"role": "assistant", "content": "Hi there"}

    def test_skips_empty_string_content(self):
        agent = _make_agent()
        agent.conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "How are you?"},
        ]
        result = agent._text_history()
        # Empty assistant is skipped, so two consecutive user messages merge
        assert len(result) == 1
        assert "Hello" in result[0]["content"]
        assert "How are you?" in result[0]["content"]

    def test_skips_whitespace_only_content(self):
        agent = _make_agent()
        agent.conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "   \n\t  "},
            {"role": "user", "content": "Next"},
        ]
        result = agent._text_history()
        # Whitespace-only assistant is skipped, so two user messages merge
        assert len(result) == 1
        assert "Hello" in result[0]["content"]
        assert "Next" in result[0]["content"]

    # ---------- Merging consecutive same-role ----------

    def test_merges_consecutive_same_role_messages(self):
        agent = _make_agent()
        agent.conversation_history = [
            {"role": "user", "content": "First question"},
            {"role": "user", "content": "More context"},
            {"role": "assistant", "content": "Answer"},
        ]
        result = agent._text_history()
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert "First question" in result[0]["content"]
        assert "More context" in result[0]["content"]
        assert result[1]["content"] == "Answer"

    def test_merges_three_consecutive_user_messages(self):
        agent = _make_agent()
        agent.conversation_history = [
            {"role": "user", "content": "A"},
            {"role": "user", "content": "B"},
            {"role": "user", "content": "C"},
            {"role": "assistant", "content": "Reply"},
        ]
        result = agent._text_history()
        assert len(result) == 2
        assert "A" in result[0]["content"]
        assert "B" in result[0]["content"]
        assert "C" in result[0]["content"]

    def test_no_merge_when_roles_alternate(self):
        agent = _make_agent()
        agent.conversation_history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]
        result = agent._text_history()
        assert len(result) == 4

    # ---------- List content with text blocks ----------

    def test_extracts_text_from_dict_text_blocks(self):
        agent = _make_agent()
        agent.conversation_history = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Hello from list"},
                    {"type": "text", "text": "more text"},
                ],
            },
        ]
        result = agent._text_history()
        assert len(result) == 1
        assert "Hello from list" in result[0]["content"]
        assert "more text" in result[0]["content"]

    def test_skips_tool_use_blocks_in_list(self):
        agent = _make_agent()
        agent.conversation_history = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Routing to agent"},
                    {"type": "tool_use", "id": "tool_1", "name": "route_to_data_agent", "input": {"query": "test"}},
                ],
            },
        ]
        result = agent._text_history()
        assert len(result) == 1
        assert "Routing to agent" in result[0]["content"]
        assert "route_to_data_agent" not in result[0]["content"]

    def test_skips_tool_result_list_content(self):
        """When content is a list of tool_result dicts (no text blocks), skip entirely."""
        agent = _make_agent()
        agent.conversation_history = [
            {"role": "user", "content": "Hello"},
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "abc", "content": "{}"},
                ],
            },
            {"role": "assistant", "content": "Response"},
        ]
        result = agent._text_history()
        # tool_result message should be skipped, leaving user + assistant
        assert len(result) == 2
        assert result[0]["content"] == "Hello"
        assert result[1]["content"] == "Response"

    # ---------- ContentBlock objects (Anthropic SDK) ----------

    def test_extracts_text_from_content_block_objects(self):
        """Simulate Anthropic SDK ContentBlock objects with .type and .text attributes."""
        agent = _make_agent()
        block1 = SimpleNamespace(type="text", text="Block one")
        block2 = SimpleNamespace(type="text", text="Block two")
        agent.conversation_history = [
            {"role": "assistant", "content": [block1, block2]},
        ]
        result = agent._text_history()
        assert len(result) == 1
        assert "Block one" in result[0]["content"]
        assert "Block two" in result[0]["content"]

    def test_skips_content_block_tool_use(self):
        """ContentBlock objects with type='tool_use' should be excluded via hasattr check."""
        agent = _make_agent()
        text_block = SimpleNamespace(type="text", text="Some text")
        tool_block = SimpleNamespace(type="tool_use", id="t1", name="test", input={})
        agent.conversation_history = [
            {"role": "assistant", "content": [text_block, tool_block]},
        ]
        result = agent._text_history()
        assert len(result) == 1
        assert "Some text" in result[0]["content"]

    def test_empty_content_block_list_skipped(self):
        """If all ContentBlocks are tool_use (no text), skip the message."""
        agent = _make_agent()
        tool_block = SimpleNamespace(type="tool_use", id="t1", name="test", input={})
        agent.conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": [tool_block]},
            {"role": "user", "content": "Next"},
        ]
        result = agent._text_history()
        # assistant message with only tool_use should be skipped
        # two consecutive user messages should merge
        assert len(result) == 1
        assert "Hello" in result[0]["content"]
        assert "Next" in result[0]["content"]

    # ---------- Edge cases ----------

    def test_empty_history(self):
        agent = _make_agent()
        agent.conversation_history = []
        result = agent._text_history()
        assert result == []

    def test_none_content_skipped(self):
        agent = _make_agent()
        agent.conversation_history = [
            {"role": "user", "content": None},
            {"role": "assistant", "content": "Reply"},
        ]
        result = agent._text_history()
        assert len(result) == 1
        assert result[0]["content"] == "Reply"

    def test_mixed_content_types_in_sequence(self):
        """Realistic scenario: user text, assistant tool_use+text, tool_result (skipped), assistant text.

        The tool_result user message is skipped (no text blocks), so the two
        assistant messages become consecutive and get merged.
        """
        agent = _make_agent()
        tool_use_block = SimpleNamespace(type="tool_use", id="t1", name="route_to_data_agent", input={"query": "test"})
        text_block = SimpleNamespace(type="text", text="Let me check")
        agent.conversation_history = [
            {"role": "user", "content": "Show my events"},
            {"role": "assistant", "content": [text_block, tool_use_block]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "{}"}]},
            {"role": "assistant", "content": "Here are your events."},
        ]
        result = agent._text_history()
        # tool_result skipped -> two assistant messages merge
        assert len(result) == 2
        assert result[0]["content"] == "Show my events"
        assert "Let me check" in result[1]["content"]
        assert "Here are your events." in result[1]["content"]
