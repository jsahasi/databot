"""Chat endpoint: WebSocket-based agent conversation."""

import asyncio
import json
import logging
import re
from typing import Any

import anthropic
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, field_validator

from app.agents.orchestrator import OrchestratorAgent

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active sessions (in production, use Redis or similar)
_sessions: dict[str, OrchestratorAgent] = {}


async def generate_suggestions(
    user_message: str,
    response_text: str,
    agent_used: str | None,
    has_chart: bool = False,
    has_table: bool = False,
    chart_type: str | None = None,
) -> list[str]:
    """Generate 5 short follow-up question suggestions using Haiku."""
    client = anthropic.AsyncAnthropic()
    prompt = f"User asked: {user_message}\nAssistant answered: {response_text}"

    view_rule = ""
    if has_chart:
        # Offer views that are NOT the current chart type
        if chart_type == "bar":
            view_rule = (
                "The response already shows a BAR chart. "
                "Include 1 suggestion for an alternative view — 'Show as line chart', 'Show as pie chart', or 'Show as table'. "
                "Do NOT suggest 'Show as bar chart'."
            )
        elif chart_type == "line":
            view_rule = (
                "The response already shows a LINE chart. "
                "Include 1 suggestion for an alternative view — 'Show as bar chart', 'Show as pie chart', or 'Show as table'. "
                "Do NOT suggest 'Show as line chart'."
            )
        elif chart_type == "pie":
            view_rule = (
                "The response already shows a PIE chart. "
                "Include 1 suggestion for an alternative view — 'Show as bar chart' or 'Show as table'. "
                "Do NOT suggest 'Show as pie chart'."
            )
        else:
            view_rule = (
                "The response included a chart. Include 1 suggestion for an alternative view "
                "such as 'Show as table', 'Show as bar chart', or 'Show as pie chart'. "
            )
    elif has_table:
        view_rule = (
            "The response already shows a DATA TABLE. "
            "Include 1-2 suggestions offering chart views: 'Show as bar chart', 'Show as line chart', or 'Show as pie chart'. "
            "Do NOT suggest 'Show as table'."
        )

    # Branch the system prompt for knowledge-base (help) mode vs data mode
    if agent_used == "concierge":
        system_prompt = (
            "The user just asked a how-to question about ON24 and got an answer. "
            "Generate 4 follow-up questions that are DIRECTLY related to the specific topic just answered — "
            "drill deeper into that same topic, cover adjacent sub-features, or address common next steps. "
            "Do NOT generate generic ON24 how-to questions unrelated to the current answer. "
            f"User asked: {user_message}\n"
            f"The answer covered: {bot_response[:400]}\n"
            "Example: if the answer was about registration pages, good follow-ups are about specific sections "
            "(SEO settings, managing registrants, conditional fields, confirmation emails) — "
            "NOT generic topics like 'How do I set up polls'.\n"
            "Each suggestion must be a short how-to phrase (3-8 words), conversational. "
            "Do NOT suggest data/analytics queries — "
            "the last chip is always 'Explore my event data' added automatically. "
            "Return only a JSON array of exactly 4 strings, nothing else."
        )
    else:
        system_prompt = (
            "You anticipate the next 5 questions a user would naturally ask next in a "
            "webinar analytics chatbot conversation. Think ahead: if they just saw one event, "
            "they'll want KPIs, attendees, polls, trends, comparisons, etc. "
            f"{view_rule}"
            "Each suggestion must be 3-7 words, conversational, specific to the context. "
            "\n\nCRITICAL — Only suggest things the system can actually do. "
            "The system has these capabilities ONLY:\n"
            "- List/search events (by name, type, date)\n"
            "- Event KPIs (registrants, attendees, engagement, conversion)\n"
            "- Attendance trends over time\n"
            "- Top events by attendees or engagement\n"
            "- Poll results for a specific event\n"
            "- Q&A questions asked by attendees for a specific event\n"
            "- Top events by poll responses\n"
            "- Audience companies (who attended)\n"
            "- Audience sources (referral/partner tracking)\n"
            "- Resource downloads for an event\n"
            "- Charts (bar, line, pie) of the above data\n"
            "- Content topic analysis and recommendations\n"
            "- Platform how-to questions (searches knowledge base)\n"
            "\nDo NOT suggest anything outside this list. Specifically NEVER suggest:\n"
            "- Speaker/presenter performance or metrics (not tracked per-speaker)\n"
            "- Region, geography, or location data (not available)\n"
            "- Individual attendee details or contact info\n"
            "- Revenue, ROI, or financial metrics\n"
            "- Email campaign metrics\n"
            "- A/B testing or experiments\n"
            "- Anything the response already said the system cannot do\n"
            "\nExamples: 'How did it perform?', 'Show attendee breakdown', 'Compare to last month', "
            "'Which companies attended?', 'Show poll results', 'Show as bar chart', 'Show as pie chart', 'Show as table'. "
            "Return only a JSON array of exactly 5 strings, nothing else."
        )

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in response.content if hasattr(b, "text"))
    # Extract JSON array even if Haiku wraps it in prose
    match = re.search(r'\[.*\]', text, re.DOTALL)
    raw = match.group() if match else text
    suggestions: list[str] = json.loads(raw)
    suggestions = suggestions[:5]

    # In help mode, always replace the last chip with a data exploration escape
    if agent_used == "concierge":
        suggestions = suggestions[:4] + ["Explore my event data"]

    return suggestions


def _get_or_create_agent(session_id: str) -> OrchestratorAgent:
    if session_id not in _sessions:
        _sessions[session_id] = OrchestratorAgent()
    return _sessions[session_id]


async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming agent conversations.

    Protocol:
    Client -> Server: {"type": "message", "content": "...", "session_id": "..."}
    Server -> Client: {"type": "agent_start", "agent": "orchestrator"}
    Server -> Client: {"type": "agent_routing", "target": "data_agent"}
    Server -> Client: {"type": "text", "content": "..."}
    Server -> Client: {"type": "chart_data", "data": {...}}
    Server -> Client: {"type": "message_complete", "agent_used": "..."}
    Server -> Client: {"type": "error", "message": "..."}
    """
    await websocket.accept()
    session_id = "default"

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "message":
                content = data.get("content", "").strip()
                session_id = data.get("session_id", "default")
                confirmed = bool(data.get("confirmed", False))

                if not content:
                    await websocket.send_json({"type": "error", "message": "Empty message"})
                    continue

                # Bound message length to prevent prompt-stuffing and resource exhaustion (A03).
                _MAX_MESSAGE_LEN = 4000
                if len(content) > _MAX_MESSAGE_LEN:
                    await websocket.send_json({"type": "error", "message": "Message too long (max 4000 characters)."})
                    continue

                # Sanitise session_id: accept only alphanumeric/hyphen/underscore to prevent
                # session-ID-based injection or path traversal in future storage backends (A01).
                if not re.match(r'^[\w\-]{1,128}$', session_id):
                    session_id = "default"

                agent = _get_or_create_agent(session_id)

                # Notify client we're starting
                await websocket.send_json({"type": "agent_start", "agent": "orchestrator"})

                try:
                    result = await agent.process_message(content, confirmed=confirmed)

                    # Send agent routing info
                    if result.get("agent_used"):
                        await websocket.send_json({
                            "type": "agent_routing",
                            "target": result["agent_used"],
                        })

                    # Send text response
                    await websocket.send_json({
                        "type": "text",
                        "content": result.get("text", ""),
                    })

                    # Send chart data if available
                    if result.get("chart_data"):
                        await websocket.send_json({
                            "type": "chart_data",
                            "data": result["chart_data"],
                        })

                    # Send event card if available
                    if result.get("event_card"):
                        await websocket.send_json({
                            "type": "event_card",
                            "data": result["event_card"],
                        })

                    # Send event cards grid (2–4 events)
                    if result.get("event_cards"):
                        await websocket.send_json({
                            "type": "event_cards",
                            "data": result["event_cards"],
                        })

                    # Send poll cards only if no chart is already being shown
                    # (chart takes precedence — avoids duplicate rendering when user asks "show as pie chart")
                    if result.get("poll_cards") and not result.get("chart_data"):
                        await websocket.send_json({
                            "type": "poll_cards",
                            "data": result["poll_cards"],
                        })

                    # Send confirmation request if a destructive operation is pending
                    if result.get("requires_confirmation"):
                        await websocket.send_json({
                            "type": "confirmation_required",
                            "confirmation_summary": result.get("confirmation_summary"),
                        })

                    # Signal completion
                    await websocket.send_json({
                        "type": "message_complete",
                        "agent_used": result.get("agent_used"),
                        "requires_confirmation": result.get("requires_confirmation", False),
                    })

                    # Fire suggestions asynchronously — non-blocking, skip on timeout/error
                    _chart_data = result.get("chart_data")
                    _has_chart = bool(_chart_data)
                    _chart_type = _chart_data.get("type") if _chart_data else None
                    _response_text = result.get("text", "")
                    _has_table = "|" in _response_text and "---" in _response_text

                    async def _send_suggestions(
                        ws: WebSocket, user_msg: str, text: str, agent: str | None,
                        has_chart: bool, has_table: bool, chart_type: str | None,
                    ) -> None:
                        try:
                            suggestions = await asyncio.wait_for(
                                generate_suggestions(user_msg, text, agent, has_chart, has_table, chart_type),
                                timeout=8.0,
                            )
                            # Guarantee a "find event with polls" chip when polls were empty
                            if "no poll results for" in text.lower():
                                poll_chip = "Show polls for the most recent event that had polls"
                                suggestions = [poll_chip] + [s for s in suggestions if s != poll_chip][:4]
                            await ws.send_json({"type": "suggestions", "suggestions": suggestions})
                        except Exception:
                            pass  # Suggestions are best-effort; never block the user

                    asyncio.create_task(_send_suggestions(
                        websocket,
                        content,
                        _response_text,
                        result.get("agent_used"),
                        _has_chart,
                        _has_table,
                        _chart_type,
                    ))

                except Exception as e:
                    # Log full detail server-side; send only a generic message to the client
                    # to prevent leaking stack traces, SQL errors, or internal details (A02).
                    logger.error(f"Agent error: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": "An error occurred processing your request. Please try again.",
                    })

            elif data.get("type") == "reset":
                session_id = data.get("session_id", "default")
                if session_id in _sessions:
                    _sessions[session_id].reset()
                await websocket.send_json({"type": "reset_complete"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
        # Clean up session after disconnect
        _sessions.pop(session_id, None)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)


# --- HTTP fallback ---


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

    # Bound message length to prevent prompt-stuffing / resource exhaustion (A03).
    @field_validator("message")
    @classmethod
    def _message_length(cls, v: str) -> str:
        if len(v) > 4000:
            raise ValueError("Message too long (max 4000 characters).")
        return v


class ChatResponse(BaseModel):
    text: str
    agent_used: str | None = None
    chart_data: dict | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat_http(request: ChatRequest):
    """HTTP fallback for agent conversations (non-streaming)."""
    # Sanitise session_id (A01) — same rule as the WebSocket handler.
    session_id = request.session_id if re.match(r'^[\w\-]{1,128}$', request.session_id) else "default"
    try:
        agent = _get_or_create_agent(session_id)
        result = await agent.process_message(request.message)
        return ChatResponse(
            text=result.get("text", ""),
            agent_used=result.get("agent_used"),
            chart_data=result.get("chart_data"),
        )
    except Exception as e:
        # Log internally; do not expose exception details to the client (A02).
        logger.error(f"HTTP chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred processing your request.")
