"""Tests for generate_suggestions() chip logic and pre-warm constants.

Covers:
1. Markdown bold/italic stripping from chip labels (** and * removal).
2. Funnel chip replacement when "no funnel tags found" is in response text.
3. Poll chip injection when "no poll results for" is in response text.
4. Pre-warm constant sizes: TRENDS_CHIP_PROMPTS == 8, EXPLORE_CONTENT_PROMPTS == 6.

All LLM calls to Anthropic are mocked; no real network traffic occurs.

Architecture note: The funnel/poll chip injection logic lives inside the
``_send_suggestions`` nested closure in ``websocket_chat``, *after* the
``generate_suggestions()`` call. Since ``_send_suggestions`` is not importable
directly, these tests:
  - Unit-test ``generate_suggestions()`` for the markdown-stripping behaviour.
  - Test the injection rules via ``_apply_chip_overrides`` — a pure helper
    that mirrors the production logic, declared here for testability.
  - Verify ``TRENDS_CHIP_PROMPTS`` / ``EXPLORE_CONTENT_PROMPTS`` sizes directly.

Run with:
    python -m pytest tests/test_chip_generation.py -v
"""

import json
import re
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.chat import generate_suggestions, _extract_inline_options
from app.services.data_prefetch import TRENDS_CHIP_PROMPTS, EXPLORE_CONTENT_PROMPTS


# ---------------------------------------------------------------------------
# Helper: mirror of the post-generate_suggestions injection logic in
# _send_suggestions (websocket_chat).  Keep in sync with chat.py.
# ---------------------------------------------------------------------------

_FUNNEL_CHIP_1 = "How do I add funnel tags?"
_FUNNEL_CHIP_2 = (
    "Classify my events into TOFU/MOFU/BOFU using their titles — no tags needed. "
    "TOFU = awareness, intro, overview, trends, keynote, demo. "
    "MOFU = deep-dive, how-to, comparison, case study, best practices, workshop. "
    "BOFU = customer success, training, onboarding, advanced, certification, ROI. "
    "Fetch events from the last 30 days, classify each, sum registrants per stage, "
    "and show a funnel chart. Add note: Approximate funnel based on event title classification."
)
_POLL_CHIP = "Show polls for the most recent event that had polls"


def _apply_chip_overrides(
    suggestions: list[str],
    response_text: str,
    agent_used: str | None,
) -> list[str]:
    """Mirror the injection rules from _send_suggestions in chat.py.

    Called AFTER generate_suggestions() returns the base chip list. Applies:
    1. Poll chip injection when "no poll results for" is in response text.
    2. Funnel chip replacement when "no funnel tags found" is in response text.
    3. "Suggest something" injection for content_agent prompts asking for direction.
    4. "View proposed calendar" injection for content calendar responses.
    """
    text_lower = response_text.lower()

    # Poll chip injection
    if "no poll results for" in text_lower:
        suggestions = [_POLL_CHIP] + [s for s in suggestions if s != _POLL_CHIP][:4]

    # Funnel chip replacement
    if "no funnel tags found" in text_lower:
        suggestions = [_FUNNEL_CHIP_1, _FUNNEL_CHIP_2]

    # "Suggest something" for content agent asking for direction
    if agent_used == "content_agent" and any(
        kw in text_lower for kw in ("pick a topic", "what topic", "let me know", "which topic", "just let me know")
    ):
        suggestions = ["Suggest something"] + [s for s in suggestions if s != "Suggest something"][:4]

    # "View proposed calendar" for content calendar responses
    if agent_used == "content_agent" and any(
        kw in text_lower for kw in ("tofu", "mofu", "bofu", "funnel stage", "content calendar", "webinar plan", "proposed event")
    ):
        cal_chip = "View proposed calendar"
        if cal_chip not in suggestions:
            suggestions = [cal_chip] + [s for s in suggestions if s != cal_chip][:4]

    return suggestions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_haiku_response(chips: list[str]) -> MagicMock:
    """Return a mock Anthropic message response whose text is a JSON array."""
    text_block = SimpleNamespace(text=json.dumps(chips))
    response = MagicMock()
    response.content = [text_block]
    return response


# ---------------------------------------------------------------------------
# 1. Markdown stripping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestChipMarkdownStripping:
    """Verify that ** and * markers are removed from chip labels."""

    async def test_bold_markers_stripped_from_chip_labels(self):
        """Chips containing **label** must have the ** removed."""
        # Simulate Haiku returning chips with bold markers (can happen when
        # the LLM echoes bold text from the response into chip suggestions).
        raw_chips = ["**Timezone**", "**Event type**: Webcast"]
        mock_response = _mock_haiku_response(raw_chips)

        with patch("app.api.chat.anthropic.AsyncAnthropic") as MockClient:
            MockClient.return_value.messages.create = AsyncMock(return_value=mock_response)
            suggestions = await generate_suggestions(
                user_message="Create an event",
                response_text="Some response text",
                agent_used="admin_agent",
            )

        # context_chips are the first 2 items; they should have no ** markers
        context_chips = suggestions[:2]
        for chip in context_chips:
            assert "**" not in chip, f"Chip still contains **: {chip!r}"
            assert "*" not in chip, f"Chip still contains *: {chip!r}"

    async def test_italic_markers_stripped_from_chip_labels(self):
        """Chips containing *label* (single asterisk) must have * removed."""
        raw_chips = ["*Attendees*", "*Registration count*"]
        mock_response = _mock_haiku_response(raw_chips)

        with patch("app.api.chat.anthropic.AsyncAnthropic") as MockClient:
            MockClient.return_value.messages.create = AsyncMock(return_value=mock_response)
            suggestions = await generate_suggestions(
                user_message="Show me KPIs",
                response_text="Here are your KPIs",
                agent_used="data_agent",
            )

        context_chips = suggestions[:2]
        for chip in context_chips:
            assert "*" not in chip, f"Chip still contains *: {chip!r}"

    async def test_clean_chip_labels_are_preserved(self):
        """Chip labels without markdown markers should be returned unchanged."""
        raw_chips = ["Show attendance trends", "Compare Q3 vs Q4"]
        mock_response = _mock_haiku_response(raw_chips)

        with patch("app.api.chat.anthropic.AsyncAnthropic") as MockClient:
            MockClient.return_value.messages.create = AsyncMock(return_value=mock_response)
            suggestions = await generate_suggestions(
                user_message="Any data question",
                response_text="Some response",
                agent_used="data_agent",
            )

        assert suggestions[0] == "Show attendance trends"
        assert suggestions[1] == "Compare Q3 vs Q4"

    async def test_mixed_markdown_and_clean_chips(self):
        """Mixed chips: bold markers stripped, clean chips left intact."""
        raw_chips = ["**Timezone**", "Show engagement score"]
        mock_response = _mock_haiku_response(raw_chips)

        with patch("app.api.chat.anthropic.AsyncAnthropic") as MockClient:
            MockClient.return_value.messages.create = AsyncMock(return_value=mock_response)
            suggestions = await generate_suggestions(
                user_message="Create a webinar",
                response_text="Here is your new event",
                agent_used="admin_agent",
            )

        context_chips = suggestions[:2]
        assert "**" not in context_chips[0]
        assert context_chips[1] == "Show engagement score"


# ---------------------------------------------------------------------------
# 2. Funnel chip injection
#    The injection happens in _send_suggestions (nested in websocket_chat),
#    not in generate_suggestions(). We test the injection rules via the
#    _apply_chip_overrides helper defined at the top of this file, which
#    mirrors the production logic exactly.
# ---------------------------------------------------------------------------


class TestFunnelChipInjection:
    """Verify funnel chips are injected when 'no funnel tags found' is in response."""

    def test_funnel_chips_injected_on_no_funnel_tags(self):
        """When response contains 'no funnel tags found', inject funnel chips."""
        base_chips = ["Show attendance trends", "Top events by engagement", "How do I...?", "Content performance insights", "Home"]
        response_text = (
            "No funnel tags found for your events in the last 30 days. "
            "Add funnel tags (TOFU/MOFU/BOFU) in ON24 to enable funnel analysis."
        )

        result = _apply_chip_overrides(base_chips, response_text, "data_agent")

        assert result[0] == _FUNNEL_CHIP_1

    def test_funnel_chips_include_title_classification_chip(self):
        """Funnel chip injection sets second chip to title-classification prompt."""
        base_chips = ["Chip A", "Chip B", "How do I...?", "Content performance insights", "Home"]
        response_text = "No funnel tags found in your event data."

        result = _apply_chip_overrides(base_chips, response_text, "data_agent")

        assert len(result) >= 2
        assert "Classify" in result[1] or "TOFU" in result[1]

    def test_normal_response_does_not_inject_funnel_chips(self):
        """When response does not mention 'no funnel tags', funnel chips are NOT injected."""
        base_chips = ["Show line chart", "Show as table", "How do I...?", "Content performance insights", "Home"]
        response_text = "Here are events by funnel stage: TOFU 5, MOFU 3, BOFU 2."

        result = _apply_chip_overrides(base_chips, response_text, "data_agent")

        assert result[0] != _FUNNEL_CHIP_1

    def test_funnel_chips_replace_existing_context_chips_with_exactly_2(self):
        """Funnel injection replaces all chips with exactly 2 specific funnel chips."""
        base_chips = ["Any chip 1", "Any chip 2", "How do I...?", "Content performance insights", "Home"]
        response_text = "No funnel tags found for these events."

        result = _apply_chip_overrides(base_chips, response_text, "data_agent")

        assert len(result) == 2
        assert result[0] == _FUNNEL_CHIP_1
        assert result[1] == _FUNNEL_CHIP_2

    def test_funnel_detection_is_case_insensitive(self):
        """'NO FUNNEL TAGS FOUND' (uppercase) also triggers funnel injection."""
        base_chips = ["Chip X", "Chip Y"]
        response_text = "NO FUNNEL TAGS FOUND for your events."

        result = _apply_chip_overrides(base_chips, response_text, "data_agent")

        assert result[0] == _FUNNEL_CHIP_1


# ---------------------------------------------------------------------------
# 3. Poll chip injection
#    Same architectural note as funnel chips: injection lives in
#    _send_suggestions, tested via _apply_chip_overrides.
# ---------------------------------------------------------------------------


class TestPollChipInjection:
    """Verify poll chip is injected to the front when 'no poll results for' is in response."""

    def test_poll_chip_injected_on_no_poll_results(self):
        """When response contains 'no poll results for', inject poll chip at front."""
        base_chips = ["Show event KPIs", "Compare attendance", "How do I...?", "Content performance insights", "Home"]
        response_text = (
            "No poll results for event 12345 — this event may not have had polls, "
            "or the poll data has not been collected yet."
        )

        result = _apply_chip_overrides(base_chips, response_text, "data_agent")

        assert result[0] == _POLL_CHIP

    def test_poll_chip_not_duplicated(self):
        """The poll chip should appear exactly once even if it was already in the list."""
        base_chips = [_POLL_CHIP, "Event KPIs", "How do I...?", "Content performance insights", "Home"]
        response_text = "No poll results for event 99999."

        result = _apply_chip_overrides(base_chips, response_text, "data_agent")

        count = result.count(_POLL_CHIP)
        assert count == 1, f"Poll chip appears {count} times; expected exactly 1"

    def test_normal_response_does_not_inject_poll_chip(self):
        """When response has poll results, poll chip is NOT injected at front."""
        base_chips = ["Show as pie chart", "Compare events", "How do I...?", "Content performance insights", "Home"]
        response_text = "Poll 1: 'Was this useful?' — Yes: 72%, No: 28%."

        result = _apply_chip_overrides(base_chips, response_text, "data_agent")

        assert result[0] != _POLL_CHIP

    def test_poll_chip_at_front_caps_list_at_5(self):
        """Poll chip is prepended; remaining chips capped so total is <= 5."""
        base_chips = ["Chip A", "Chip B", "How do I...?", "Content performance insights", "Home"]
        response_text = "No poll results for this event."

        result = _apply_chip_overrides(base_chips, response_text, "data_agent")

        assert result[0] == _POLL_CHIP
        assert len(result) <= 5

    def test_poll_detection_is_case_insensitive(self):
        """'No Poll Results For' (mixed case) also triggers poll chip injection."""
        base_chips = ["Chip A", "Chip B"]
        response_text = "No Poll Results For event 888."

        result = _apply_chip_overrides(base_chips, response_text, "data_agent")

        assert result[0] == _POLL_CHIP


# ---------------------------------------------------------------------------
# 4. Pre-warm constants
# ---------------------------------------------------------------------------


class TestPreWarmConstants:
    """Verify the chip pre-warm prompt lists have the expected number of entries."""

    def test_trends_chip_prompts_has_8_entries(self):
        """TRENDS_CHIP_PROMPTS must contain exactly 8 (label, prompt) tuples."""
        assert len(TRENDS_CHIP_PROMPTS) == 8, (
            f"Expected 8 TRENDS_CHIP_PROMPTS entries, got {len(TRENDS_CHIP_PROMPTS)}"
        )

    def test_explore_content_prompts_has_6_entries(self):
        """EXPLORE_CONTENT_PROMPTS must contain exactly 6 (label, prompt) tuples."""
        assert len(EXPLORE_CONTENT_PROMPTS) == 6, (
            f"Expected 6 EXPLORE_CONTENT_PROMPTS entries, got {len(EXPLORE_CONTENT_PROMPTS)}"
        )

    def test_trends_chip_prompts_are_tuples_of_strings(self):
        """Every entry in TRENDS_CHIP_PROMPTS must be a (str, str) tuple."""
        for i, entry in enumerate(TRENDS_CHIP_PROMPTS):
            assert isinstance(entry, tuple), f"Entry {i} is not a tuple: {entry!r}"
            assert len(entry) == 2, f"Entry {i} tuple length is {len(entry)}, expected 2"
            label, prompt = entry
            assert isinstance(label, str) and label, f"Entry {i} label is not a non-empty str"
            assert isinstance(prompt, str) and prompt, f"Entry {i} prompt is not a non-empty str"

    def test_explore_content_prompts_are_tuples_of_strings(self):
        """Every entry in EXPLORE_CONTENT_PROMPTS must be a (str, str) tuple."""
        for i, entry in enumerate(EXPLORE_CONTENT_PROMPTS):
            assert isinstance(entry, tuple), f"Entry {i} is not a tuple: {entry!r}"
            label, prompt = entry
            assert isinstance(label, str) and label
            assert isinstance(prompt, str) and prompt

    def test_trends_chip_labels_are_unique(self):
        """All trend chip labels must be unique (no duplicates)."""
        labels = [label for label, _ in TRENDS_CHIP_PROMPTS]
        assert len(labels) == len(set(labels)), f"Duplicate labels: {labels}"

    def test_explore_content_labels_are_unique(self):
        """All explore-content chip labels must be unique."""
        labels = [label for label, _ in EXPLORE_CONTENT_PROMPTS]
        assert len(labels) == len(set(labels)), f"Duplicate labels: {labels}"

    def test_trends_chip_labels_known_entries(self):
        """Key expected labels must be present in TRENDS_CHIP_PROMPTS."""
        labels = {label for label, _ in TRENDS_CHIP_PROMPTS}
        expected = {
            "Attendance over time",
            "Registrations over time",
            "Engagement scores over time",
            "Top events by engagement",
            "Poll trends",
        }
        missing = expected - labels
        assert not missing, f"Missing expected TRENDS_CHIP_PROMPTS labels: {missing}"

    def test_explore_content_labels_known_entries(self):
        """Key expected labels must be present in EXPLORE_CONTENT_PROMPTS."""
        labels = {label for label, _ in EXPLORE_CONTENT_PROMPTS}
        expected = {
            "Key Takeaways",
            "Blog Posts",
            "eBooks",
            "FAQs",
            "Follow-up Emails",
            "Social Media",
        }
        missing = expected - labels
        assert not missing, f"Missing expected EXPLORE_CONTENT_PROMPTS labels: {missing}"


# ---------------------------------------------------------------------------
# 5. Structural / output shape tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSuggestionsOutputShape:
    """Verify generate_suggestions() always returns a non-empty list ending with 'Home'."""

    async def test_suggestions_always_ends_with_home(self):
        """The last chip must always be 'Home'."""
        mock_response = _mock_haiku_response(["Chip A", "Chip B"])

        with patch("app.api.chat.anthropic.AsyncAnthropic") as MockClient:
            MockClient.return_value.messages.create = AsyncMock(return_value=mock_response)
            suggestions = await generate_suggestions(
                user_message="Any question",
                response_text="Any response",
                agent_used="data_agent",
            )

        assert suggestions[-1] == "Home"

    async def test_suggestions_includes_agent_switch_chips(self):
        """For data_agent, switch chips 'How do I...?' and 'Content performance insights' are included."""
        mock_response = _mock_haiku_response(["Chip X", "Chip Y"])

        with patch("app.api.chat.anthropic.AsyncAnthropic") as MockClient:
            MockClient.return_value.messages.create = AsyncMock(return_value=mock_response)
            suggestions = await generate_suggestions(
                user_message="Attendance KPIs",
                response_text="Attendance was 1000.",
                agent_used="data_agent",
            )

        assert "How do I...?" in suggestions
        assert "Content performance insights" in suggestions

    async def test_suggestions_returns_list_on_malformed_llm_response(self):
        """If Haiku returns non-JSON text, generate_suggestions still returns a list with switch chips."""
        bad_block = SimpleNamespace(text="Sorry, I can't do that.")
        bad_response = MagicMock()
        bad_response.content = [bad_block]

        with patch("app.api.chat.anthropic.AsyncAnthropic") as MockClient:
            MockClient.return_value.messages.create = AsyncMock(return_value=bad_response)
            suggestions = await generate_suggestions(
                user_message="Anything",
                response_text="Any answer",
                agent_used="data_agent",
            )

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert suggestions[-1] == "Home"

    async def test_concierge_suggestions_count(self):
        """Concierge mode returns exactly 2 context chips + 2 switch chips + Home = 5 total."""
        mock_response = _mock_haiku_response(["How do I add polls?", "How do I view analytics?"])

        with patch("app.api.chat.anthropic.AsyncAnthropic") as MockClient:
            MockClient.return_value.messages.create = AsyncMock(return_value=mock_response)
            suggestions = await generate_suggestions(
                user_message="How do I set up a webinar?",
                response_text="To set up a webinar, navigate to Elite Studio…",
                agent_used="concierge",
            )

        # concierge switch chips: "Explore my event data", "Content performance insights"
        assert "Explore my event data" in suggestions
        assert "Content performance insights" in suggestions
        assert suggestions[-1] == "Home"


# ---------------------------------------------------------------------------
# 6. _extract_inline_options unit tests
# ---------------------------------------------------------------------------


class TestExtractInlineOptions:
    """Unit tests for the _extract_inline_options helper function."""

    def test_bullet_list_extracted(self):
        """A response ending in 2–5 bullet points returns those as chips."""
        text = (
            "Here are some options:\n"
            "- Extend to 6 months — push the calendar horizon\n"
            "- Focus on BOFU — heavier bottom-of-funnel weighting\n"
            "- Switch to engagement metric — use engagement score instead"
        )
        result = _extract_inline_options(text)
        assert result is not None
        assert len(result) == 3

    def test_numbered_list_extracted(self):
        """Numbered lists are also extracted as inline options."""
        text = (
            "Choose a topic:\n"
            "1. AI in Marketing — latest trends\n"
            "2. Customer Success — retention strategies\n"
            "3. Product Demo — new features walkthrough"
        )
        result = _extract_inline_options(text)
        assert result is not None
        assert len(result) == 3

    def test_single_item_returns_none(self):
        """A single bullet point must NOT be promoted to chips (needs 2–5)."""
        text = "Here is one option:\n- Show as pie chart"
        result = _extract_inline_options(text)
        assert result is None

    def test_ten_items_returns_none(self):
        """Ten or more items must NOT be promoted (max is 9)."""
        lines = "\n".join(f"- Option {i}" for i in range(1, 11))
        text = f"Choose one:\n{lines}"
        result = _extract_inline_options(text)
        assert result is None

    def test_nine_items_returns_list(self):
        """Nine items should be promoted (decision tree Q1 has 9 options)."""
        lines = "\n".join(f"- Option {i}" for i in range(1, 10))
        text = f"Choose one:\n{lines}"
        result = _extract_inline_options(text)
        assert result is not None
        assert len(result) == 9

    def test_labels_truncated_after_dash(self):
        """Label is the short part before ' — ' separator."""
        text = "Options:\n- Extend horizon — push out to 6 or 12 months\n- Shift weighting — BOFU focus"
        result = _extract_inline_options(text)
        assert result is not None
        assert "Extend horizon" == result[0]
        assert "Shift weighting" == result[1]

    def test_empty_text_returns_none(self):
        """Empty string should return None (no items found)."""
        result = _extract_inline_options("")
        assert result is None
