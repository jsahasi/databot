"""Data Agent: queries database and produces analytics for user questions."""

import json
import logging
from pathlib import Path
from typing import Any

import anthropic

from app.agents.tools import DATA_AGENT_TOOLS, TOOL_HANDLERS
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "data_agent.md").read_text()


class DataAgent:
    """Agent that queries the database to answer analytics questions."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-20250514"
        self.max_tool_rounds = 5

    async def run(self, user_message: str, conversation_history: list[dict] | None = None) -> dict[str, Any]:
        """Process a user message and return a response with optional chart data.

        Returns:
            {
                "text": str,           # Agent's text response
                "chart_data": dict | None,  # Chart data if generated
                "tool_calls": list,    # Tools that were called
            }
        """
        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": user_message})

        chart_data = None
        tool_calls_made = []

        for _round in range(self.max_tool_rounds):
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=DATA_AGENT_TOOLS,
                messages=messages,
            )

            # Check if model wants to use tools
            if response.stop_reason == "tool_use":
                # Process all tool calls in the response
                assistant_content = response.content
                messages.append({"role": "assistant", "content": assistant_content})

                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        logger.info(f"Data Agent calling tool: {tool_name}({tool_input})")

                        handler = TOOL_HANDLERS.get(tool_name)
                        if handler:
                            try:
                                result = await handler(**tool_input)
                                tool_calls_made.append({"tool": tool_name, "input": tool_input})

                                # Capture chart data if this was a chart generation call
                                if tool_name == "generate_chart_data":
                                    chart_data = result

                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": json.dumps(result, default=str),
                                })
                            except Exception as e:
                                logger.error(f"Tool {tool_name} failed: {e}")
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": json.dumps({"error": str(e)}),
                                    "is_error": True,
                                })
                        else:
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps({"error": f"Unknown tool: {tool_name}"}),
                                "is_error": True,
                            })

                messages.append({"role": "user", "content": tool_results})
            else:
                # Model returned a final text response
                text_parts = [block.text for block in response.content if hasattr(block, "text")]
                return {
                    "text": "\n".join(text_parts),
                    "chart_data": chart_data,
                    "tool_calls": tool_calls_made,
                }

        # If we hit max rounds, return what we have
        return {
            "text": "I've gathered the data but hit the analysis limit. Here's what I found so far.",
            "chart_data": chart_data,
            "tool_calls": tool_calls_made,
        }
