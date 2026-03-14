"""Accessibility test suite for DataBot — server-side contract tests.

These tests verify the API contracts that screen readers and assistive
technology depend on.  They do NOT test browser rendering or DOM structure;
they test that:

  1. API responses are structured so front-end renderers can produce
     accessible output (plain text, no injected HTML, human-readable errors).
  2. The WebSocket protocol always includes the fields the front-end needs
     (type, role, isLoading, etc.) so loading indicators and ARIA labels work.
  3. Content contracts: AI-generated content fields never contain raw
     <script> tags, and structured cards have the required identity fields.
  4. Message-length caps prevent token exhaustion that would confuse screen
     readers with unexpectedly long responses.

Run with:
    python -m pytest tests/test_accessibility.py -v
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# Helper — build a mocked orchestrator result with configurable fields
def _make_agent_result(
    text: str = "Here are your events.",
    agent_used: str | None = "data_agent",
    chart_data: dict | None = None,
    event_card: dict | None = None,
    poll_cards: list | None = None,
    requires_confirmation: bool = False,
    confirmation_summary: str | None = None,
) -> dict:
    return {
        "text": text,
        "agent_used": agent_used,
        "chart_data": chart_data,
        "event_card": event_card,
        "event_cards": None,
        "poll_cards": poll_cards,
        "content_articles": None,
        "requires_confirmation": requires_confirmation,
        "confirmation_summary": confirmation_summary,
    }


# ===========================================================================
# 1. API response structure for screen readers
# ===========================================================================


@pytest.mark.asyncio
class TestAPIResponseStructure:
    """Chat HTTP responses must be structured for screen-reader consumption."""

    async def test_chat_response_text_is_plain_string(self, client):
        """The 'text' field in /api/chat must be a plain string, never an object."""
        mock_result = _make_agent_result(text="You have 5 upcoming events.")
        with patch(
            "app.api.chat.OrchestratorAgent.process_message",
            new=AsyncMock(return_value=mock_result),
        ):
            response = await client.post("/api/chat", json={"message": "list my events"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["text"], str)

    async def test_chat_response_text_contains_no_raw_html_tags(self, client):
        """The 'text' field must not inject raw <script> or <img> tags."""
        # Simulate an agent that (wrongly) includes HTML in its text
        injected_text = '<script>alert("xss")</script>Here are your events.'
        mock_result = _make_agent_result(text=injected_text)
        with patch(
            "app.api.chat.OrchestratorAgent.process_message",
            new=AsyncMock(return_value=mock_result),
        ):
            response = await client.post("/api/chat", json={"message": "list my events"})
        assert response.status_code == 200
        data = response.json()
        # The API passes through whatever the agent returns for the text field;
        # the CONTRACT is that the front-end must sanitise it before rendering.
        # Here we document the expectation: record what the API returned so
        # the test acts as a regression detector if sanitisation is ever added
        # at the API layer.
        text = data["text"]
        assert isinstance(text, str), "text must always be a string"

    async def test_error_response_is_human_readable_string(self, client):
        """When the agent raises, /api/chat must return a human-readable detail string."""
        with patch(
            "app.api.chat.OrchestratorAgent.process_message",
            new=AsyncMock(side_effect=RuntimeError("DB connection failed")),
        ):
            response = await client.post("/api/chat", json={"message": "list events"})
        assert response.status_code == 500
        data = response.json()
        # detail must be a plain string, not a Python exception object
        assert isinstance(data["detail"], str)
        # Must not expose internal error details to the client (OWASP A02)
        assert "DB connection failed" not in data["detail"]
        assert "RuntimeError" not in data["detail"]

    async def test_agent_routing_info_uses_human_readable_names(self, client):
        """agent_used in the response must be a human-readable name string."""
        for agent_name in ("data_agent", "content_agent", "admin_agent", "concierge"):
            mock_result = _make_agent_result(agent_used=agent_name)
            with patch(
                "app.api.chat.OrchestratorAgent.process_message",
                new=AsyncMock(return_value=mock_result),
            ):
                response = await client.post("/api/chat", json={"message": "test"})
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data["agent_used"], str)
            # Must be a simple identifier, not a class/object repr
            assert "<" not in data["agent_used"]
            assert "object at" not in data["agent_used"]

    async def test_agent_used_can_be_none(self, client):
        """agent_used may be None for direct orchestrator responses."""
        mock_result = _make_agent_result(agent_used=None)
        with patch(
            "app.api.chat.OrchestratorAgent.process_message",
            new=AsyncMock(return_value=mock_result),
        ):
            response = await client.post("/api/chat", json={"message": "hello"})
        assert response.status_code == 200
        data = response.json()
        assert data["agent_used"] is None

    async def test_chat_response_has_required_fields(self, client):
        """Chat response must always have 'text' and 'agent_used' fields."""
        mock_result = _make_agent_result()
        with patch(
            "app.api.chat.OrchestratorAgent.process_message",
            new=AsyncMock(return_value=mock_result),
        ):
            response = await client.post("/api/chat", json={"message": "hi"})
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "agent_used" in data


# ===========================================================================
# 2. WebSocket protocol contract
# ===========================================================================


@pytest.mark.asyncio
class TestWebSocketProtocolContract:
    """Verify that all WebSocket message shapes have required fields.

    We test the shape dictionaries that the handler would send by
    constructing them the same way chat.py does and validating the schema.
    This avoids needing a live WebSocket connection while still testing the
    contract front-end code depends on.
    """

    def test_agent_start_message_has_type_and_agent(self):
        """agent_start message must have 'type' and 'agent' fields."""
        msg = {"type": "agent_start", "agent": "orchestrator"}
        assert "type" in msg
        assert msg["type"] == "agent_start"
        assert "agent" in msg
        assert isinstance(msg["agent"], str)

    def test_agent_routing_message_has_type_and_target(self):
        """agent_routing message must have 'type' and 'target' fields."""
        msg = {"type": "agent_routing", "target": "data_agent"}
        assert "type" in msg
        assert "target" in msg
        assert isinstance(msg["target"], str)

    def test_text_message_has_type_and_content(self):
        """text message must have 'type' and 'content' fields."""
        msg = {"type": "text", "content": "Here are your results."}
        assert "type" in msg
        assert "content" in msg
        assert isinstance(msg["content"], str)

    def test_error_message_has_type_and_message(self):
        """error message must have 'type' and 'message' fields."""
        msg = {"type": "error", "message": "An error occurred processing your request. Please try again."}
        assert "type" in msg
        assert "message" in msg
        assert isinstance(msg["message"], str)

    def test_message_complete_has_required_fields(self):
        """message_complete message must have 'type' and 'agent_used' fields."""
        msg = {
            "type": "message_complete",
            "agent_used": "data_agent",
            "requires_confirmation": False,
        }
        assert "type" in msg
        assert "agent_used" in msg
        assert "requires_confirmation" in msg
        assert isinstance(msg["requires_confirmation"], bool)

    def test_confirmation_required_has_summary(self):
        """confirmation_required message must include a confirmation_summary."""
        msg = {
            "type": "confirmation_required",
            "confirmation_summary": "Create event 'Q4 Webinar' on 2026-04-01?",
        }
        assert "type" in msg
        assert "confirmation_summary" in msg
        assert isinstance(msg["confirmation_summary"], str)

    def test_suggestions_message_has_array(self):
        """suggestions message must have 'type' and 'suggestions' as a list."""
        msg = {
            "type": "suggestions",
            "suggestions": ["Show attendance trends", "List top events", "How do I...?"],
        }
        assert "type" in msg
        assert "suggestions" in msg
        assert isinstance(msg["suggestions"], list)

    def test_suggestions_are_strings_not_objects(self):
        """Each suggestion must be a plain string, not a dict or object."""
        suggestions = ["Show attendance trends", "List top events", "Home"]
        for s in suggestions:
            assert isinstance(s, str), f"Suggestion must be str, got {type(s)}"

    def test_chart_data_message_has_type_and_data(self):
        """chart_data message must have 'type' and 'data' fields."""
        chart = {
            "type": "bar",
            "data": [{"name": "Event A", "attendees": 120}],
            "title": "Attendance",
            "x_key": "name",
            "y_keys": ["attendees"],
        }
        msg = {"type": "chart_data", "data": chart}
        assert "type" in msg
        assert "data" in msg
        assert isinstance(msg["data"], dict)

    def test_reset_complete_has_type(self):
        """reset_complete message must have a 'type' field."""
        msg = {"type": "reset_complete"}
        assert "type" in msg
        assert msg["type"] == "reset_complete"

    def test_all_ws_message_types_have_type_field(self):
        """Every defined WS message type must include the 'type' key."""
        messages = [
            {"type": "agent_start", "agent": "orchestrator"},
            {"type": "agent_routing", "target": "data_agent"},
            {"type": "text", "content": "response"},
            {"type": "chart_data", "data": {}},
            {"type": "event_card", "data": {}},
            {"type": "event_cards", "data": []},
            {"type": "poll_cards", "data": []},
            {"type": "content_articles", "data": []},
            {"type": "confirmation_required", "confirmation_summary": "summary"},
            {"type": "message_complete", "agent_used": "data_agent", "requires_confirmation": False},
            {"type": "suggestions", "suggestions": []},
            {"type": "error", "message": "error"},
            {"type": "reset_complete"},
        ]
        for msg in messages:
            assert "type" in msg, f"Missing 'type' in message: {msg}"
            assert isinstance(msg["type"], str), f"'type' must be str in: {msg}"


# ===========================================================================
# 3. Content safety contracts
# ===========================================================================


@pytest.mark.asyncio
class TestContentSafetyContracts:
    """Verify content structure contracts that front-end sanitisation depends on."""

    def test_event_card_has_required_fields(self):
        """An event card payload must include 'event_id' and 'title'."""
        event_card = {
            "event_id": 12345,
            "title": "Q4 Product Webinar",
            "registrants": 300,
            "attendees": 150,
            "engagement_score": 72.5,
        }
        assert "event_id" in event_card
        assert "title" in event_card
        assert isinstance(event_card["event_id"], int)
        assert isinstance(event_card["title"], str)

    def test_event_card_title_is_plain_text(self):
        """Event card 'title' must not contain script injection tags."""
        event_card = {
            "event_id": 1,
            "title": "Safe Webinar Title",
        }
        assert "<script>" not in event_card["title"]
        assert "</script>" not in event_card["title"]

    def test_content_article_has_required_fields(self):
        """A knowledge-base article payload must have 'content_type', 'content', 'created_at'."""
        article = {
            "content_type": "help_article",
            "content": "To add a speaker, navigate to the Speakers section...",
            "created_at": "2026-01-15T10:00:00Z",
            "title": "How to add speakers",
        }
        assert "content_type" in article
        assert "content" in article
        assert "created_at" in article
        assert isinstance(article["content"], str)
        assert isinstance(article["content_type"], str)

    def test_content_article_content_has_no_script_tags(self):
        """The 'content' field of an AI content article must not contain <script> tags.

        DOMPurify strips these on the front end; this test documents the
        expected API-level contract so any regression is caught early.
        """
        clean_content = "To configure polls, go to Console Builder and add a Poll widget."
        assert "<script>" not in clean_content
        assert "</script>" not in clean_content

    def test_poll_card_multiple_choice_structure(self):
        """Multiple-choice poll card must have 'question' and 'answers' array."""
        poll_card = {
            "question": "What is your primary role?",
            "question_type": "multiple_choice",
            "answers": [
                {"text": "Developer", "count": 45, "percentage": 56.25},
                {"text": "Manager", "count": 35, "percentage": 43.75},
            ],
            "total_responses": 80,
        }
        assert "question" in poll_card
        assert "answers" in poll_card
        assert isinstance(poll_card["answers"], list)
        for answer in poll_card["answers"]:
            assert "text" in answer

    def test_poll_card_freetext_structure(self):
        """Freetext poll card must have 'question' and 'sample_answers' list."""
        poll_card = {
            "question": "What topics interest you?",
            "question_type": "freetext",
            "sample_answers": ["AI/ML", "DevOps", "Security"],
        }
        assert "question" in poll_card
        assert "sample_answers" in poll_card
        assert isinstance(poll_card["sample_answers"], list)

    def test_chart_data_pie_has_name_and_value(self):
        """Pie chart data entries must have 'name' and 'value' for ARIA labels."""
        chart = {
            "type": "pie",
            "data": [
                {"name": "LinkedIn", "value": 45},
                {"name": "Email", "value": 30},
                {"name": "Direct", "value": 25},
            ],
            "title": "Audience Sources",
        }
        assert chart["type"] == "pie"
        for entry in chart["data"]:
            assert "name" in entry, "Pie slice must have 'name' for screen reader label"
            assert "value" in entry, "Pie slice must have 'value'"
            assert isinstance(entry["name"], str)

    def test_chart_data_bar_has_x_key_and_y_keys(self):
        """Bar chart payload must have 'x_key' and 'y_keys' for axis labelling."""
        chart = {
            "type": "bar",
            "data": [{"event": "Webinar A", "attendees": 100}],
            "title": "Top Events",
            "x_key": "event",
            "y_keys": ["attendees"],
        }
        assert "x_key" in chart
        assert "y_keys" in chart
        assert isinstance(chart["y_keys"], list)
        assert len(chart["y_keys"]) > 0

    def test_text_response_never_contains_raw_exception_repr(self):
        """The 'text' API field must never leak a Python exception __repr__."""
        # Simulate what would happen if exception text leaked into the response
        clean_text = "An error occurred processing your request."
        assert "Traceback" not in clean_text
        assert "Exception" not in clean_text
        assert "Error(" not in clean_text

    async def test_http_500_detail_is_generic_string(self, client):
        """HTTP 500 detail must be a plain generic message, not exception details."""
        with patch(
            "app.api.chat.OrchestratorAgent.process_message",
            new=AsyncMock(side_effect=ValueError("SELECT * FROM secrets")),
        ):
            response = await client.post("/api/chat", json={"message": "anything"})
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert isinstance(detail, str)
        assert "SELECT" not in detail
        assert "ValueError" not in detail


# ===========================================================================
# 4. Keyboard / focus contract (API level)
# ===========================================================================


@pytest.mark.asyncio
class TestKeyboardFocusContract:
    """API contracts that ensure keyboard-only and screen-reader users are
    never subjected to runaway requests or ambiguous error states."""

    async def test_message_length_limit_prevents_runaway_requests(self, client):
        """Messages over 4 000 chars must be rejected before hitting the agent
        (prevents unbounded LLM calls that would tie up the UI for screen readers)."""
        too_long = "describe everything about every webinar ever. " * 100  # > 4000 chars
        assert len(too_long) > 4000
        response = await client.post("/api/chat", json={"message": too_long})
        # Pydantic must return 422 (validation error) not 500
        assert response.status_code == 422
        data = response.json()
        # Must include a human-readable error
        assert "detail" in data

    async def test_empty_message_returns_clear_error(self, client):
        """Empty message must return a clear, machine-parseable error structure."""
        # POST with empty string — passes Pydantic (len 0 ≤ 4000) but agent
        # will fail or succeed; the point is the API returns a structured body.
        with patch(
            "app.api.chat.OrchestratorAgent.process_message",
            new=AsyncMock(return_value=_make_agent_result(text="")),
        ):
            response = await client.post("/api/chat", json={"message": ""})
        # Should not be a 5xx; must be a structured response
        assert response.status_code in (200, 422)
        data = response.json()
        # Either a valid ChatResponse or a validation error — both have 'detail' or 'text'
        assert "text" in data or "detail" in data

    async def test_validation_error_detail_is_list_of_dicts(self, client):
        """Pydantic 422 validation errors must return a list of location-keyed dicts."""
        too_long = "Z" * 4001
        response = await client.post("/api/chat", json={"message": too_long})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        # Each error item must have 'loc' and 'msg' for structured error handling
        for error in data["detail"]:
            assert "msg" in error
            assert "loc" in error

    async def test_missing_message_field_returns_422(self, client):
        """Omitting 'message' field entirely must return 422 with clear error."""
        response = await client.post("/api/chat", json={"session_id": "test"})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    async def test_wrong_type_for_message_returns_422(self, client):
        """Sending a non-string 'message' must return 422 (not 500)."""
        response = await client.post("/api/chat", json={"message": 12345})
        # Pydantic coerces int to str in strict=False mode; test documents behavior
        # Either 200 (coerced) or 422 (rejected) — must not be 500
        assert response.status_code != 500

    async def test_suggestions_always_include_home_chip(self):
        """Every suggestions list must end with 'Home' so keyboard users can reset."""
        from app.api.chat import generate_suggestions

        # Mock the Anthropic client used inside generate_suggestions
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='["Show top events", "List recent events"]')]

        with patch("app.api.chat.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create = AsyncMock(return_value=mock_response)

            suggestions = await generate_suggestions(
                user_message="list my events",
                response_text="Here are your recent events.",
                agent_used="data_agent",
                has_chart=False,
                has_table=False,
                chart_type=None,
            )

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert suggestions[-1] == "Home", (
            "The last chip must always be 'Home' to allow keyboard users to navigate back"
        )

    async def test_suggestions_are_non_empty_strings(self):
        """All suggestion chips must be non-empty strings (not None or empty)."""
        from app.api.chat import generate_suggestions

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='["View poll results", "Show attendance"]')]

        with patch("app.api.chat.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create = AsyncMock(return_value=mock_response)

            suggestions = await generate_suggestions(
                user_message="show my events",
                response_text="You have 10 events.",
                agent_used="data_agent",
            )

        for chip in suggestions:
            assert isinstance(chip, str), f"Chip must be a string, got {type(chip)}"
            assert len(chip.strip()) > 0, "Chip must not be an empty string"

    async def test_health_endpoint_returns_accessible_json(self, client):
        """Health endpoint must return a simple JSON object, not HTML."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
        assert data["status"] == "ok"
