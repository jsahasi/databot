"""Data Agent: queries database and produces analytics for user questions."""

import asyncio
import json
import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

import anthropic

from app.agents.tools import DATA_AGENT_TOOLS, TOOL_HANDLERS
from app.config import settings

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = (Path(__file__).parent / "prompts" / "data_agent.md").read_text()


def _extract_chart(text: str) -> tuple[str, dict | None]:
    """Pull ```chart JSON blocks out of the agent text response.

    Returns (cleaned_text, chart_dict_or_None).
    The chart block is removed from the text so it's not shown as raw JSON.
    """
    pattern = re.compile(r'```chart\s*\n(.*?)\n```', re.DOTALL)
    match = pattern.search(text)
    if not match:
        return text, None
    try:
        chart = json.loads(match.group(1))
        cleaned = (text[:match.start()].rstrip() + "\n" + text[match.end():].lstrip()).strip()
        return cleaned, chart
    except Exception:
        return text, None


def _build_system_prompt() -> str:
    today = date.today().strftime("%B %d, %Y")
    return f"Today's date is {today}.\n\n{_PROMPT_TEMPLATE}"


class DataAgent:
    """Agent that queries the database to answer analytics questions."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-opus-4-6"
        self.max_tool_rounds = 10

    async def _write_audit_log(
        self,
        session_id: str,
        tool_name: str,
        tool_input: dict,
        tool_result: Any,
        error: str | None = None,
    ) -> None:
        """Fire-and-forget audit log write — must not raise."""
        try:
            from app.db.session import async_session_factory
            from app.models.agent_audit_log import AgentAuditLog

            result_snippet = str(tool_result)[:2000] if tool_result is not None else None
            log_entry = AgentAuditLog(
                session_id=session_id,
                agent_name="data_agent",
                tool_name=tool_name,
                tool_input=tool_input,
                tool_result={"result": result_snippet} if result_snippet is not None else None,
                confirmed=False,
                error=error,
            )
            async with async_session_factory() as db:
                db.add(log_entry)
                await db.commit()
        except Exception:
            logger.exception("Failed to write agent audit log")

    async def run(self, user_message: str, conversation_history: list[dict] | None = None, session_id: str = "") -> dict[str, Any]:
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
        event_card = None
        poll_cards = None
        tool_calls_made = []

        system_prompt = _build_system_prompt()

        for _round in range(self.max_tool_rounds):
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
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

                                # Capture poll cards for visual display
                                if tool_name == "get_polls" and isinstance(result, list) and len(result) > 0:
                                    poll_cards = result

                                # Capture event card for single-event queries
                                if tool_name == "get_event_detail" and isinstance(result, dict) and result.get("event_id"):
                                    event_card = {
                                        "event_id": result["event_id"],
                                        "title": result.get("description") or result.get("title") or "",
                                        "start_time": result.get("goodafter") or result.get("start_time"),
                                        "end_time": result.get("goodtill") or result.get("end_time"),
                                        "event_type": result.get("event_type") or "",
                                        "registrant_count": None,
                                        "attendee_count": None,
                                        "conversion_rate": None,
                                        "engagement_score_avg": None,
                                    }

                                if tool_name == "compute_event_kpis" and isinstance(result, dict) and result.get("event_id"):
                                    eid = result["event_id"]
                                    try:
                                        from app.agents.tools.on24_query_tools import get_event_detail
                                        detail = await get_event_detail(eid)
                                        if detail:
                                            event_card = {
                                                "event_id": eid,
                                                "title": detail.get("description") or detail.get("title") or "",
                                                "start_time": detail.get("goodafter") or detail.get("start_time"),
                                                "end_time": detail.get("goodtill") or detail.get("end_time"),
                                                "event_type": detail.get("event_type") or "",
                                                "registrant_count": result.get("total_registrants"),
                                                "attendee_count": result.get("total_attendees"),
                                                "conversion_rate": result.get("conversion_rate"),
                                                "engagement_score_avg": result.get("avg_engagement"),
                                            }
                                    except Exception:
                                        pass  # event card is best-effort

                                asyncio.create_task(
                                    self._write_audit_log(session_id, tool_name, tool_input, result)
                                )

                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": json.dumps(result, default=str),
                                })
                            except Exception as e:
                                logger.error(f"Tool {tool_name} failed: {e}")
                                asyncio.create_task(
                                    self._write_audit_log(session_id, tool_name, tool_input, None, error=str(e))
                                )
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
                raw_text = "\n".join(text_parts)
                cleaned_text, extracted_chart = _extract_chart(raw_text)
                return {
                    "text": cleaned_text,
                    "chart_data": extracted_chart or chart_data,
                    "event_card": event_card,
                    "poll_cards": poll_cards,
                    "tool_calls": tool_calls_made,
                }

        # Hit max rounds — force a final text response with tool_choice=none
        messages.append({
            "role": "user",
            "content": "Summarize the data you have gathered and give a final answer. Do not call any more tools.",
        })
        final = await self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system_prompt,
            tools=DATA_AGENT_TOOLS,
            tool_choice={"type": "none"},
            messages=messages,
        )
        text_parts = [block.text for block in final.content if hasattr(block, "text")]
        raw_text = "\n".join(text_parts)
        cleaned_text, extracted_chart = _extract_chart(raw_text)
        return {
            "text": cleaned_text,
            "chart_data": extracted_chart or chart_data,
            "tool_calls": tool_calls_made,
        }
