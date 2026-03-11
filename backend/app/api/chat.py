"""Chat endpoint: WebSocket-based agent conversation."""

import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.agents.orchestrator import OrchestratorAgent

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active sessions (in production, use Redis or similar)
_sessions: dict[str, OrchestratorAgent] = {}


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

                if not content:
                    await websocket.send_json({"type": "error", "message": "Empty message"})
                    continue

                agent = _get_or_create_agent(session_id)

                # Notify client we're starting
                await websocket.send_json({"type": "agent_start", "agent": "orchestrator"})

                try:
                    result = await agent.process_message(content)

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

                    # Signal completion
                    await websocket.send_json({
                        "type": "message_complete",
                        "agent_used": result.get("agent_used"),
                    })

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
