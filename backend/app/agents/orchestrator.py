"""Orchestrator Agent: classifies user intent and routes to specialist agents."""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any, AsyncIterator

import anthropic

from app.agents.admin_agent import AdminAgent
from app.agents.data_agent import DataAgent
from app.agents.content_agent import ContentAgent
from app.config import settings

logger = logging.getLogger(__name__)

_ORCHESTRATOR_TEMPLATE = (Path(__file__).parent / "prompts" / "orchestrator.md").read_text()

import re

def _extract_proposed_events(text: str) -> list[dict] | None:
    """Extract proposed_events JSON from a ```proposed_events fenced block."""
    m = re.search(r"```proposed_events\s*\n(.*?)```", text, re.DOTALL)
    if not m:
        return None
    try:
        events = json.loads(m.group(1).strip())
        if isinstance(events, list) and events:
            return events
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse proposed_events JSON from content agent")
    return None


def _build_orchestrator_prompt() -> str:
    today = date.today().strftime("%B %d, %Y")
    return f"Today's date is {today}.\n\n{_ORCHESTRATOR_TEMPLATE}"


class OrchestratorAgent:
    """Routes user messages to the appropriate specialist agent."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-opus-4-6"
        self.data_agent = DataAgent()
        self.content_agent = ContentAgent()
        self.admin_agent = AdminAgent()
        self.conversation_history: list[dict] = []

    # Tool for routing to sub-agents
    ROUTING_TOOLS = [
        {
            "name": "search_knowledge_base",
            "description": "Search the ON24 knowledge base (Zendesk help articles) for platform how-to questions, feature explanations, and configuration guides. Use this for ANY question about how to do something on the ON24 platform (e.g. 'how do I add speakers', 'how to set up polls', 'how to configure registration').",
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
            "description": "Route the user's question to the Data Agent for database queries, analytics, KPIs, and chart generation.",
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
            "description": "Route to Content Agent for content strategy, topic recommendations, and writing/drafting articles.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The refined query for content analysis"},
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
        """
        clean = []
        for msg in self.conversation_history:
            content = msg.get("content")
            if isinstance(content, str):
                clean.append(msg)
            elif isinstance(content, list):
                # Keep only text blocks; skip tool_use and tool_result
                text_blocks = [b for b in content if isinstance(b, dict) and b.get("type") == "text"]
                if text_blocks:
                    clean.append({"role": msg["role"], "content": text_blocks})
                # If content is a list of ContentBlock objects (Anthropic SDK), extract text
                elif all(hasattr(b, "type") for b in content):
                    texts = [{"type": "text", "text": b.text} for b in content if hasattr(b, "text")]
                    if texts:
                        clean.append({"role": msg["role"], "content": texts})
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
        self.conversation_history.append({"role": "user", "content": user_message})

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=_build_orchestrator_prompt(),
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
                        self.conversation_history.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps({
                                    "articles": articles,
                                    "note": "ONLY use information from these articles. If none are relevant, say you don't have information about that and suggest contacting ON24 support or checking the ON24 Help Center.",
                                }, default=str),
                            }],
                        })

                        # Let the orchestrator generate a grounded response
                        try:
                            followup = await self.client.messages.create(
                                model=self.model,
                                max_tokens=2048,
                                system=_build_orchestrator_prompt(),
                                tools=self.ROUTING_TOOLS,
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
                            result = await self.data_agent.run(query, conversation_history=self._text_history())
                        except Exception:
                            # Roll back the dangling tool_use assistant message + user message
                            self.conversation_history.pop()  # assistant tool_use
                            self.conversation_history.pop()  # user message
                            raise

                        # Feed result back into conversation history for context
                        self.conversation_history.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps({
                                    "agent": "data_agent",
                                    "response": result["text"],
                                    "has_chart": result["chart_data"] is not None,
                                }, default=str),
                            }],
                        })

                        text = result["text"]
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": text,
                        })

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
                            )
                        except Exception:
                            self.conversation_history.pop()
                            self.conversation_history.pop()
                            raise

                        self.conversation_history.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps({
                                    "agent": "content_agent",
                                    "response": result["text"],
                                }, default=str),
                            }],
                        })

                        text = result["text"]
                        self.conversation_history.append({"role": "assistant", "content": text})

                        return {
                            "text": text,
                            "agent_used": "content_agent",
                            "chart_data": None,
                            "requires_confirmation": False,
                            "confirmation_summary": None,
                        }

                    elif tool_name == "propose_content_calendar":
                        months = block.input.get("months", 3)
                        logger.info(f"Two-step content calendar: gathering data then routing to Content Agent")

                        # Step 1: Gather analytics from the data agent
                        data_query = (
                            f"Get attendance trends for the last 6 months and the top 20 events by engagement score."
                        )
                        try:
                            data_result = await self.data_agent.run(
                                data_query,
                                conversation_history=self._text_history(),
                            )
                        except Exception:
                            self.conversation_history.pop()  # assistant tool_use
                            self.conversation_history.pop()  # user message
                            raise

                        # Step 2: Pass data + original query to content agent
                        enriched_query = (
                            f"{query}\n\n"
                            f"Here is the analytics data you need to build this calendar:\n\n"
                            f"{data_result['text']}"
                        )
                        try:
                            result = await self.content_agent.run(
                                enriched_query,
                                conversation_history=self._text_history(),
                            )
                        except Exception:
                            self.conversation_history.pop()  # assistant tool_use
                            self.conversation_history.pop()  # user message
                            raise

                        self.conversation_history.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps({
                                    "agent": "content_agent",
                                    "response": result["text"],
                                }, default=str),
                            }],
                        })

                        text = result["text"]
                        self.conversation_history.append({"role": "assistant", "content": text})

                        # Extract proposed_events JSON block from content agent response
                        proposed_events = _extract_proposed_events(text)

                        return {
                            "text": text,
                            "agent_used": "content_agent",
                            "chart_data": None,
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
                            )
                        except Exception:
                            self.conversation_history.pop()
                            self.conversation_history.pop()
                            raise

                        self.conversation_history.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps({
                                    "agent": "admin_agent",
                                    "response": result["text"],
                                    "requires_confirmation": result.get("requires_confirmation", False),
                                }, default=str),
                            }],
                        })

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
