"""Benchmark ON24 READ-only API endpoints -- REST vs Direct DB.

Runs each GET endpoint 3 times, records median response time, and optionally
compares against an equivalent direct-DB query on on24master.

CRITICAL: This script calls ONLY GET endpoints. No writes/updates/deletes.

Usage:
    cd backend
    python -m tests.benchmark_read_apis
"""

import asyncio
import json
import shutil
import ssl
import sys
import tempfile
import time
import os
from datetime import datetime
from pathlib import Path
from statistics import median

# ---------------------------------------------------------------------------
# Path setup — allow running from backend/ or project root
# ---------------------------------------------------------------------------
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.services.on24_client import ON24Client, ON24APIError  # noqa: E402
from app.config import settings  # noqa: E402

RUNS = 3
RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_FILE = RESULTS_DIR / "benchmark_results.json"

# ---------------------------------------------------------------------------
# Direct-DB queries (on24master) — keyed by benchmark name
# ---------------------------------------------------------------------------
DB_QUERIES: dict[str, str] = {
    "list_events": (
        "SELECT * FROM on24master.event "
        "WHERE client_id = ANY($1::bigint[]) "
        "AND goodafter >= '2025-12-01' AND goodafter <= '2026-03-14' "
        "ORDER BY goodafter DESC LIMIT 10"
    ),
    "list_client_attendees": (
        "SELECT da.* FROM on24master.dw_attendee da "
        "JOIN on24master.event e ON da.event_id = e.event_id "
        "WHERE e.client_id = ANY($1::bigint[]) "
        "LIMIT 10"
    ),
    "list_client_registrants": (
        "SELECT eu.* FROM on24master.event_user eu "
        "JOIN on24master.event e ON eu.event_id = e.event_id "
        "WHERE e.client_id = ANY($1::bigint[]) "
        "LIMIT 10"
    ),
    "list_client_leads": (
        "SELECT * FROM on24master.dw_lead "
        "WHERE client_id = ANY($1::bigint[]) "
        "LIMIT 10"
    ),
    "list_event_attendees": (
        "SELECT * FROM on24master.dw_attendee "
        "WHERE event_id = $2 "
        "LIMIT 10"
    ),
    "list_event_registrants": (
        "SELECT eu.* FROM on24master.event_user eu "
        "WHERE eu.event_id = $2 AND eu.userrole = 'Participant' "
        "LIMIT 10"
    ),
    "get_event": (
        "SELECT * FROM on24master.event "
        "WHERE event_id = $2 AND client_id = ANY($1::bigint[])"
    ),
    "get_event_polls": (
        "SELECT q.question_id, q.description AS question_text, qxa.answer "
        "FROM on24master.event_user eu "
        "JOIN on24master.event_user_x_answer euxa ON eu.event_user_id = euxa.event_user_id "
        "JOIN on24master.question_x_answer qxa ON euxa.answer_id = qxa.answer_id "
        "JOIN on24master.question q ON qxa.question_id = q.question_id "
        "JOIN on24master.media_url mu ON q.media_url_id = mu.media_url_id "
        "WHERE eu.event_id = $2 AND mu.cd = 'poll' "
        "LIMIT 50"
    ),
    "get_event_surveys": (
        "SELECT q.question_id, q.description AS question_text, qxa.answer "
        "FROM on24master.event_user eu "
        "JOIN on24master.event_user_x_answer euxa ON eu.event_user_id = euxa.event_user_id "
        "JOIN on24master.question_x_answer qxa ON euxa.answer_id = qxa.answer_id "
        "JOIN on24master.question q ON qxa.question_id = q.question_id "
        "JOIN on24master.media_url mu ON q.media_url_id = mu.media_url_id "
        "WHERE eu.event_id = $2 AND mu.cd = 'survey' "
        "LIMIT 50"
    ),
    "get_event_resources": (
        "SELECT chtd.event_user_id, chtd.media_url_id, mu.name "
        "FROM on24master.content_hit_track_details chtd "
        "JOIN on24master.media_url mu ON chtd.media_url_id = mu.media_url_id "
        "JOIN on24master.event_user eu ON chtd.event_user_id = eu.event_user_id "
        "WHERE eu.event_id = $2 AND chtd.action = 'TotalHits' "
        "LIMIT 50"
    ),
}


# ---------------------------------------------------------------------------
# DB connection helper
# ---------------------------------------------------------------------------
async def _get_db_pool() -> "asyncpg.Pool | None":
    """Create a one-off asyncpg pool for on24master, or None if unconfigured."""
    import asyncpg

    if not settings.on24_db_url:
        return None

    ssl_ctx = _build_ssl_context()

    url = settings.on24_db_url.replace("postgresql+asyncpg://", "")
    userpass, hostdb = url.split("@", 1)
    user, password = userpass.split(":", 1)
    hostport, database = hostdb.split("/", 1)
    host, port = hostport.rsplit(":", 1)

    try:
        pool = await asyncpg.create_pool(
            host=host,
            port=int(port),
            database=database,
            user=user,
            password=password,
            ssl=ssl_ctx,
            min_size=1,
            max_size=5,
            command_timeout=30,
        )
        return pool
    except Exception as exc:
        print(f"  [WARN] Could not connect to on24master: {exc}")
        return None


def _build_ssl_context() -> ssl.SSLContext | None:
    """Build SSL context from cert env vars (mirrors on24_db.py)."""
    if not settings.db_pg_ssl_root_cert_content:
        return None

    def unescape(s: str) -> str:
        return s.replace("\\n", "\n").strip('"').strip("'")

    ca = unescape(settings.db_pg_ssl_root_cert_content)
    cert = unescape(settings.db_pg_ssl_cert_content)
    key = unescape(settings.db_pg_ssl_key_content)

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_REQUIRED

    tmp_dir = tempfile.mkdtemp()
    try:
        ca_path = os.path.join(tmp_dir, "ca.pem")
        cert_path = os.path.join(tmp_dir, "client.crt")
        key_path = os.path.join(tmp_dir, "client.key")
        with open(ca_path, "w", newline="\n") as f:
            f.write(ca)
        with open(cert_path, "w", newline="\n") as f:
            f.write(cert)
        with open(key_path, "w", newline="\n") as f:
            f.write(key)
        ctx.load_verify_locations(ca_path)
        ctx.load_cert_chain(cert_path, key_path)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return ctx


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------
async def benchmark_endpoint(name: str, coro_factory, runs: int = RUNS) -> dict:
    """Run an endpoint multiple times and return median timing."""
    times: list[float] = []
    error: str | None = None
    result_sample = None

    for _ in range(runs):
        start = time.perf_counter()
        try:
            resp = await coro_factory()
            elapsed = time.perf_counter() - start
            times.append(elapsed)
            if result_sample is None and resp is not None:
                # Capture shape info
                if isinstance(resp, dict):
                    result_sample = {k: type(v).__name__ for k, v in resp.items()}
                elif isinstance(resp, list):
                    result_sample = f"list[{len(resp)} items]"
        except ON24APIError as e:
            elapsed = time.perf_counter() - start
            error = f"HTTP {e.status_code}: {e.message[:80]}"
            times.append(elapsed)
        except Exception as e:
            elapsed = time.perf_counter() - start
            error = str(e)[:100]
            times.append(elapsed)

    return {
        "name": name,
        "median_ms": round(median(times) * 1000, 1) if times else None,
        "min_ms": round(min(times) * 1000, 1) if times else None,
        "max_ms": round(max(times) * 1000, 1) if times else None,
        "runs": len(times),
        "error": error,
    }


async def benchmark_db_query(
    name: str, pool, query: str, params: list, runs: int = RUNS
) -> dict:
    """Run a direct DB query and return median timing."""
    times: list[float] = []
    error: str | None = None

    for _ in range(runs):
        start = time.perf_counter()
        try:
            async with pool.acquire() as conn:
                await conn.fetch(query, *params)
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        except Exception as e:
            elapsed = time.perf_counter() - start
            error = str(e)[:100]
            times.append(elapsed)

    return {
        "name": f"DB: {name}",
        "median_ms": round(median(times) * 1000, 1) if times else None,
        "min_ms": round(min(times) * 1000, 1) if times else None,
        "max_ms": round(max(times) * 1000, 1) if times else None,
        "runs": len(times),
        "error": error,
    }


# ---------------------------------------------------------------------------
# Print helpers
# ---------------------------------------------------------------------------
def print_header(title: str) -> None:
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}")


def print_table(rows: list[dict]) -> None:
    """Print a formatted table of benchmark results."""
    col_w = {"name": 40, "median_ms": 12, "min_ms": 10, "max_ms": 10, "runs": 5, "error": 40}
    header = (
        f"{'Endpoint':<{col_w['name']}} "
        f"{'Median(ms)':>{col_w['median_ms']}} "
        f"{'Min(ms)':>{col_w['min_ms']}} "
        f"{'Max(ms)':>{col_w['max_ms']}} "
        f"{'Runs':>{col_w['runs']}} "
        f"{'Error':<{col_w['error']}}"
    )
    print(header)
    print("-" * len(header))

    for r in rows:
        med = f"{r['median_ms']:.1f}" if r["median_ms"] is not None else "N/A"
        mn = f"{r['min_ms']:.1f}" if r.get("min_ms") is not None else "N/A"
        mx = f"{r['max_ms']:.1f}" if r.get("max_ms") is not None else "N/A"
        err = (r["error"] or "")[:col_w["error"]]
        print(
            f"{r['name']:<{col_w['name']}} "
            f"{med:>{col_w['median_ms']}} "
            f"{mn:>{col_w['min_ms']}} "
            f"{mx:>{col_w['max_ms']}} "
            f"{r['runs']:>{col_w['runs']}} "
            f"{err:<{col_w['error']}}"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> None:
    print_header("ON24 READ API Benchmark")
    print(f"  Client ID : {settings.on24_client_id}")
    print(f"  Base URL  : {settings.on24_base_url}")
    print(f"  Runs/EP   : {RUNS}")
    print(f"  Started   : {datetime.now().isoformat()}")

    client = ON24Client()
    all_results: list[dict] = []

    # ------------------------------------------------------------------
    # Phase 0: Fetch a valid event_id for event-level endpoints
    # ------------------------------------------------------------------
    print("\n[1/7] Fetching a sample event ID...")
    event_id: int | None = None
    try:
        # Use a recent 60-day window to ensure events exist (well within 180-day limit)
        from datetime import timedelta
        _end = datetime.now()
        _start = _end - timedelta(days=60)
        _start_str = _start.strftime("%Y-%m-%d")
        _end_str = _end.strftime("%Y-%m-%d")
        print(f"  Date range: {_start_str} to {_end_str}")
        events_resp = await client.list_events(
            start_date=_start_str, end_date=_end_str, items_per_page=5
        )
        # ON24 returns events under various keys
        events_list = (
            events_resp.get("events")
            or events_resp.get("items")
            or (events_resp if isinstance(events_resp, list) else [])
        )
        if events_list and isinstance(events_list, list) and len(events_list) > 0:
            event_id = events_list[0].get("eventid") or events_list[0].get("eventId")
            print(f"  Using event_id: {event_id}")
        else:
            print("  [WARN] No events found — event-level endpoints will be skipped.")
    except Exception as exc:
        print(f"  [ERROR] Could not fetch events: {exc}")

    # ------------------------------------------------------------------
    # Phase 1: Client-Level Analytics (REST API)
    # ------------------------------------------------------------------
    print("\n[2/7] Benchmarking client-level REST endpoints...")

    client_benchmarks = [
        ("list_events", lambda: client.list_events(
            start_date="2025-12-01", end_date="2026-03-14", items_per_page=10)),
        ("list_client_attendees", lambda: client.list_client_attendees(
            start_date="2025-12-01", end_date="2026-03-14", items_per_page=10)),
        ("get_attendee_by_email", lambda: client.get_attendee_by_email(
            email="test@example.com")),
        ("get_attendee_all_events", lambda: client.get_attendee_all_events(
            email="test@example.com", items_per_page=10)),
        ("list_client_registrants", lambda: client.list_client_registrants(
            start_date="2025-12-01", end_date="2026-03-14", items_per_page=10)),
        ("get_registrant_by_email", lambda: client.get_registrant_by_email(
            email="test@example.com")),
        ("get_registrant_all_events", lambda: client.get_registrant_all_events(
            email="test@example.com", items_per_page=10)),
        ("get_survey_library", lambda: client.get_survey_library()),
        ("get_engaged_accounts", lambda: client.get_engaged_accounts()),
        ("list_client_leads", lambda: client.list_client_leads(
            start_date="2025-12-01", end_date="2026-03-14", items_per_page=10)),
        ("get_pep", lambda: client.get_pep(email="test@example.com")),
        ("list_client_presenters", lambda: client.list_client_presenters()),
        ("list_sub_clients", lambda: client.list_sub_clients()),
        ("get_realtime_user_questions", lambda: client.get_realtime_user_questions()),
        ("list_users", lambda: client.list_users()),
    ]

    for name, factory in client_benchmarks:
        result = await benchmark_endpoint(name, factory)
        status = f"{result['median_ms']}ms" if result["median_ms"] else "ERR"
        err_hint = f" ({result['error'][:40]})" if result["error"] else ""
        print(f"  {name:<40} {status:>10}{err_hint}")
        all_results.append(result)

    # ------------------------------------------------------------------
    # Phase 2: Event-Level Analytics (REST API)
    # ------------------------------------------------------------------
    print("\n[3/7] Benchmarking event-level REST endpoints...")

    if event_id is not None:
        event_benchmarks = [
            ("list_event_attendees", lambda: client.list_event_attendees(
                event_id, items_per_page=10)),
            ("get_event_viewing_sessions", lambda: client.get_event_viewing_sessions(
                event_id, items_per_page=10)),
            ("get_event_polls", lambda: client.get_event_polls(event_id)),
            ("get_event_surveys", lambda: client.get_event_surveys(event_id)),
            ("get_event_resources", lambda: client.get_event_resources(event_id)),
            ("get_event_ctas", lambda: client.get_event_ctas(event_id)),
            ("get_event_group_chat", lambda: client.get_event_group_chat(event_id)),
            ("get_event_email_stats", lambda: client.get_event_email_stats(event_id)),
            ("get_event_certifications", lambda: client.get_event_certifications(event_id)),
            ("get_event_content_activity", lambda: client.get_event_content_activity(event_id)),
            ("get_event_presenters", lambda: client.get_event_presenters(event_id)),
            ("get_event_calendar_reminder", lambda: client.get_event_calendar_reminder(event_id)),
            ("get_event_email", lambda: client.get_event_email(event_id)),
            ("get_event_presenter_chat", lambda: client.get_event_presenter_chat(event_id)),
            ("get_event_slides", lambda: client.get_event_slides(event_id)),
            ("list_event_registrants", lambda: client.list_event_registrants(
                event_id, items_per_page=10)),
            ("get_event", lambda: client.get_event(event_id)),
            ("get_registration_fields", lambda: client.get_registration_fields(event_id)),
        ]

        for name, factory in event_benchmarks:
            result = await benchmark_endpoint(name, factory)
            status = f"{result['median_ms']}ms" if result["median_ms"] else "ERR"
            err_hint = f" ({result['error'][:40]})" if result["error"] else ""
            print(f"  {name:<40} {status:>10}{err_hint}")
            all_results.append(result)
    else:
        print("  [SKIP] No event_id available — skipping event-level endpoints.")

    # ------------------------------------------------------------------
    # Phase 3: Content + Helper Endpoints (REST API)
    # ------------------------------------------------------------------
    print("\n[4/7] Benchmarking content & helper REST endpoints...")

    helper_benchmarks = [
        ("list_media_manager_content", lambda: client.list_media_manager_content(
            items_per_page=10)),
        # get_ehub_content requires a gateway_id — skip if unknown
        ("get_custom_account_tags", lambda: client.get_custom_account_tags()),
        ("get_account_managers", lambda: client.get_account_managers()),
        ("get_event_managers", lambda: client.get_event_managers()),
        ("get_event_profiles", lambda: client.get_event_profiles()),
        ("get_event_types", lambda: client.get_event_types()),
        ("get_languages", lambda: client.get_languages()),
        ("get_replacement_tokens", lambda: client.get_replacement_tokens()),
        ("get_sales_reps", lambda: client.get_sales_reps()),
        ("get_signal_contacts", lambda: client.get_signal_contacts()),
        ("get_technical_reps", lambda: client.get_technical_reps()),
        ("get_timezones", lambda: client.get_timezones()),
    ]

    for name, factory in helper_benchmarks:
        result = await benchmark_endpoint(name, factory)
        status = f"{result['median_ms']}ms" if result["median_ms"] else "ERR"
        err_hint = f" ({result['error'][:40]})" if result["error"] else ""
        print(f"  {name:<40} {status:>10}{err_hint}")
        all_results.append(result)

    # ------------------------------------------------------------------
    # Phase 4: MCP server read tools
    # ------------------------------------------------------------------
    print("\n[5/7] Benchmarking MCP server read tools...")

    mcp_results: list[dict] = []
    mcp_url = settings.mcp_server_url.rstrip("/") + "/mcp"

    async def _call_mcp(tool_name: str, arguments: dict) -> dict:
        from mcp.client.streamable_http import streamablehttp_client
        from mcp import ClientSession
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
        if result.content:
            import json as _json
            try:
                return _json.loads(result.content[0].text)
            except Exception:
                return {"raw": result.content[0].text}
        return {}

    try:
        # Quick connectivity test
        await _call_mcp("get_timezones", {})
        mcp_available = True
        print(f"  MCP server at {mcp_url} — connected")
    except Exception as exc:
        mcp_available = False
        print(f"  [SKIP] MCP server not available: {exc}")

    if mcp_available:
        mcp_benchmarks = [
            ("list_events", {"start_date": "2025-12-01", "end_date": "2026-03-14", "items_per_page": 10}),
            ("list_client_attendees", {"start_date": "2025-12-01", "end_date": "2026-03-14", "items_per_page": 10}),
            ("list_client_registrants", {"start_date": "2025-12-01", "end_date": "2026-03-14", "items_per_page": 10}),
            ("list_client_leads", {"start_date": "2025-12-01", "end_date": "2026-03-14", "items_per_page": 10}),
            ("get_event_types", {}),
            ("get_timezones", {}),
        ]
        if event_id is not None:
            mcp_benchmarks += [
                ("get_event", {"event_id": event_id}),
                ("list_event_attendees", {"event_id": event_id, "items_per_page": 10}),
                ("list_event_registrants", {"event_id": event_id, "items_per_page": 10}),
                ("get_event_polls", {"event_id": event_id}),
                ("get_event_surveys", {"event_id": event_id}),
                ("get_event_resources", {"event_id": event_id}),
            ]

        for tool_name, args in mcp_benchmarks:
            result = await benchmark_endpoint(
                f"MCP: {tool_name}",
                lambda tn=tool_name, a=args: _call_mcp(tn, a),
            )
            status = f"{result['median_ms']}ms" if result["median_ms"] else "ERR"
            err_hint = f" ({result['error'][:40]})" if result["error"] else ""
            print(f"  {result['name']:<40} {status:>10}{err_hint}")
            mcp_results.append(result)

    # ------------------------------------------------------------------
    # Phase 5: Direct DB queries (on24master)
    # ------------------------------------------------------------------
    print("\n[6/7] Benchmarking direct DB queries (on24master)...")

    db_pool = await _get_db_pool()
    db_results: list[dict] = []

    if db_pool is not None:
        # Resolve tenant IDs for parameterised queries
        tenant_ids = [int(settings.on24_client_id)]
        try:
            rows = await db_pool.fetch(
                "SELECT DISTINCT sub_client_id FROM on24master.client_hierarchy "
                "WHERE client_id = $1",
                tenant_ids[0],
            )
            tenant_ids += [r["sub_client_id"] for r in rows]
        except Exception:
            pass  # proceed with root only

        for qname, query in DB_QUERIES.items():
            # Build params: $1 = tenant_ids, $2 = event_id (if present)
            params: list = [tenant_ids]
            if "$2" in query:
                if event_id is None:
                    db_results.append({
                        "name": f"DB: {qname}",
                        "median_ms": None, "min_ms": None, "max_ms": None,
                        "runs": 0, "error": "no event_id",
                    })
                    continue
                params.append(event_id)

            result = await benchmark_db_query(qname, db_pool, query, params)
            status = f"{result['median_ms']}ms" if result["median_ms"] else "ERR"
            err_hint = f" ({result['error'][:40]})" if result["error"] else ""
            print(f"  {result['name']:<40} {status:>10}{err_hint}")
            db_results.append(result)

        await db_pool.close()
    else:
        print("  [SKIP] ON24 DB not available — skipping direct DB benchmarks.")

    # ------------------------------------------------------------------
    # [7/7] Summary tables
    # ------------------------------------------------------------------
    print_header("REST API Results")
    print_table(all_results)

    if mcp_results:
        print_header("MCP Server Results")
        print_table(mcp_results)

    if db_results:
        print_header("Direct DB Results")
        print_table(db_results)

    # 3-way comparison: REST vs MCP vs DB
    rest_by_name = {r["name"]: r for r in all_results}
    mcp_by_name = {r["name"].replace("MCP: ", ""): r for r in mcp_results}
    db_by_name = {r["name"].replace("DB: ", ""): r for r in db_results}

    # Collect all endpoint names that appear in at least 2 sources
    all_names = set(rest_by_name) | set(mcp_by_name) | set(db_by_name)
    comparisons = []
    for name in sorted(all_names):
        rest_ms = rest_by_name.get(name, {}).get("median_ms")
        mcp_ms = mcp_by_name.get(name, {}).get("median_ms")
        db_ms = db_by_name.get(name, {}).get("median_ms")
        sources = sum(1 for v in [rest_ms, mcp_ms, db_ms] if v is not None)
        if sources >= 2:
            comparisons.append({"endpoint": name, "rest_ms": rest_ms, "mcp_ms": mcp_ms, "db_ms": db_ms})

    if comparisons:
        print_header("REST vs MCP vs DB Comparison")
        print(f"{'Endpoint':<35} {'REST(ms)':>10} {'MCP(ms)':>10} {'DB(ms)':>10} {'MCP/REST':>10} {'REST/DB':>10}")
        print("-" * 89)
        for c in comparisons:
            rest_s = f"{c['rest_ms']:.1f}" if c["rest_ms"] else "N/A"
            mcp_s = f"{c['mcp_ms']:.1f}" if c["mcp_ms"] else "N/A"
            db_s = f"{c['db_ms']:.1f}" if c["db_ms"] else "N/A"
            mcp_ratio = f"{c['mcp_ms'] / c['rest_ms']:.1f}x" if c["mcp_ms"] and c["rest_ms"] and c["rest_ms"] > 0 else "N/A"
            rest_db_ratio = f"{c['rest_ms'] / c['db_ms']:.1f}x" if c["rest_ms"] and c["db_ms"] and c["db_ms"] > 0 else "N/A"
            print(f"{c['endpoint']:<35} {rest_s:>10} {mcp_s:>10} {db_s:>10} {mcp_ratio:>10} {rest_db_ratio:>10}")

    # ------------------------------------------------------------------
    # Save JSON
    # ------------------------------------------------------------------
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    output = {
        "timestamp": datetime.now().isoformat(),
        "client_id": settings.on24_client_id,
        "base_url": settings.on24_base_url,
        "mcp_url": mcp_url,
        "event_id_used": event_id,
        "runs_per_endpoint": RUNS,
        "rest_api": all_results,
        "mcp": mcp_results,
        "direct_db": db_results,
        "comparison": comparisons,
    }

    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to {RESULTS_FILE}")

    # Cleanup
    await client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
