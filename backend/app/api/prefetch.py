"""Prefetch API — serves pre-cached data for instant chip responses.

These endpoints return data from the Redis prefetch cache (warmed on startup).
If cache is empty, they fall back to live queries. This eliminates the
orchestrator+agent LLM roundtrip for common first-click queries.
"""

import logging

from fastapi import APIRouter

from app.db.on24_db import get_client_id
from app.services.data_prefetch import get_prefetched

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/recent-events")
async def get_recent_events():
    """Return prefetched recent 10 events (instant, no LLM call)."""
    client_id = get_client_id()
    cached = await get_prefetched("recent_events", client_id)
    if cached:
        return {"events": cached, "source": "prefetch"}

    # Fallback: live query
    from app.agents.tools.on24_query_tools import query_events
    events = await query_events(limit=10, past_only=True)
    return {"events": events, "source": "live"}


@router.get("/event-details")
async def get_event_details():
    """Return prefetched event details + KPIs for recent 10 events."""
    client_id = get_client_id()
    cached = await get_prefetched("event_details", client_id)
    if cached:
        return {"events": cached, "source": "prefetch"}
    return {"events": [], "source": "empty"}


@router.get("/ai-content/{content_type}")
async def get_ai_content(content_type: str):
    """Return prefetched AI content by type (BLOG, KEYTAKEAWAYS, etc.)."""
    client_id = get_client_id()
    content_map = await get_prefetched("ai_content", client_id)
    if content_map:
        ct = content_type.upper()
        articles = content_map.get(ct, [])
        if articles:
            return {"articles": articles, "content_type": ct, "source": "prefetch"}

    # Fallback: live query
    from app.agents.tools.on24_query_tools import query_ai_content
    articles = await query_ai_content(content_type=content_type, limit=3)
    return {"articles": articles, "content_type": content_type.upper(), "source": "live"}


@router.get("/attendance-trends")
async def get_attendance_trends():
    """Return prefetched 12-month attendance trends."""
    client_id = get_client_id()
    cached = await get_prefetched("attendance_trends", client_id)
    if cached:
        return {"trends": cached, "source": "prefetch"}

    from app.agents.tools.on24_query_tools import query_attendance_trends
    trends = await query_attendance_trends(months=12)
    return {"trends": trends, "source": "live"}


@router.post("/refresh")
async def refresh_prefetch():
    """Manually trigger a prefetch refresh."""
    from app.services.data_prefetch import prefetch_common_data
    import asyncio
    asyncio.create_task(prefetch_common_data())
    return {"status": "refresh started"}
