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

    # 1. Recent events — all events back to first of previous month, min 10, max 25
    try:
        from app.agents.tools.on24_query_tools import query_events
        events = await query_events(limit=25, past_only=True)
        # Keep at least 10, but trim to events from first of previous month onward
        if len(events) > 10:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            if now.month == 1:
                cutoff_year, cutoff_month = now.year - 1, 12
            else:
                cutoff_year, cutoff_month = now.year, now.month - 1
            cutoff = datetime(cutoff_year, cutoff_month, 1, tzinfo=timezone.utc)
            recent = [e for e in events if e.get("goodafter") and e["goodafter"] >= cutoff.isoformat()]
            events = recent if len(recent) >= 10 else events[:max(10, len(recent))]
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

    # 6. Calendar analytics (3-month trends + top events by engagement)
    try:
        await prefetch_calendar_data(client_id)
    except Exception as e:
        logger.warning(f"Prefetch calendar data failed (outer): {e}")

    # 7. Pre-warm fixed Tier-2 chip responses (Trends + Explore Content + How-do-I)
    #    These are constant prompts — caching them makes Tier-2/3 navigation <1s.
    try:
        await prewarm_chip_responses(client_id)
    except Exception as e:
        logger.warning(f"Prefetch chip pre-warm failed: {e}")

    elapsed = asyncio.get_event_loop().time() - t0
    logger.info(f"Prefetch complete in {elapsed:.1f}s for client {client_id}")


CALENDAR_DATA_KEY = "calendar_analytics"


async def prefetch_calendar_data(client_id: int | None = None) -> bool:
    """Pre-fetch calendar analytics: 3-month attendance trends + top 20 events by engagement.

    Returns True if data was fetched and stored, False if already cached or failed.
    Safe to call repeatedly — skips if cache is already warm.
    """
    from app.db.on24_db import get_client_id as _get_client_id

    try:
        cid = client_id if client_id is not None else _get_client_id()
    except Exception:
        return False

    # Skip if already cached
    if await get_prefetched(CALENDAR_DATA_KEY, cid):
        return False

    try:
        from app.agents.tools.on24_query_tools import query_attendance_trends, query_top_events
        trends, top_events = await asyncio.gather(
            query_attendance_trends(months=3),
            query_top_events(limit=20, sort_by="engagement", months=3),
        )
        await _store(CALENDAR_DATA_KEY, {"attendance_trends": trends, "top_events": top_events}, cid)
        logger.info(f"Prefetch: calendar analytics cached ({len(trends)} months, {len(top_events)} events)")
        return True
    except Exception as e:
        logger.warning(f"Prefetch calendar data failed: {e}")
        return False


async def get_prefetched_calendar_data(client_id: int) -> dict | None:
    """Return pre-fetched calendar analytics, or None if not cached."""
    return await get_prefetched(CALENDAR_DATA_KEY, client_id)


# Fixed Tier-2 chip prompts that are candidates for pre-warming.
# Key = display label used in the UI, value = prompt sent to the agent.
TRENDS_CHIP_PROMPTS: list[tuple[str, str]] = [
    ("Attendance over time",       "Show me attendance trends over the last 12 months as a line chart. Use get_attendance_trends with months=12, then generate_chart_data with chart_type=\"line\", x_key=\"period\", y_keys=[\"attendees\"]. Title: \"Attendance Over Time\"."),
    ("Registrations over time",    "Show me registration trends over the last 12 months as a line chart. Use get_attendance_trends with months=12, then generate_chart_data with chart_type=\"line\", x_key=\"period\", y_keys=[\"registrants\"]. Title: \"Registrations Over Time\"."),
    ("Engagement scores over time","Show me average engagement score trends over the last 12 months as a line chart. Use get_attendance_trends with months=12, then generate_chart_data with chart_type=\"line\", x_key=\"period\", y_keys=[\"avg_engagement\"]. Title: \"Avg Engagement Score Over Time\"."),
    ("Top events by engagement",   "Show me the top 10 events by engagement score as a bar chart."),
]

EXPLORE_CONTENT_PROMPTS: list[tuple[str, str]] = [
    ("Key Takeaways",    "Show me the most recent AI-generated Key Takeaways articles"),
    ("Blog Posts",       "Show me the most recent AI-generated blog posts"),
    ("Follow-up Emails", "Show me the most recent AI-generated follow-up emails"),
    ("Social Media",     "Show me the most recent AI-generated social media posts"),
]

HOW_DO_I_PROMPTS: list[str] = [
    "How do I set up a webinar?",
    "How do I set up polls for my event?",
    "How do I configure a registration page?",
    "How do I set up an integration?",
    "How do I view my event analytics?",
    "How do I create an Engagement Hub?",
    "How do I prepare as a presenter?",
    "How do I use Connect integrations?",
]


async def prewarm_chip_responses(client_id: int) -> None:
    """Pre-warm response cache for all fixed Tier-2 chip prompts.

    Calls the DataAgent and OrchestratorAgent directly for fixed prompts so the
    first user to click any Tier-2 chip gets a cached response (<1s) instead of
    waiting for a live LLM call (~5-10s).

    Only warms if the cache entry is missing — safe to call repeatedly.
    """
    from app.services.response_cache import get_cached_response, cache_response
    from app.agents.data_agent import DataAgent
    from app.agents.orchestrator import OrchestratorAgent

    data_agent = DataAgent()
    orch = OrchestratorAgent()

    async def _warm_data(prompt: str) -> None:
        """Warm a single data-agent prompt if not already cached."""
        if await get_cached_response(prompt, client_id):
            return  # already warm
        try:
            result = await data_agent.run(prompt)
            await cache_response(prompt, client_id, result)
            logger.debug(f"Chip pre-warm cached: {prompt[:60]}")
        except Exception as e:
            logger.debug(f"Chip pre-warm failed for '{prompt[:40]}': {e}")

    async def _warm_orch(prompt: str) -> None:
        """Warm an orchestrator prompt (concierge how-to) if not already cached."""
        if await get_cached_response(prompt, client_id):
            return
        try:
            result = await orch.process_message(prompt)
            if result.get("agent_used") == "concierge":
                await cache_response(prompt, client_id, result)
                logger.debug(f"How-to pre-warm cached: {prompt[:60]}")
        except Exception as e:
            logger.debug(f"How-to pre-warm failed for '{prompt[:40]}': {e}")

    # Trends chips (parallel)
    await asyncio.gather(*[_warm_data(p) for _, p in TRENDS_CHIP_PROMPTS], return_exceptions=True)
    logger.info("Chip pre-warm: Trends done")

    # Explore Content chips (parallel)
    await asyncio.gather(*[_warm_data(p) for _, p in EXPLORE_CONTENT_PROMPTS], return_exceptions=True)
    logger.info("Chip pre-warm: Explore Content done")

    # How-do-I chips (parallel — each spawns 2 LLM calls so throttle slightly)
    for prompt in HOW_DO_I_PROMPTS:
        await _warm_orch(prompt)
    logger.info("Chip pre-warm: How-do-I done")
