"""Chat endpoint: WebSocket-based agent conversation."""

import asyncio
import base64
import json
import logging
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import anthropic
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, field_validator

from app.agents.orchestrator import OrchestratorAgent
from app.config import settings
from app.db.on24_db import set_request_client_id, get_client_id, get_pool, get_tenant_client_ids
from app.services.response_cache import get_cached_response, cache_response

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active sessions (in production, use Redis or similar)
_sessions: dict[str, OrchestratorAgent] = {}

# SEC-02: Per-IP WebSocket message rate limiter
_ws_rate: dict[str, list[float]] = defaultdict(list)
_WS_RATE_WINDOW = 60.0  # seconds


def _check_ws_rate(client_ip: str) -> bool:
    """Return True if under limit, False if rate exceeded."""
    now = time.monotonic()
    limit = settings.rate_limit_per_minute
    # Prune old entries
    _ws_rate[client_ip] = [t for t in _ws_rate[client_ip] if now - t < _WS_RATE_WINDOW]
    if len(_ws_rate[client_ip]) >= limit:
        return False
    _ws_rate[client_ip].append(now)
    return True

# Permission → product name mapping for restriction context
_PERM_PRODUCT_MAP = {
    "view-webcasts": "Elite (Webcasts)",
    "manage-engagement-hub": "Engagement Hub",
    "manage-target-experiences": "Target (Landing Pages)",
    "manage-virtual-events": "GoLive (Virtual Events)",
    "manage-brand-settings": "Branding settings",
    "manage-integrations": "Connect / Integrations",
    "manage-users": "User management",
    "view-analytics": "Analytics and event data",
    "manage-meetups": "Forums (interactive webinars)",
}

# Cache client admin contacts (refreshed per session, not per message)
_admin_contacts_cache: dict[str, str] = {}


async def _get_admin_contacts() -> str:
    """Look up up to 2 Client Admin names for the current client hierarchy."""
    cache_key = str(get_client_id())
    if cache_key in _admin_contacts_cache:
        return _admin_contacts_cache[cache_key]

    try:
        pool = await get_pool()
        client_ids = await get_tenant_client_ids()
        sql = """
            SELECT DISTINCT a.firstname, a.lastname
            FROM on24master.admin a
            JOIN on24master.admin_x_client axc ON a.admin_id = axc.admin_id
            JOIN on24master.admin_x_profile axp ON axp.admin_id = a.admin_id
            WHERE axc.client_id = ANY($1::bigint[])
              AND a.is_active = 'Y'
              AND axp.admin_profile_name = 'Client Admin'
              AND axp.is_active = 'Y'
            ORDER BY a.lastname, a.firstname
            LIMIT 2
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, client_ids, timeout=5.0)
        names = [f"{r['firstname']} {r['lastname']}".strip() for r in rows if r['firstname']]
        result = " or ".join(names) if names else ""
        _admin_contacts_cache[cache_key] = result
        return result
    except Exception:
        return ""


async def _build_restriction_context(permissions: list[str]) -> str:
    """Build a system prompt addendum listing restricted products."""
    if not permissions:
        return ""

    restricted = []
    for perm, product in _PERM_PRODUCT_MAP.items():
        if perm not in permissions:
            restricted.append(product)

    if not restricted:
        return ""

    admin_names = await _get_admin_contacts()
    contact = f"reach out to {admin_names} or your ON24 CSM" if admin_names else "reach out to your account administrator or ON24 CSM"

    return (
        "\n\n## Product Access Restrictions (MANDATORY)\n"
        f"This user does NOT have access to: {', '.join(restricted)}.\n"
        "- Do NOT mention, link to, or suggest these products in your response.\n"
        "- Do NOT show deep links to restricted products.\n"
        "- If the user asks about a restricted product, respond: "
        f"\"That feature requires additional access. To enable it, {contact}.\"\n"
        "- You may mention restricted products ONLY in the context of an upsell opportunity, "
        f"framed as: \"To unlock [product], {contact}.\"\n"
    )


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

    # Fixed agent-switch chips appended after LLM context chips.
    # Keys = agent that just answered; values = switch chips for the other agents.
    _AGENT_SWITCHES: dict[str | None, list[str]] = {
        "concierge":     ["Explore my event data", "Content performance insights"],
        "data_agent":    ["How do I...?",           "Content performance insights"],
        "content_agent": ["Explore my event data",  "How do I...?"],
        "admin_agent":   ["Explore my event data",  "How do I...?"],
        None:            ["Explore my event data",  "How do I...?"],
    }
    switch_chips = _AGENT_SWITCHES.get(agent_used, _AGENT_SWITCHES[None])

    # Branch the system prompt for concierge (help) mode vs data/content mode
    if agent_used == "concierge":
        system_prompt = (
            "The user just asked a how-to question about ON24 and got an answer. "
            "Generate 2 follow-up questions DIRECTLY related to the specific topic just answered — "
            "drill deeper, cover adjacent sub-features, or address common next steps. "
            "Do NOT generate generic unrelated how-to questions. "
            f"User asked: {user_message}\n"
            f"The answer covered: {response_text[:400]}\n"
            "Each suggestion must be a short how-to phrase (3-8 words), conversational. "
            "Return only a JSON array of exactly 2 strings, nothing else."
        )
    else:
        system_prompt = (
            "You anticipate the next 2 questions a user would naturally ask next in a "
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
            "\nDo NOT suggest anything outside this list. Specifically NEVER suggest:\n"
            "- Speaker/presenter performance or metrics\n"
            "- Region, geography, or location data\n"
            "- Individual attendee details or contact info\n"
            "- Revenue, ROI, or financial metrics\n"
            "- Anything the response already said the system cannot do\n"
            "\nReturn only a JSON array of exactly 2 strings, nothing else."
        )

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in response.content if hasattr(b, "text"))
    match = re.search(r'\[.*\]', text, re.DOTALL)
    raw = match.group() if match else text
    try:
        context_chips: list[str] = json.loads(raw)[:2]
    except Exception:
        context_chips = []  # Always return switch chips + Home even if LLM output is malformed

    return context_chips + switch_chips + ["Home"]


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
    # SEC-01: Validate API key on WebSocket upgrade (if auth enabled)
    if settings.api_key:
        query_params = dict(websocket.query_params)
        if query_params.get("api_key") != settings.api_key:
            await websocket.close(code=4001, reason="Unauthorized")
            return

    await websocket.accept()
    client_ip = websocket.client.host if websocket.client else "unknown"
    session_id = "default"

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "message":
                content = data.get("content", "").strip()
                session_id = data.get("session_id", "default")
                confirmed = bool(data.get("confirmed", False))

                # Set per-request client_id from the frontend account switcher.
                # Validated to be within this deployment's hierarchy.
                raw_client_id = data.get("client_id")
                if raw_client_id is not None:
                    try:
                        cid = int(raw_client_id)
                        root = int(settings.on24_client_id)
                        # Only allow if it's the root or a known sub-client.
                        # We use the cached hierarchy (cheap after first call).
                        from app.db.on24_db import get_tenant_client_ids, set_request_client_id as _set
                        # Temporarily set to root to get full list
                        set_request_client_id(root)
                        allowed = set(await get_tenant_client_ids())
                        if cid in allowed:
                            set_request_client_id(cid)
                        else:
                            set_request_client_id(root)
                    except Exception:
                        set_request_client_id(None)
                else:
                    set_request_client_id(None)

                if not content:
                    await websocket.send_json({"type": "error", "message": "Empty message"})
                    continue

                # Strip null bytes and ASCII control characters to prevent prompt-injection
                # payloads that embed hidden instructions via non-printing characters (A03).
                content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content).strip()
                if not content:
                    await websocket.send_json({"type": "error", "message": "Empty message"})
                    continue

                # Reject messages containing script tags or javascript: protocol
                if re.search(r'<script[\s>]|javascript\s*:', content, re.I):
                    await websocket.send_json({"type": "error", "message": "HTML and JavaScript are not allowed in messages."})
                    continue

                # Strip any HTML tags from user input (preserves text content between tags)
                content = re.sub(r'</?[a-z][^>]*>', '', content, flags=re.I).strip()
                if not content:
                    await websocket.send_json({"type": "error", "message": "Please enter a text message."})
                    continue

                # SEC-02: Rate limit WebSocket messages per IP
                if not _check_ws_rate(client_ip):
                    await websocket.send_json({"type": "error", "message": f"Rate limit exceeded ({settings.rate_limit_per_minute} messages/min). Please slow down."})
                    continue

                # Bound message length to prevent prompt-stuffing and resource exhaustion (A03).
                # Higher limit for messages with file attachments (PDF text can be large)
                _MAX_MSG_LEN = 16000 if "[Attached" in content else 4000
                if len(content) > _MAX_MSG_LEN:
                    await websocket.send_json({"type": "error", "message": f"Message too long (max {_MAX_MSG_LEN} characters)."})
                    continue

                # Sanitise session_id: accept only alphanumeric/hyphen/underscore to prevent
                # session-ID-based injection or path traversal in future storage backends (A01).
                if not re.match(r'^[\w\-]{1,128}$', session_id):
                    session_id = "default"

                agent = _get_or_create_agent(session_id)

                # Build permission restriction context for agents
                user_permissions: list[str] = data.get("permissions", [])
                restriction_context = ""
                if user_permissions:
                    restriction_context = await _build_restriction_context(user_permissions)
                agent.restriction_context = restriction_context

                # Load attached image as base64 for vision (if present)
                image_block = None
                raw_image_url = data.get("image_url")
                if raw_image_url and isinstance(raw_image_url, str):
                    try:
                        from app.api.upload import UPLOAD_DIR
                        fname = Path(raw_image_url).name
                        # Sanitise filename — alphanumeric + dots + hyphens only
                        if re.match(r'^[\w\-.]+$', fname):
                            fpath = UPLOAD_DIR / fname
                            if fpath.exists() and fpath.stat().st_size < 5_000_000:
                                b64 = base64.standard_b64encode(fpath.read_bytes()).decode()
                                ext = fpath.suffix.lower().lstrip('.')
                                media_map = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}
                                media_type = media_map.get(ext, 'image/png')
                                image_block = {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}}
                                logger.info(f"Loaded image for vision: {fname} ({fpath.stat().st_size} bytes)")
                    except Exception as e:
                        logger.warning(f"Image load failed: {e}")
                agent.image_block = image_block

                # Check response cache (skip for confirmed actions and short/ambiguous messages)
                cached_result = None
                if not confirmed and len(content) > 5:
                    cached_result = await get_cached_response(content, get_client_id())

                # Notify client we're starting
                await websocket.send_json({"type": "agent_start", "agent": "orchestrator"})

                try:
                    if cached_result:
                        result = cached_result
                        logger.info(f"Cache HIT for: {content[:50]}")
                    else:
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

                    # Send AI content articles if available
                    if result.get("content_articles"):
                        await websocket.send_json({
                            "type": "content_articles",
                            "data": result["content_articles"],
                        })

                    # Send rendered HTML content for preview modal
                    if result.get("content_html"):
                        await websocket.send_json({
                            "type": "content_html",
                            "data": result["content_html"],
                        })

                    # Send proposed calendar events if available
                    if result.get("proposed_events"):
                        await websocket.send_json({
                            "type": "proposed_events",
                            "data": result["proposed_events"],
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

                    # Cache the response for data/concierge queries (not admin/content creation)
                    if not cached_result:
                        _agent_used = result.get("agent_used", "")
                        if _agent_used in ("data_agent", "concierge") and not result.get("requires_confirmation"):
                            await cache_response(content, get_client_id(), result)

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
                            # Guarantee funnel-specific chips when funnel tags are missing
                            if "no funnel tags found" in text.lower():
                                suggestions = [
                                    "How do I add funnel tags?",
                                    "Analyze funnel stages anyway",
                                ]
                            # Inject "Suggest something" chip when content agent asks for direction
                            if agent == "content_agent" and any(
                                kw in text.lower() for kw in ("pick a topic", "what topic", "let me know", "which topic", "just let me know")
                            ):
                                suggestions = ["Suggest something"] + [s for s in suggestions if s != "Suggest something"][:4]
                            # Inject "View proposed calendar" chip for content calendar responses
                            if agent == "content_agent" and any(
                                kw in text.lower() for kw in ("tofu", "mofu", "bofu", "funnel stage", "content calendar", "webinar plan", "proposed event")
                            ):
                                cal_chip = "View proposed calendar"
                                if cal_chip not in suggestions:
                                    suggestions = [cal_chip] + [s for s in suggestions if s != cal_chip][:4]
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
        # Strip null bytes and control characters (matches WS handler)
        v = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', v)
        limit = 16000 if "[Attached" in v else 4000
        if len(v) > limit:
            raise ValueError(f"Message too long (max {limit} characters).")
        # Reject script tags and javascript: protocol
        if re.search(r'<script[\s>]|javascript\s*:', v, re.I):
            raise ValueError("HTML and JavaScript are not allowed in messages.")
        # Strip HTML tags from input (only if there are tags to strip)
        stripped = re.sub(r'</?[a-z][^>]*>', '', v, flags=re.I).strip()
        if v.strip() and not stripped:
            raise ValueError("Please enter a text message.")
        return stripped if stripped else v


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
