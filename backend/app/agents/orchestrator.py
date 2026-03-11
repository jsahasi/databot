"""Orchestrator Agent: classifies user intent and routes to specialist agents."""

import json
import logging
from pathlib import Path
from typing import Any, AsyncIterator

import anthropic

from app.agents.data_agent import DataAgent
from app.agents.content_agent import ContentAgent
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "orchestrator.md").read_text()


class OrchestratorAgent:
    """Routes user messages to the appropriate specialist agent."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-20250514"
        self.data_agent = DataAgent()
        self.content_agent = ContentAgent()
        self.conversation_history: list[dict] = []

    # Tool for routing to sub-agents
    ROUTING_TOOLS = [
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
            "description": "Route to Content Agent for content strategy and topic recommendations.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The refined query for content analysis"},
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

    async def process_message(self, user_message: str) -> dict[str, Any]:
        """Process a user message through the orchestrator.

        Returns:
            {
                "text": str,
                "agent_used": str | None,
                "chart_data": dict | None,
            }
        """
        self.conversation_history.append({"role": "user", "content": user_message})

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=self.ROUTING_TOOLS,
            messages=self.conversation_history,
        )

        if response.stop_reason == "tool_use":
            assistant_content = response.content
            self.conversation_history.append({"role": "assistant", "content": assistant_content})

            for block in assistant_content:
                if block.type == "tool_use":
                    tool_name = block.name
                    query = block.input.get("query", user_message)

                    if tool_name == "route_to_data_agent":
                        logger.info(f"Routing to Data Agent: {query}")
                        result = await self.data_agent.run(query)

                        # Feed result back to orchestrator for synthesis
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

                        # Get orchestrator's synthesis
                        synthesis = await self.client.messages.create(
                            model=self.model,
                            max_tokens=2048,
                            system=SYSTEM_PROMPT,
                            messages=self.conversation_history,
                        )

                        text = "\n".join(
                            b.text for b in synthesis.content if hasattr(b, "text")
                        )
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": text,
                        })

                        return {
                            "text": text,
                            "agent_used": "data_agent",
                            "chart_data": result.get("chart_data"),
                        }

                    elif tool_name == "route_to_content_agent":
                        logger.info(f"Routing to Content Agent: {query}")
                        result = await self.content_agent.run(query)

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

                        synthesis = await self.client.messages.create(
                            model=self.model,
                            max_tokens=2048,
                            system=SYSTEM_PROMPT,
                            messages=self.conversation_history,
                        )
                        text = "\n".join(b.text for b in synthesis.content if hasattr(b, "text"))
                        self.conversation_history.append({"role": "assistant", "content": text})

                        return {
                            "text": text,
                            "agent_used": "content_agent",
                            "chart_data": None,
                        }

                    elif tool_name == "route_to_admin_agent":
                        # Admin agent not yet implemented
                        self.conversation_history.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps({
                                    "agent": "admin_agent",
                                    "response": "Admin Agent is not yet available. Event management features are coming soon.",
                                }),
                            }],
                        })

                        synthesis = await self.client.messages.create(
                            model=self.model,
                            max_tokens=1024,
                            system=SYSTEM_PROMPT,
                            messages=self.conversation_history,
                        )
                        text = "\n".join(b.text for b in synthesis.content if hasattr(b, "text"))
                        self.conversation_history.append({"role": "assistant", "content": text})

                        return {
                            "text": text,
                            "agent_used": "admin_agent",
                            "chart_data": None,
                        }

        # Direct response (no routing needed)
        text = "\n".join(b.text for b in response.content if hasattr(b, "text"))
        self.conversation_history.append({"role": "assistant", "content": text})

        return {
            "text": text,
            "agent_used": None,
            "chart_data": None,
        }

    def reset(self):
        """Clear conversation history."""
        self.conversation_history = []
