"""Data prefetch service — warm Redis cache with commonly requested data.

Runs on app startup (background task) and caches the results of the most
common first-click queries so users get instant responses. Data is stored
in Redis with a longer TTL (15 min) than regular chat cache (5 min).

Prefetched data:
- Recent 10 events (list_events)
- Event details + KPIs for each of the 10 events
- AI-ACE content by type (KEYTAKEAWAYS, BLOG, FOLLOWUPEMAI, SOCIALMEDIAP, EBOOK, FAQ)
- Attendance trends (12 months)
"""

import asyncio
import json
import logging
from typing import Any

from app.config import settings
from app.services.response_cache import get_redis

logger = logging.getLogger(__name__)

# Prefetch cache lives longer than regular chat cache (15 min vs 5 min)
PREFETCH_TTL = 900  # 15 minutes

# Redis key prefix for prefetched data
PREFIX = "prefetch"


async def _store(key: str, data: Any, client_id: int) -> None:
    """Store prefetched data in Redis."""
    r = await get_redis()
    if not r:
        return
    try:
        full_key = f"{PREFIX}:{client_id}:{key}"
        await r.setex(full_key, PREFETCH_TTL, json.dumps(data, default=str))
    except Exception as e:
        logger.debug(f"Prefetch store failed for {key}: {e}")


async def get_prefetched(key: str, client_id: int) -> Any | None:
    """Retrieve prefetched data from Redis."""
    r = await get_redis()
    if not r:
        return None
    try:
        full_key = f"{PREFIX}:{client_id}:{key}"
        cached = await r.get(full_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.debug(f"Prefetch get failed for {key}: {e}")
    return None


async def prefetch_common_data() -> None:
    """Prefetch commonly requested data into Redis.

    Called on app startup as a background task. Safe to fail — all queries
    have try/except so a single failure doesn't block others.
    """
    from app.db.on24_db import get_client_id, get_tenant_client_ids, get_pool

    try:
        client_id = get_client_id()
        client_ids = await get_tenant_client_ids()
        pool = await get_pool()
    except Exception as e:
        logger.warning(f"Prefetch skipped — DB not available: {e}")
        return

    logger.info(f"Prefetch: warming cache for client {client_id}...")
    t0 = asyncio.get_event_loop().time()

    # 1. Recent 10 events
    try:
        from app.agents.tools.on24_query_tools import query_events
        events = await query_events(limit=10, past_only=True)
        await _store("recent_events", events, client_id)
        logger.info(f"Prefetch: {len(events)} recent events cached")

        # 2. Event details + KPIs for each (parallel)
        from app.agents.tools.on24_query_tools import get_event_detail, compute_event_kpis

        async def _fetch_event(ev: dict) -> dict | None:
            eid = ev.get("event_id")
            if not eid:
                return None
            try:
                detail = await get_event_detail(eid)
                kpis = await compute_event_kpis(eid)
                return {
                    "event_id": eid,
                    "detail": detail,
                    "kpis": kpis,
                }
            except Exception:
                return None

        event_data = await asyncio.gather(*[_fetch_event(e) for e in events[:10]])
        event_data = [d for d in event_data if d]
        await _store("event_details", event_data, client_id)
        logger.info(f"Prefetch: {len(event_data)} event details+KPIs cached")

        # 3. Key Takeaways for recent events (parallel)
        from app.api.calendar import _parse_kt_sections

        async def _fetch_kt(ev: dict) -> dict | None:
            eid = ev.get("event_id")
            if not eid:
                return None
            try:
                sql = """
                    SELECT vl.media_content
                    FROM on24master.video_library vl
                    WHERE vl.source_event_id = $1
                      AND vl.source = 'AUTOGEN_KEYTAKEAWAYS'
                      AND vl.client_id = ANY($2::bigint[])
                    ORDER BY LENGTH(vl.media_content) DESC
                    LIMIT 1
                """
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(sql, eid, client_ids, timeout=8)
                if row and row["media_content"]:
                    sections = _parse_kt_sections(row["media_content"])
                    return {"event_id": eid, "kt_sections": sections}
            except Exception:
                pass
            return None

        kt_data = await asyncio.gather(*[_fetch_kt(e) for e in events[:10]])
        kt_data = [d for d in kt_data if d]
        await _store("event_kt_sections", kt_data, client_id)
        logger.info(f"Prefetch: {len(kt_data)} Key Takeaways cached")

    except Exception as e:
        logger.warning(f"Prefetch events failed: {e}")

    # 4. AI content by type (parallel)
    try:
        from app.agents.tools.on24_query_tools import query_ai_content

        content_types = ["KEYTAKEAWAYS", "BLOG", "FOLLOWUPEMAIL", "SOCIALMEDIA", "EBOOK", "FAQ"]

        async def _fetch_content(ct: str) -> tuple[str, list]:
            try:
                articles = await query_ai_content(content_type=ct, limit=3)
                return (ct, articles)
            except Exception:
                return (ct, [])

        content_results = await asyncio.gather(*[_fetch_content(ct) for ct in content_types])
        content_map = {ct: articles for ct, articles in content_results if articles}
        await _store("ai_content", content_map, client_id)
        logger.info(f"Prefetch: AI content cached for {len(content_map)} types")
    except Exception as e:
        logger.warning(f"Prefetch AI content failed: {e}")

    # 5. Attendance trends (12 months)
    try:
        from app.agents.tools.on24_query_tools import query_attendance_trends
        trends = await query_attendance_trends(months=12)
        await _store("attendance_trends", trends, client_id)
        logger.info(f"Prefetch: attendance trends cached ({len(trends)} months)")
    except Exception as e:
        logger.warning(f"Prefetch trends failed: {e}")

    elapsed = asyncio.get_event_loop().time() - t0
    logger.info(f"Prefetch complete in {elapsed:.1f}s for client {client_id}")
