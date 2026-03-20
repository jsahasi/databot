"""Orchestrator Agent: classifies user intent and routes to specialist agents."""

import json
import logging
from datetime import UTC, date
from pathlib import Path
from typing import Any

import anthropic

from app.agents.admin_agent import AdminAgent
from app.agents.content_agent import ContentAgent
from app.agents.data_agent import DataAgent
from app.config import settings

logger = logging.getLogger(__name__)

_ORCHESTRATOR_TEMPLATE = (Path(__file__).parent / "prompts" / "orchestrator.md").read_text()

import re


def _is_timeout(exc: Exception) -> bool:
    """Return True if the exception looks like a network/connect timeout."""
    msg = str(exc).lower()
    return any(kw in msg for kw in ("timeout", "connecttimeout", "timed out", "connect"))


def _log_error_to_inbox(context: str, user_query: str, error_detail: str) -> None:
    """Append a structured error entry to today's improvement-inbox file."""
    try:
        from datetime import datetime
        from pathlib import Path

        now = datetime.now(UTC)
        data_dir = Path("/app/data")
        data_dir.mkdir(parents=True, exist_ok=True)
        filename = data_dir / f"improvement-inbox-{now.strftime('%m-%d-%Y')}.txt"
        entry = f"\n{'=' * 60}\n[AUTO-ERROR] {now.isoformat()}\nContext: {context}\nUser query: {user_query[:300]}\nError: {error_detail[:500]}\n"
        with open(filename, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass  # Never let logging block the request


def _extract_proposed_events(text: str) -> list[dict] | None:
    """Extract proposed_events JSON from a fenced block in the content agent response."""
    # Try exact tag first, then any fenced block containing a JSON array with date/title keys
    for pattern in [
        r"```proposed_events\s*\n(.*?)```",
        r"```json\s*\n(\[.*?\])\s*```",
        r"```\s*\n(\[\s*\{.*?\]\s*)```",
    ]:
        m = re.search(pattern, text, re.DOTALL)
        if not m:
            continue
        try:
            events = json.loads(m.group(1).strip())
            if isinstance(events, list) and events and "title" in events[0]:
                logger.info(f"Matched proposed_events via pattern: {pattern}")
                return events
        except (json.JSONDecodeError, TypeError):
            continue
    logger.warning("No proposed_events JSON block found in content agent response")
    return None


def _build_orchestrator_prompt() -> str:
    today = date.today().strftime("%B %d, %Y")
    return f"Today's date is {today}.\n\n{_ORCHESTRATOR_TEMPLATE}"


class OrchestratorAgent:
    """Routes user messages to the appropriate specialist agent."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-6"
        self.data_agent = DataAgent()
        self.content_agent = ContentAgent()
        self.admin_agent = AdminAgent()
        self.conversation_history: list[dict] = []
        self.restriction_context: str = ""  # Set by chat.py per message
        self.image_block: dict | None = None  # Set by chat.py for vision

    # Tool for routing to sub-agents
    ROUTING_TOOLS = [
        {
            "name": "search_knowledge_base",
            "description": "Search the ON24 knowledge base (Zendesk help articles AND ON24 REST API v2 reference — 71 endpoints) for platform how-to questions, feature explanations, configuration guides, and API/integration questions. Use this for ANY question about how to do something on the ON24 platform OR about ON24 REST APIs, endpoints, integrations, and developer capabilities.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query about an ON24 platform feature or how-to"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "route_to_data_agent",
            "description": (
                "Route the user's question to the Data Agent for database queries, analytics, "
                "KPIs, attendance trends, and chart generation. "
                "Do NOT use this tool when the user asks to write, draft, or create content "
                "(blog posts, emails, social media posts, etc.) — even if they reference a specific "
                "event. Use route_to_content_agent instead."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The refined query to send to the Data Agent"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "route_to_content_agent",
            "description": (
                "Route to Content Agent for: content strategy, topic recommendations, AND "
                "writing/drafting ANY content (blog posts, emails, social media posts, FAQs, "
                "key takeaways, eBooks, webinar scripts). "
                "IMPORTANT: Use this tool even when the user says 'based on my most recent event', "
                "'based on event X', or references a specific event — the Content Agent has its own "
                "list_events and get_ai_content tools and will look up the event itself. "
                "Do NOT route to the Data Agent first to fetch event details for content writing."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The refined query for content creation or analysis"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "propose_content_calendar",
            "description": (
                "Use EXCLUSIVELY for requests to 'propose a content calendar', 'suggest a webinar schedule', "
                "'plan our webinar calendar', or any request to create a multi-event content plan. "
                "This tool first retrieves attendance trends and top-performing events from the data agent, "
                "then passes that data to the content agent to generate a strategic calendar proposal."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The original user request for the content calendar"},
                    "months": {"type": "integer", "description": "Number of months for the calendar (default 3, max 12)"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "route_to_admin_agent",
            "description": "Route to Admin Agent for event management and registration operations.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The refined query for admin operations"},
                },
                "required": ["query"],
            },
        },
    ]

    def _text_history(self) -> list[dict]:
        """Return conversation history with only plain-text turns (no tool_use/tool_result).

        The orchestrator's routing tool_use blocks must not be forwarded to sub-agents
        because they reference tools the sub-agents don't have, causing API 400 errors.
        Merges consecutive same-role messages to prevent API validation errors.
        """
        clean: list[dict] = []
        for msg in self.conversation_history:
            content = msg.get("content")
            text: str | None = None
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                # Keep only text blocks; skip tool_use and tool_result
                text_blocks = [b for b in content if isinstance(b, dict) and b.get("type") == "text"]
                if text_blocks:
                    text = " ".join(b.get("text", "") for b in text_blocks)
                # If content is a list of ContentBlock objects (Anthropic SDK), extract text
                elif all(hasattr(b, "type") for b in content):
                    texts = [b.text for b in content if hasattr(b, "text")]
                    if texts:
                        text = " ".join(texts)
            if not text or not text.strip():
                continue
            # Merge consecutive same-role messages (can happen when tool_result messages are stripped)
            if clean and clean[-1]["role"] == msg["role"]:
                clean[-1]["content"] += "\n" + text
            else:
                clean.append({"role": msg["role"], "content": text})
        return clean

    async def process_message(self, user_message: str, confirmed: bool = False) -> dict[str, Any]:
        """Process a user message through the orchestrator.

        Args:
            user_message: The message from the user.
            confirmed: Set to True when the user has confirmed a pending admin operation.

        Returns:
            {
                "text": str,
                "agent_used": str | None,
                "chart_data": dict | None,
                "requires_confirmation": bool,
                "confirmation_summary": str | None,
            }
        """
        import re as _re

        # If the user typed just a number (or ordinal word), check whether the last assistant
        # message contained a numbered list of options — and if so, expand the selection.
        _num_match = _re.fullmatch(
            r"\s*(?:(\d+)|one|first|two|second|three|third|four|fourth|five|fifth)\s*[.)]?\s*",
            user_message,
            _re.IGNORECASE,
        )
        if _num_match:
            _word_map = {"one": 1, "first": 1, "two": 2, "second": 2, "three": 3, "third": 3, "four": 4, "fourth": 4, "five": 5, "fifth": 5}
            _n = int(_num_match.group(1)) if _num_match.group(1) else _word_map.get(user_message.strip().lower().rstrip("."), 0)
            # Find the last plain-text assistant turn
            _last_text = next(
                (m["content"] for m in reversed(self.conversation_history) if m["role"] == "assistant" and isinstance(m["content"], str)),
                "",
            )
            # Extract numbered options from that turn
            _opts: list[str] = []
            for _line in _last_text.splitlines():
                _om = _re.match(r"^\s*(\d+)[.)]\s*(?:\*{1,2})?(.+?)(?:\*{1,2})?(?:\s*[—–-].*)?$", _line.strip())
                if _om:
                    _opts.append((_om.group(1), _om.group(2).strip()))
            if _opts and 1 <= _n <= len(_opts):
                _selected_label = _opts[_n - 1][1]
                user_message = f"Option {_n}: {_selected_label}"

        # Detect references to proposed-calendar events:
        #   "Tell me about event -1 — Title"  (old chip format, still handle for safety)
        #   "Tell me about this proposed event — Title"  (new chip format)
        _proposed_match = _re.search(r"(?:\bevent\s+-\d+|this proposed event)\s*(?:[—\-]+\s*(.+))?", user_message, _re.IGNORECASE)
        if _proposed_match:
            title = (_proposed_match.group(1) or "").strip() or "this proposed event"
            enriched_query = (
                f"The user wants to know more about the proposed event '{title}' from the content calendar you just created. "
                f"Using the calendar data and past event performance you already have, provide:\n"
                f"1. Why you proposed this event — which past events or data points justify it\n"
                f"2. A full webinar outline: objectives, 4-6 key talking points, suggested format and duration, and target audience\n"
                f"3. One concrete action to get it on the schedule"
            )
            self.conversation_history.append({"role": "user", "content": user_message})
            try:
                result = await self.content_agent.run(
                    enriched_query,
                    conversation_history=self._text_history()[:-1],  # exclude the just-appended user turn
                    restriction_context=self.restriction_context,
                )
            except Exception:
                self.conversation_history.pop()
                raise
            self.conversation_history.append({"role": "assistant", "content": result["text"]})
            return {
                "text": result["text"],
                "agent_used": "content_agent",
                "chart_data": result.get("chart_data"),
                "content_html": result.get("content_html"),
                "requires_confirmation": False,
                "confirmation_summary": None,
            }

        # Build user message — include image as vision block if attached
        if self.image_block:
            user_content = [{"type": "text", "text": user_message}, self.image_block]
            self.image_block = None  # Consume — only send once
        else:
            user_content = user_message
        self.conversation_history.append({"role": "user", "content": user_content})

        system_blocks = [{"type": "text", "text": _build_orchestrator_prompt(), "cache_control": {"type": "ephemeral"}}]
        if self.restriction_context:
            system_blocks.append({"type": "text", "text": self.restriction_context})

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_blocks,
                tools=self.ROUTING_TOOLS,
                messages=self.conversation_history,
            )
        except Exception:
            # Roll back the user message to keep history consistent
            self.conversation_history.pop()
            raise

        if response.stop_reason == "tool_use":
            assistant_content = response.content
            self.conversation_history.append({"role": "assistant", "content": assistant_content})

            for block in assistant_content:
                if block.type == "tool_use":
                    tool_name = block.name
                    query = block.input.get("query", user_message)

                    if tool_name == "search_knowledge_base":
                        logger.info(f"Searching knowledge base: {query}")
                        try:
                            from app.db.knowledge_base import query_knowledge

                            articles = await query_knowledge(query, n_results=5)
                        except Exception:
                            self.conversation_history.pop()
                            self.conversation_history.pop()
                            raise

                        # Feed results back to orchestrator for a grounded response
                        self.conversation_history.append(
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": block.id,
                                        "content": json.dumps(
                                            {
                                                "articles": articles,
                                                "note": "ONLY use information from these articles. If none are relevant, say you don't have information about that and suggest contacting ON24 support or checking the ON24 Help Center.",
                                            },
                                            default=str,
                                        ),
                                    }
                                ],
                            }
                        )

                        # Let the orchestrator generate a grounded text response (no tools — prevents recursion)
                        # Use Haiku for synthesis: KB articles are already retrieved; simple text composition
                        # doesn't need Sonnet reasoning — saves ~3s per concierge response.
                        try:
                            followup = await self.client.messages.create(
                                model="claude-haiku-4-5-20251001",
                                max_tokens=2048,
                                system=system_blocks,
                                messages=self.conversation_history,
                            )
                        except Exception:
                            self.conversation_history.pop()  # tool_result
                            self.conversation_history.pop()  # assistant tool_use
                            self.conversation_history.pop()  # user message
                            raise

                        text = "\n".join(b.text for b in followup.content if hasattr(b, "text"))
                        self.conversation_history.append({"role": "assistant", "content": text})

                        return {
                            "text": text,
                            "agent_used": "concierge",
                            "chart_data": None,
                            "event_card": None,
                            "poll_cards": None,
                            "requires_confirmation": False,
                            "confirmation_summary": None,
                        }

                    elif tool_name == "route_to_data_agent":
                        logger.info(f"Routing to Data Agent: {query}")
                        try:
                            result = await self.data_agent.run(query, conversation_history=self._text_history(), restriction_context=self.restriction_context)
                        except Exception:
                            # Roll back the dangling tool_use assistant message + user message
                            self.conversation_history.pop()  # assistant tool_use
                            self.conversation_history.pop()  # user message
                            raise

                        # Feed result back into conversation history for context
                        self.conversation_history.append(
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": block.id,
                                        "content": json.dumps(
                                            {
                                                "agent": "data_agent",
                                                "response": result["text"],
                                                "has_chart": result["chart_data"] is not None,
                                            },
                                            default=str,
                                        ),
                                    }
                                ],
                            }
                        )

                        text = result["text"]
                        self.conversation_history.append(
                            {
                                "role": "assistant",
                                "content": text,
                            }
                        )

                        return {
                            "text": text,
                            "agent_used": "data_agent",
                            "chart_data": result.get("chart_data"),
                            "event_card": result.get("event_card"),
                            "event_cards": result.get("event_cards"),
                            "poll_cards": result.get("poll_cards"),
                            "content_articles": result.get("content_articles"),
                            "requires_confirmation": False,
                            "confirmation_summary": None,
                        }

                    elif tool_name == "route_to_content_agent":
                        logger.info(f"Routing to Content Agent: {query}")
                        try:
                            result = await self.content_agent.run(
                                query,
                                conversation_history=self._text_history(),
                                restriction_context=self.restriction_context,
                            )
                        except Exception:
                            self.conversation_history.pop()
                            self.conversation_history.pop()
                            raise

                        self.conversation_history.append(
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": block.id,
                                        "content": json.dumps(
                                            {
                                                "agent": "content_agent",
                                                "response": result["text"],
                                            },
                                            default=str,
                                        ),
                                    }
                                ],
                            }
                        )

                        text = result["text"]
                        self.conversation_history.append({"role": "assistant", "content": text})

                        return {
                            "text": text,
                            "agent_used": "content_agent",
                            "chart_data": None,
                            "content_html": result.get("content_html"),
                            "requires_confirmation": False,
                            "confirmation_summary": None,
                        }

                    elif tool_name == "propose_content_calendar":
                        months = block.input.get("months", 3)
                        logger.info("Two-step content calendar: gathering data then routing to Content Agent")

                        # Step 1: Try cache first — skip data agent call if analytics already warmed
                        data_text: str = ""
                        cache_hit = False
                        try:
                            from app.db.on24_db import get_client_id as _get_cid
                            from app.services.data_prefetch import get_prefetched_calendar_data

                            cached = await get_prefetched_calendar_data(_get_cid())
                            if cached:
                                trends = cached.get("attendance_trends", [])
                                top_events = cached.get("top_events", [])
                                trend_lines = (
                                    "\n".join(
                                        f"- {t.get('month', '')}: {t.get('total_registrants', 0)} registrants, {t.get('total_attendees', 0)} attendees"
                                        for t in trends
                                    )
                                    or "No trend data available."
                                )
                                event_lines = (
                                    "\n".join(
                                        f"- {e.get('description', 'Unknown')} (ID {e.get('event_id')}): "
                                        f"{e.get('avg_engagement', 0):.1f} avg engagement, {e.get('total_attendees', 0)} attendees"
                                        for e in top_events
                                    )
                                    or "No top events available."
                                )
                                data_text = f"## Attendance Trends (Last 3 Months)\n{trend_lines}\n\n## Top Events by Engagement\n{event_lines}"
                                cache_hit = True
                                logger.info("Calendar analytics: cache HIT — skipping data agent call")
                        except Exception as e:
                            logger.warning(f"Calendar cache lookup failed: {e}")

                        if not cache_hit:
                            # Fallback: gather analytics from data agent
                            data_query = f"Get attendance trends for the last {months} months and the top 20 events by engagement score."
                            try:
                                data_result = await self.data_agent.run(
                                    data_query,
                                    conversation_history=self._text_history(),
                                    restriction_context=self.restriction_context,
                                )
                                data_text = data_result["text"]
                                # Warm cache in background for next time
                                try:
                                    import asyncio as _asyncio

                                    from app.db.on24_db import get_client_id as _get_cid2
                                    from app.services.data_prefetch import prefetch_calendar_data

                                    _asyncio.create_task(prefetch_calendar_data(_get_cid2()))
                                except Exception:
                                    pass
                            except Exception as e:
                                logger.error(f"Calendar data agent failed: {e}", exc_info=True)
                                self.conversation_history.pop()  # assistant tool_use
                                self.conversation_history.pop()  # user message
                                _log_error_to_inbox("propose_content_calendar/data_agent", query, str(e))
                                _err = "network timeout" if _is_timeout(e) else "an error"
                                return {
                                    "text": (f"I couldn't retrieve your analytics data ({_err}). Please try again — the next attempt may be faster."),
                                    "agent_used": "content_agent",
                                    "chart_data": None,
                                    "content_html": None,
                                    "requires_confirmation": False,
                                    "confirmation_summary": None,
                                    "proposed_events": None,
                                }

                        # Step 2: Pass data + original query to content agent
                        enriched_query = f"{query}\n\nHere is the analytics data you need to build this calendar:\n\n{data_text}"
                        try:
                            result = await self.content_agent.run(
                                enriched_query,
                                conversation_history=self._text_history(),
                                restriction_context=self.restriction_context,
                            )
                        except Exception as e:
                            logger.error(f"Calendar content agent failed: {e}", exc_info=True)
                            self.conversation_history.pop()  # assistant tool_use
                            self.conversation_history.pop()  # user message
                            _log_error_to_inbox("propose_content_calendar/content_agent", query, str(e))
                            _err = "network timeout" if _is_timeout(e) else "an error"
                            return {
                                "text": (f"I gathered your analytics but couldn't generate the calendar ({_err}). Your data is now cached — please try again."),
                                "agent_used": "content_agent",
                                "chart_data": None,
                                "content_html": None,
                                "requires_confirmation": False,
                                "confirmation_summary": None,
                                "proposed_events": None,
                            }

                        self.conversation_history.append(
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": block.id,
                                        "content": json.dumps(
                                            {
                                                "agent": "content_agent",
                                                "response": result["text"],
                                            },
                                            default=str,
                                        ),
                                    }
                                ],
                            }
                        )

                        text = result["text"]

                        # Extract proposed_events JSON block from content agent response
                        proposed_events = _extract_proposed_events(text)
                        if proposed_events:
                            logger.info(f"Extracted {len(proposed_events)} proposed events from content agent")
                            # Strip the raw JSON block from user-visible text
                            text = re.sub(r"```(?:proposed_events|json)?\s*\n\[.*?\]\s*```", "", text, flags=re.DOTALL).strip()
                        else:
                            logger.warning("Content agent did not emit proposed_events JSON block")

                        self.conversation_history.append({"role": "assistant", "content": text})

                        return {
                            "text": text,
                            "agent_used": "content_agent",
                            "chart_data": None,
                            "content_html": result.get("content_html"),
                            "requires_confirmation": False,
                            "confirmation_summary": None,
                            "proposed_events": proposed_events,
                        }

                    elif tool_name == "route_to_admin_agent":
                        logger.info(f"Routing to Admin Agent: {query} (confirmed={confirmed})")
                        try:
                            result = await self.admin_agent.run(
                                message=query,
                                session_id="orchestrator",
                                confirmed=confirmed,
                                conversation_history=self._text_history(),
                                restriction_context=self.restriction_context,
                            )
                        except Exception:
                            self.conversation_history.pop()
                            self.conversation_history.pop()
                            raise

                        self.conversation_history.append(
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": block.id,
                                        "content": json.dumps(
                                            {
                                                "agent": "admin_agent",
                                                "response": result["text"],
                                                "requires_confirmation": result.get("requires_confirmation", False),
                                            },
                                            default=str,
                                        ),
                                    }
                                ],
                            }
                        )

                        text = result["text"]
                        self.conversation_history.append({"role": "assistant", "content": text})

                        return {
                            "text": text,
                            "agent_used": "admin_agent",
                            "chart_data": None,
                            "requires_confirmation": result.get("requires_confirmation", False),
                            "confirmation_summary": result.get("confirmation_summary"),
                        }

        # Direct response (no routing needed)
        text = "\n".join(b.text for b in response.content if hasattr(b, "text"))
        self.conversation_history.append({"role": "assistant", "content": text})

        return {
            "text": text,
            "agent_used": None,
            "chart_data": None,
            "requires_confirmation": False,
            "confirmation_summary": None,
        }

    def reset(self):
        """Clear conversation history."""
        self.conversation_history = []
