"""Admin Agent: manages ON24 write operations with confirmation gate for destructive tools."""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

import anthropic

from app.agents.tools import ADMIN_AGENT_TOOLS, ADMIN_TOOL_HANDLERS
from app.config import settings

logger = logging.getLogger(__name__)

_ADMIN_PROMPT_TEMPLATE = (Path(__file__).parent / "prompts" / "admin_agent.md").read_text()


def _build_admin_prompt() -> str:
    today = date.today().strftime("%B %d, %Y")
    return f"Today's date is {today}.\n\n{_ADMIN_PROMPT_TEMPLATE}"


class AdminAgent:
    """Agent for ON24 write operations.

    ALL destructive tools require explicit confirmation before executing. The agent:
    1. Calls get_event_summary first to show the user what will be affected.
    2. Presents a confirmation summary to the user.
    3. Only proceeds with the destructive tool if the caller passes confirmed=True.
    """

    # Tools that mutate state on ON24 — require user confirmation
    DESTRUCTIVE_TOOLS = {"create_event", "create_event_from_copy", "update_event", "add_registrant", "remove_registrant"}

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-6"
        self.max_tool_rounds = 5

    async def run(
        self,
        message: str,
        session_id: str,
        confirmed: bool = False,
        conversation_history: list[dict] | None = None,
        restriction_context: str = "",
    ) -> dict[str, Any]:
        """Process an admin request, gating destructive tools behind confirmation.

        Returns:
            {
                "text": str,
                "requires_confirmation": bool,
                "confirmation_summary": str | None,
                "tool_calls": list,
            }
        """
        # Build messages from conversation history so the agent can track
        # multi-turn flows (decision tree, confirmation re-sends, edits).
        messages: list[dict] = []
        if conversation_history:
            for h in conversation_history:
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": message})

        tool_calls_made: list[dict] = []

        system_cached = [{"type": "text", "text": _build_admin_prompt(), "cache_control": {"type": "ephemeral"}}]
        if restriction_context:
            system_cached.append({"type": "text", "text": restriction_context})

        for _round in range(self.max_tool_rounds):
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_cached,
                tools=ADMIN_AGENT_TOOLS,
                messages=messages,
            )

            if response.stop_reason != "tool_use":
                # Final text response from the model
                text_parts = [block.text for block in response.content if hasattr(block, "text")]
                return {
                    "text": "\n".join(text_parts),
                    "requires_confirmation": False,
                    "confirmation_summary": None,
                    "tool_calls": tool_calls_made,
                }

            # --- Tool use round ---
            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})

            tool_results = []
            held_for_confirmation: list[dict] = []

            for block in assistant_content:
                if block.type != "tool_use":
                    continue

                tool_name = block.name
                tool_input = block.input
                logger.info(f"Admin Agent tool requested: {tool_name}({tool_input})")

                # Gate: destructive tools need confirmation
                if tool_name in self.DESTRUCTIVE_TOOLS and not confirmed:
                    # Collect all destructive blocks; we will NOT execute any
                    held_for_confirmation.append(
                        {
                            "tool": tool_name,
                            "input": tool_input,
                            "tool_use_id": block.id,
                        }
                    )
                    continue

                # Execute the tool (safe or confirmed)
                handler = ADMIN_TOOL_HANDLERS.get(tool_name)
                if handler:
                    try:
                        result = await handler(**tool_input)
                        tool_calls_made.append({"tool": tool_name, "input": tool_input})
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(result, default=str),
                            }
                        )
                    except Exception as e:
                        logger.error(f"Tool {tool_name} failed: {e}")
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps({"error": str(e)}),
                                "is_error": True,
                            }
                        )
                else:
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"error": f"Unknown tool: {tool_name}"}),
                            "is_error": True,
                        }
                    )

            # If we held back any destructive tools, return a confirmation request
            if held_for_confirmation:
                pending = held_for_confirmation[0]
                summary = _build_confirmation_summary(pending["tool"], pending["input"])
                return {
                    "text": summary,
                    "requires_confirmation": True,
                    "confirmation_summary": summary,
                    "tool_calls": tool_calls_made,
                }

            messages.append({"role": "user", "content": tool_results})

        # Hit max tool rounds — return partial result
        return {
            "text": "I've processed the request but reached the operation limit. Please review and try again.",
            "requires_confirmation": False,
            "confirmation_summary": None,
            "tool_calls": tool_calls_made,
        }


_EVENT_TYPE_LABELS = {
    "fav": "Live Video",
    "simulive": "Simulive",
    "ondemand": "On Demand",
    "encodeonsite": "Broadcast",
    "sim2live": "Sim-2-Live",
    "meetups": "Forums",
}


def _event_id_to_path(eid: int) -> str:
    s = str(eid)
    return "/".join(s[i : i + 2] for i in range(0, len(s), 2))


def _build_confirmation_summary(tool_name: str, tool_input: dict) -> str:
    """Build a human-readable summary of a pending destructive operation."""
    if tool_name in ("create_event", "create_event_from_copy"):
        etype = tool_input.get("event_type", "")
        etype_label = _EVENT_TYPE_LABELS.get(etype, etype)
        title = tool_input.get("title", "")
        start = tool_input.get("start_time", "")
        end = tool_input.get("end_time", "")
        source_id = tool_input.get("source_event_id")
        lines = [
            f"Create Event: {title}",
        ]
        if etype_label:
            lines.append(f"Type: {etype_label}")
        lines.append(f"Start: {start}")
        if end:
            lines.append(f"End: {end}")
        if tool_input.get("description"):
            lines.append(f"Description: {tool_input['description']}")
        if source_id:
            lines.append(f"Template: {source_id}")
            # Add thumbnail previews
            try:
                from app.agents.agentic_templates import VONAGE_TEMPLATES, ELITE_TEMPLATES
                all_templates = {**VONAGE_TEMPLATES, **ELITE_TEMPLATES}
                tmpl = next((v for v in all_templates.values() if v["event_id"] == source_id), None)
                if tmpl:
                    path = _event_id_to_path(source_id)
                    thumb = tmpl["thumb"]
                    base = thumb.split("Locked")[0].split("Editable")[0].split("Other")[0]
                    lines.append("")
                    lines.append(f"![Console](https://wcc.on24.com/event/{path}/rt/1/{thumb}.png)")
                    lines.append(f"![Registration](https://wcc.on24.com/event/{path}/rt/1/{base}Reg.png)")
            except Exception:
                pass
        return "\n".join(lines)
    elif tool_name == "update_event":
        changes = {k: v for k, v in tool_input.items() if k != "on24_event_id" and v is not None}
        lines = [f"**Update Event** (ID: {tool_input.get('on24_event_id')})"]
        for field, value in changes.items():
            lines.append(f"- {field.replace('_', ' ').title()}: {value}")
        return "\n".join(lines)
    elif tool_name == "add_registrant":
        return (
            f"**Add Registrant** to event {tool_input.get('on24_event_id')}\n"
            f"- Name: {tool_input.get('first_name')} {tool_input.get('last_name')}\n"
            f"- Email: {tool_input.get('email')}\n"
            + (f"- Company: {tool_input.get('company')}\n" if tool_input.get("company") else "")
            + (f"- Job Title: {tool_input.get('job_title')}\n" if tool_input.get("job_title") else "")
        )
    elif tool_name == "remove_registrant":
        return f"**Remove Registrant** from event {tool_input.get('on24_event_id')}\n- Email: {tool_input.get('email')}\n\nThis action cannot be undone."
    else:
        return f"**{tool_name}**\nParameters: {json.dumps(tool_input, indent=2)}"
