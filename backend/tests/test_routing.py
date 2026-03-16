"""Orchestrator routing unit tests.

Verifies that the orchestrator correctly routes user messages to the right
specialist agent (data_agent vs content_agent vs admin_agent vs concierge)
without making real LLM calls.

Each test intercepts ``anthropic.AsyncAnthropic.messages.create`` and returns
a synthetic ``tool_use`` response for the expected routing tool, then asserts
that ``OrchestratorAgent.process_message`` returns the correct ``agent_used``
value.

Run with:
    python -m pytest tests/test_routing.py -v
"""

import asyncio
import json
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.orchestrator import OrchestratorAgent


# ---------------------------------------------------------------------------
# Helpers — build synthetic Anthropic SDK-style responses
# ---------------------------------------------------------------------------


def _make_tool_use_response(tool_name: str, query: str = "test") -> MagicMock:
    """Return a mock that looks like an Anthropic ``messages.create`` response
    with ``stop_reason == "tool_use"`` and a single tool_use content block."""
    tool_block = SimpleNamespace(
        type="tool_use",
        id="tu_test_001",
        name=tool_name,
        input={"query": query},
    )
    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [tool_block]
    return response


def _make_text_response(text: str) -> MagicMock:
    """Return a mock that looks like a direct text response (no tool use)."""
    text_block = SimpleNamespace(type="text", text=text)
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [text_block]
    return response


def _make_agent_result(text: str = "Agent reply.", agent_key: str = "data_agent") -> dict:
    """Return a minimal agent result dict matching what DataAgent / ContentAgent return."""
    return {
        "text": text,
        "agent_used": agent_key,
        "chart_data": None,
        "event_card": None,
        "event_cards": None,
        "poll_cards": None,
        "content_articles": None,
        "content_html": None,
        "requires_confirmation": False,
        "confirmation_summary": None,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def orchestrator():
    """Return an OrchestratorAgent with real Anthropic client mocked out."""
    with patch("app.agents.orchestrator.anthropic.AsyncAnthropic"):
        agent = OrchestratorAgent()
    return agent


# ---------------------------------------------------------------------------
# Routing tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestOrchestratorRouting:
    """Unit tests for orchestrator routing decisions — no real LLM calls."""

    # -----------------------------------------------------------------------
    # Blog post → content_agent
    # -----------------------------------------------------------------------

    async def test_blog_post_routes_to_content_agent(self, orchestrator):
        """'Help me write a blog post based on my most recent event' → content_agent."""
        routing_response = _make_tool_use_response("route_to_content_agent")
        agent_result = _make_agent_result("Here is your blog post draft…", "content_agent")

        orchestrator.client.messages.create = AsyncMock(return_value=routing_response)
        orchestrator.content_agent.run = AsyncMock(return_value=agent_result)

        result = await orchestrator.process_message(
            "Help me write a blog post based on my most recent event"
        )

        assert result["agent_used"] == "content_agent"
        orchestrator.content_agent.run.assert_awaited_once()
        # Ensure data_agent was NOT called
        orchestrator.data_agent.run = AsyncMock()  # should never be awaited
        assert not orchestrator.data_agent.run.called

    # -----------------------------------------------------------------------
    # "Show blog posts" → data_agent  (viewing, not writing)
    # -----------------------------------------------------------------------

    async def test_show_blog_posts_routes_to_data_agent(self, orchestrator):
        """'Show me the most recent blog posts' → data_agent (viewing existing content)."""
        routing_response = _make_tool_use_response("route_to_data_agent")
        agent_result = _make_agent_result("Here are the most recent blog posts…", "data_agent")

        orchestrator.client.messages.create = AsyncMock(return_value=routing_response)
        orchestrator.data_agent.run = AsyncMock(return_value=agent_result)

        result = await orchestrator.process_message("Show me the most recent blog posts")

        assert result["agent_used"] == "data_agent"
        orchestrator.data_agent.run.assert_awaited_once()

    # -----------------------------------------------------------------------
    # Draft email → content_agent
    # -----------------------------------------------------------------------

    async def test_draft_follow_up_email_routes_to_content_agent(self, orchestrator):
        """'Help me draft a follow-up email' → content_agent."""
        routing_response = _make_tool_use_response("route_to_content_agent")
        agent_result = _make_agent_result("Here is your follow-up email…", "content_agent")

        orchestrator.client.messages.create = AsyncMock(return_value=routing_response)
        orchestrator.content_agent.run = AsyncMock(return_value=agent_result)

        result = await orchestrator.process_message("Help me draft a follow-up email for attendees")

        assert result["agent_used"] == "content_agent"
        orchestrator.content_agent.run.assert_awaited_once()

    # -----------------------------------------------------------------------
    # Attendance trends → data_agent
    # -----------------------------------------------------------------------

    async def test_attendance_trends_routes_to_data_agent(self, orchestrator):
        """'What are my attendance trends?' → data_agent."""
        routing_response = _make_tool_use_response("route_to_data_agent")
        agent_result = _make_agent_result("Attendance has grown 12 % over 6 months.", "data_agent")

        orchestrator.client.messages.create = AsyncMock(return_value=routing_response)
        orchestrator.data_agent.run = AsyncMock(return_value=agent_result)

        result = await orchestrator.process_message("What are my attendance trends?")

        assert result["agent_used"] == "data_agent"
        orchestrator.data_agent.run.assert_awaited_once()

    # -----------------------------------------------------------------------
    # How-to → concierge (search_knowledge_base)
    # -----------------------------------------------------------------------

    async def test_how_to_question_routes_to_concierge(self, orchestrator):
        """'How do I set up polls?' → concierge (search_knowledge_base tool)."""
        import sys
        import types

        routing_response = _make_tool_use_response("search_knowledge_base", "how to set up polls")
        kb_result_response = _make_text_response("To set up polls in ON24, go to…")

        # First call = orchestrator routing; second call = Haiku synthesis
        orchestrator.client.messages.create = AsyncMock(
            side_effect=[routing_response, kb_result_response]
        )

        # The handler does a dynamic ``from app.db.knowledge_base import query_knowledge``
        # inside the if-branch. Inject a fake module so the import resolves without DB.
        fake_kb = types.ModuleType("app.db.knowledge_base")
        fake_kb.query_knowledge = AsyncMock(return_value=[{"title": "Polls", "content": "Set up polls via…"}])
        sys.modules["app.db.knowledge_base"] = fake_kb

        try:
            result = await orchestrator.process_message("How do I set up polls?")
        finally:
            sys.modules.pop("app.db.knowledge_base", None)

        assert result["agent_used"] == "concierge"

    # -----------------------------------------------------------------------
    # Direct text response (no tool use) — agent_used is None
    # -----------------------------------------------------------------------

    async def test_direct_response_has_no_agent_used(self, orchestrator):
        """When orchestrator responds directly (no routing), agent_used must be None."""
        direct_response = _make_text_response("I'm focused on helping you with ON24.")

        orchestrator.client.messages.create = AsyncMock(return_value=direct_response)

        result = await orchestrator.process_message("What's the weather today?")

        assert result["agent_used"] is None
        assert "text" in result

    # -----------------------------------------------------------------------
    # Write social post → content_agent (content creation keyword)
    # -----------------------------------------------------------------------

    async def test_write_social_post_routes_to_content_agent(self, orchestrator):
        """'Write a social post about our last webinar' → content_agent."""
        routing_response = _make_tool_use_response("route_to_content_agent")
        agent_result = _make_agent_result("Here's a LinkedIn post for you…", "content_agent")

        orchestrator.client.messages.create = AsyncMock(return_value=routing_response)
        orchestrator.content_agent.run = AsyncMock(return_value=agent_result)

        result = await orchestrator.process_message(
            "Write a social media post about our last webinar"
        )

        assert result["agent_used"] == "content_agent"
        orchestrator.content_agent.run.assert_awaited_once()

    # -----------------------------------------------------------------------
    # Create event → admin_agent
    # -----------------------------------------------------------------------

    async def test_create_event_routes_to_admin_agent(self, orchestrator):
        """'Create a new webinar for next month' → admin_agent."""
        routing_response = _make_tool_use_response("route_to_admin_agent")
        admin_result = {
            "text": "I'll need to confirm before creating the event.",
            "agent_used": "admin_agent",
            "chart_data": None,
            "requires_confirmation": True,
            "confirmation_summary": "Create webinar on 2026-04-01",
        }

        orchestrator.client.messages.create = AsyncMock(return_value=routing_response)
        orchestrator.admin_agent.run = AsyncMock(return_value=admin_result)

        result = await orchestrator.process_message("Create a new webinar for next month")

        assert result["agent_used"] == "admin_agent"
        orchestrator.admin_agent.run.assert_awaited_once()

    # -----------------------------------------------------------------------
    # "Based on my most recent event" blog → content_agent (NOT data first)
    # -----------------------------------------------------------------------

    async def test_blog_based_on_event_does_not_call_data_agent_first(self, orchestrator):
        """Blog post request referencing a specific event must NOT call data_agent first."""
        routing_response = _make_tool_use_response("route_to_content_agent")
        agent_result = _make_agent_result("Blog draft…", "content_agent")

        orchestrator.client.messages.create = AsyncMock(return_value=routing_response)
        orchestrator.content_agent.run = AsyncMock(return_value=agent_result)
        orchestrator.data_agent.run = AsyncMock()  # should never be called

        result = await orchestrator.process_message(
            "Help me write a blog post based on my most recent event"
        )

        assert result["agent_used"] == "content_agent"
        orchestrator.data_agent.run.assert_not_awaited()
        orchestrator.content_agent.run.assert_awaited_once()

    # -----------------------------------------------------------------------
    # Top events by engagement → data_agent
    # -----------------------------------------------------------------------

    async def test_top_events_by_engagement_routes_to_data_agent(self, orchestrator):
        """'Show top events by engagement' → data_agent."""
        routing_response = _make_tool_use_response("route_to_data_agent")
        agent_result = _make_agent_result("Top 10 events by engagement…", "data_agent")

        orchestrator.client.messages.create = AsyncMock(return_value=routing_response)
        orchestrator.data_agent.run = AsyncMock(return_value=agent_result)

        result = await orchestrator.process_message("Show me the top events by engagement score")

        assert result["agent_used"] == "data_agent"
        orchestrator.data_agent.run.assert_awaited_once()
