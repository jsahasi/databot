"""Chat endpoint: WebSocket-based agent conversation."""

import asyncio
import json
import logging
import re
from typing import Any

import anthropic
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

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
) -> list[str]:
    """Generate 5 short follow-up question suggestions using Haiku."""
    client = anthropic.AsyncAnthropic()
    prompt = f"User asked: {user_message}\nAssistant answered: {response_text}"

    view_rule = ""
    if has_chart:
        view_rule = (
            "The response included a chart. Include 1 suggestion offering an alternative view "
            "such as 'Show as table' or 'Show as pie chart'. "
        )
    elif has_table:
        view_rule = (
            "The response included a data table. Include 1-2 suggestions offering alternative "
            "chart views such as 'Show as bar chart', 'Show as line chart', or 'Show as pie chart'. "
        )

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=(
            "You anticipate the next 5 questions a user would naturally ask next in a "
            "webinar analytics chatbot conversation. Think ahead: if they just saw one event, "
            "they'll want KPIs, attendees, polls, trends, comparisons, etc. "
            f"{view_rule}"
            "Each suggestion must be 3-7 words, conversational, specific to the context. "
            "Examples: 'How did it perform?', 'Show attendee breakdown', 'Compare to last month', "
            "'Which companies attended?', 'Show poll results', 'Show as bar chart', 'Show as table'. "
            "Return only a JSON array of exactly 5 strings, nothing else."
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in response.content if hasattr(b, "text"))
    # Extract JSON array even if Haiku wraps it in prose
    match = re.search(r'\[.*\]', text, re.DOTALL)
    raw = match.group() if match else text
    suggestions: list[str] = json.loads(raw)
    return suggestions[:5]


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
                    _has_chart = bool(result.get("chart_data"))
                    _response_text = result.get("text", "")
                    _has_table = "|" in _response_text and "---" in _response_text

                    async def _send_suggestions(
                        ws: WebSocket, user_msg: str, text: str, agent: str | None,
                        has_chart: bool, has_table: bool,
                    ) -> None:
                        try:
                            suggestions = await asyncio.wait_for(
                                generate_suggestions(user_msg, text, agent, has_chart, has_table),
                                timeout=8.0,
                            )
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
                    ))

                except Exception as e:
                    logger.error(f"Agent error: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Agent error: {str(e)}",
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


class ChatResponse(BaseModel):
    text: str
    agent_used: str | None = None
    chart_data: dict | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat_http(request: ChatRequest):
    """HTTP fallback for agent conversations (non-streaming)."""
    agent = _get_or_create_agent(request.session_id)
    result = await agent.process_message(request.message)
    return ChatResponse(
        text=result.get("text", ""),
        agent_used=result.get("agent_used"),
        chart_data=result.get("chart_data"),
    )
