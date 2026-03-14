"""Benchmark: ON24 REST API vs Direct PostgreSQL access.

Run standalone (requires VPN + ON24 credentials in .env.local):
    python backend/tests/benchmark_api_vs_db.py

Outputs JSON to stdout with per-operation timing (median of 3 runs).
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Any

# Allow running from project root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

# Load .env.local before importing app modules
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env.local")
except ImportError:
    pass

# ── Config ────────────────────────────────────────────────────────────────────

RUNS = 3  # Number of repetitions; median is reported


# ── Timing helpers ────────────────────────────────────────────────────────────

async def timed(coro) -> tuple[float | None, Any, str | None]:
    """Run a coroutine and return (elapsed_ms, result, error_message)."""
    start = time.perf_counter()
    try:
        result = await coro
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed, result, None
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return None, None, str(exc)


async def run_n_times(coro_factory, n: int) -> tuple[float | None, str | None]:
    """Run a coroutine factory n times; return (median_ms, last_error)."""
    timings = []
    last_error = None
    for _ in range(n):
        elapsed, _, err = await timed(coro_factory())
        if err:
            last_error = err
        else:
            timings.append(elapsed)
    if timings:
        return median(timings), last_error
    return None, last_error


# ── REST API benchmarks ───────────────────────────────────────────────────────

async def bench_api_list_events(client, start_date: str) -> dict:
    return await client.list_events(start_date=start_date, items_per_page=25)


async def bench_api_get_event(client, event_id: int) -> dict:
    return await client.get_event(event_id)


async def bench_api_list_registrants(client, event_id: int) -> dict:
    return await client.get(f"event/{event_id}/registrant", params={"itemsPerPage": 100})


async def bench_api_list_attendees(client, event_id: int) -> dict:
    return await client.get(f"event/{event_id}/attendee", params={"itemsPerPage": 100})


async def bench_api_get_polls(client, event_id: int) -> dict:
    return await client.get(f"event/{event_id}/poll")


async def bench_api_attendance_trends(client) -> list[dict]:
    """12 monthly calls — REST API has no aggregate endpoint."""
    results = []
    for i in range(12):
        start = datetime.now() - timedelta(days=30 * (i + 1))
        end = datetime.now() - timedelta(days=30 * i)
        data = await client.list_events(
            start_date=start.strftime("%Y-%m-%dT00:00:00"),
            end_date=end.strftime("%Y-%m-%dT23:59:59"),
            items_per_page=100,
        )
        results.append(data)
    return results


# ── Direct DB benchmarks ──────────────────────────────────────────────────────

async def bench_db_list_events() -> list[dict]:
    from app.agents.tools.on24_query_tools import query_events
    return await query_events(limit=25)


async def bench_db_get_event(event_id: int) -> list[dict]:
    from app.db.on24_db import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM on24master.event WHERE event_id = $1 LIMIT 1",
            event_id,
            timeout=8.0,
        )
    return [dict(r) for r in rows]


async def bench_db_list_registrants(event_id: int) -> list[dict]:
    from app.db.on24_db import get_pool, get_tenant_client_ids
    pool = await get_pool()
    client_ids = await get_tenant_client_ids()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT eu.event_user_id, eu.fname, eu.lname, eu.email,
                   eu.company, eu.create_timestamp
            FROM on24master.event_user eu
            JOIN on24master.event e ON e.event_id = eu.event_id
            WHERE eu.event_id = $1
              AND e.client_id = ANY($2::bigint[])
            LIMIT 500
            """,
            event_id,
            client_ids,
            timeout=8.0,
        )
    return [dict(r) for r in rows]


async def bench_db_list_attendees(event_id: int) -> list[dict]:
    from app.db.on24_db import get_pool, get_tenant_client_ids
    pool = await get_pool()
    client_ids = await get_tenant_client_ids()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT da.event_user_id, da.engagement_score,
                   da.live_minutes, da.archive_minutes
            FROM on24master.dw_attendee da
            WHERE da.event_id = $1
              AND da.client_id = ANY($2::bigint[])
            LIMIT 500
            """,
            event_id,
            client_ids,
            timeout=8.0,
        )
    return [dict(r) for r in rows]


async def bench_db_get_polls(event_id: int) -> list[dict]:
    from app.agents.tools.on24_query_tools import query_polls
    return await query_polls(event_id=event_id)


async def bench_db_engagement_kpis(event_id: int) -> list[dict]:
    from app.db.on24_db import get_pool, get_tenant_client_ids
    pool = await get_pool()
    client_ids = await get_tenant_client_ids()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                SUM(registrant_count)    AS total_registrants,
                SUM(attendee_count)      AS total_attendees,
                AVG(engagement_score_avg) AS avg_engagement,
                SUM(live_attendee_count) AS live_attendees
            FROM on24master.dw_event_session
            WHERE event_id = $1
              AND client_id = ANY($2::bigint[])
            GROUP BY event_id
            """,
            event_id,
            client_ids,
            timeout=8.0,
        )
    return [dict(r) for r in rows]


async def bench_db_attendance_trends() -> list[dict]:
    from app.agents.tools.on24_query_tools import query_attendance_trends
    return await query_attendance_trends(months=12)


async def bench_db_top_events() -> list[dict]:
    from app.agents.tools.on24_query_tools import query_top_events
    return await query_top_events(limit=10)


async def bench_db_audience_companies(event_id: int) -> list[dict]:
    from app.agents.tools.on24_query_tools import query_audience_companies
    return await query_audience_companies(event_id=event_id)


async def bench_db_poll_response_counts(event_id: int) -> list[dict]:
    from app.agents.tools.on24_query_tools import query_polls
    return await query_polls(event_id=event_id)


# ── Main orchestration ────────────────────────────────────────────────────────

async def resolve_test_event() -> int | None:
    """Pick a real recent event ID to use for per-event benchmarks."""
    try:
        from app.agents.tools.on24_query_tools import query_events
        events = await query_events(limit=5, past_only=True)
        if events:
            return events[0]["event_id"]
    except Exception:
        pass
    return None


async def main():
    results = []

    # ── Discover a usable event_id ────────────────────────────────────────────
    print("Resolving test event ID...", file=sys.stderr)
    event_id = await resolve_test_event()
    if event_id:
        print(f"Using event_id={event_id}", file=sys.stderr)
    else:
        print("Could not resolve event_id; per-event DB benchmarks will be skipped.", file=sys.stderr)

    # ── REST API client setup ─────────────────────────────────────────────────
    api_client = None
    try:
        from app.services.on24_client import ON24Client
        api_client = ON24Client()
    except Exception as exc:
        print(f"Could not initialise ON24Client: {exc}", file=sys.stderr)

    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00")

    # ── Helper to record one benchmark row ───────────────────────────────────
    def record(operation: str, api_ms: float | None, db_ms: float | None,
               api_error: str | None = None, db_error: str | None = None):
        results.append({
            "operation": operation,
            "api_ms": round(api_ms, 1) if api_ms is not None else None,
            "db_ms": round(db_ms, 1) if db_ms is not None else None,
            "api_error": api_error,
            "db_error": db_error,
        })
        api_str = f"{api_ms:.0f}ms" if api_ms is not None else f"ERROR: {api_error}"
        db_str = f"{db_ms:.0f}ms" if db_ms is not None else f"ERROR: {db_error}"
        print(f"  {operation:<40} API={api_str}  DB={db_str}", file=sys.stderr)

    # ── 1. List recent events ─────────────────────────────────────────────────
    print("\nRunning benchmarks...", file=sys.stderr)

    if api_client:
        api_ms, api_err = await run_n_times(
            lambda: bench_api_list_events(api_client, start_date), RUNS)
    else:
        api_ms, api_err = None, "ON24Client unavailable"

    db_ms, db_err = await run_n_times(bench_db_list_events, RUNS)
    record("List recent events (30 days)", api_ms, db_ms, api_err, db_err)

    # ── 2. Get single event detail ────────────────────────────────────────────
    if api_client and event_id:
        api_ms, api_err = await run_n_times(
            lambda: bench_api_get_event(api_client, event_id), RUNS)
    else:
        api_ms, api_err = None, "ON24Client or event_id unavailable"

    if event_id:
        db_ms, db_err = await run_n_times(lambda: bench_db_get_event(event_id), RUNS)
    else:
        db_ms, db_err = None, "No event_id"
    record("Get single event detail", api_ms, db_ms, api_err, db_err)

    # ── 3. List event registrants ─────────────────────────────────────────────
    if api_client and event_id:
        api_ms, api_err = await run_n_times(
            lambda: bench_api_list_registrants(api_client, event_id), RUNS)
    else:
        api_ms, api_err = None, "ON24Client or event_id unavailable"

    if event_id:
        db_ms, db_err = await run_n_times(lambda: bench_db_list_registrants(event_id), RUNS)
    else:
        db_ms, db_err = None, "No event_id"
    record("List event registrants", api_ms, db_ms, api_err, db_err)

    # ── 4. List event attendees ───────────────────────────────────────────────
    if api_client and event_id:
        api_ms, api_err = await run_n_times(
            lambda: bench_api_list_attendees(api_client, event_id), RUNS)
    else:
        api_ms, api_err = None, "ON24Client or event_id unavailable"

    if event_id:
        db_ms, db_err = await run_n_times(lambda: bench_db_list_attendees(event_id), RUNS)
    else:
        db_ms, db_err = None, "No event_id"
    record("List event attendees", api_ms, db_ms, api_err, db_err)

    # ── 5. Get event polls ────────────────────────────────────────────────────
    if api_client and event_id:
        api_ms, api_err = await run_n_times(
            lambda: bench_api_get_polls(api_client, event_id), RUNS)
    else:
        api_ms, api_err = None, "ON24Client or event_id unavailable"

    if event_id:
        db_ms, db_err = await run_n_times(lambda: bench_db_get_polls(event_id), RUNS)
    else:
        db_ms, db_err = None, "No event_id"
    record("Get event polls", api_ms, db_ms, api_err, db_err)

    # ── 6. Get engagement KPIs ────────────────────────────────────────────────
    # REST API: basic event metadata only (no engagement_score in response)
    if api_client and event_id:
        api_ms, api_err = await run_n_times(
            lambda: bench_api_get_event(api_client, event_id), RUNS)
    else:
        api_ms, api_err = None, "ON24Client or event_id unavailable"

    if event_id:
        db_ms, db_err = await run_n_times(lambda: bench_db_engagement_kpis(event_id), RUNS)
    else:
        db_ms, db_err = None, "No event_id"
    record("Get engagement KPIs", api_ms, db_ms, api_err, db_err)

    # ── 7. Attendance trends (12 months) ──────────────────────────────────────
    if api_client:
        api_ms, api_err = await run_n_times(
            lambda: bench_api_attendance_trends(api_client), RUNS)
    else:
        api_ms, api_err = None, "ON24Client unavailable"

    db_ms, db_err = await run_n_times(bench_db_attendance_trends, RUNS)
    record("Attendance trends (12 months)", api_ms, db_ms, api_err, db_err)

    # ── 8. Top events by engagement ───────────────────────────────────────────
    # REST API: no sorted aggregate endpoint; would require fetching all events + manual sort
    api_ms, api_err = None, "No REST API equivalent (requires N calls + client-side sort)"
    db_ms, db_err = await run_n_times(bench_db_top_events, RUNS)
    record("Top events by engagement", api_ms, db_ms, api_err, db_err)

    # ── 9. Audience companies ─────────────────────────────────────────────────
    api_ms, api_err = None, "Not available in REST API"
    if event_id:
        db_ms, db_err = await run_n_times(lambda: bench_db_audience_companies(event_id), RUNS)
    else:
        db_ms, db_err = None, "No event_id"
    record("Audience companies", api_ms, db_ms, api_err, db_err)

    # ── 10. Poll response counts ──────────────────────────────────────────────
    if api_client and event_id:
        api_ms, api_err = await run_n_times(
            lambda: bench_api_get_polls(api_client, event_id), RUNS)
    else:
        api_ms, api_err = None, "ON24Client or event_id unavailable"

    if event_id:
        db_ms, db_err = await run_n_times(lambda: bench_db_poll_response_counts(event_id), RUNS)
    else:
        db_ms, db_err = None, "No event_id"
    record("Poll response counts", api_ms, db_ms, api_err, db_err)

    # ── Cleanup ───────────────────────────────────────────────────────────────
    if api_client:
        await api_client.close()

    try:
        from app.db.on24_db import close_pool
        await close_pool()
    except Exception:
        pass

    # ── Output ────────────────────────────────────────────────────────────────
    output = {
        "timestamp": datetime.now().isoformat(),
        "runs_per_operation": RUNS,
        "event_id_used": event_id,
        "results": results,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
