"""Query tools that read directly from the ON24 master PostgreSQL database.

SECURITY: Every function calls get_tenant_client_ids() internally to scope all
queries to the current tenant (including sub-clients). client_id is NEVER
accepted as a function parameter.
All queries use parameterised $N placeholders — never string interpolation.

PERFORMANCE RULES:
- Default window: 1 month (30 days). Max window: 24 months (2 years).
- dw_event_session: event-level aggregate (one row per session, NOT per attendee).
  Columns: registrant_count, attendee_count, engagement_score_avg, live_attendee_count, etc.
  No event_user_id column — do NOT join to it for per-attendee lookups.
- dw_attendee: per-attendee row. Has event_user_id, engagement_score, live_minutes.
  Use for per-attendee queries and company breakdowns.
- Never join event_user (585M rows) for aggregates — use dw_event_session counts.
- All aggregate fetches use timeout=8.0s.
"""

import logging
from typing import Any

from app.db.on24_db import get_pool, get_tenant_client_ids

logger = logging.getLogger(__name__)

_QUERY_TIMEOUT = 8.0


def _clamp_months(months: int, max_months: int = 24) -> int:
    return max(1, min(months, min(max_months, 24)))


async def query_events(
    limit: int = 20,
    offset: int = 0,
    event_type: str | None = None,
    is_active: str | None = None,
    search: str | None = None,
) -> list[dict]:
    """List events for the current client."""
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    sql = """
        SELECT
            event_id,
            event_name,
            event_type,
            goodafter,
            goodtill,
            is_active,
            description,
            create_timestamp,
            last_modified
        FROM on24master.event
        WHERE client_id = ANY($1::bigint[])
          AND ($2::text IS NULL OR event_type = $2)
          AND ($3::text IS NULL OR is_active = $3)
          AND ($4::text IS NULL OR event_name ILIKE '%' || $4 || '%')
        ORDER BY goodafter DESC NULLS LAST
        LIMIT $5 OFFSET $6
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, client_ids, event_type, is_active, search, limit, offset,
                                timeout=_QUERY_TIMEOUT)
    return [dict(row) for row in rows]


async def get_event_detail(event_id: int) -> dict | None:
    """Get a single event — verifies it belongs to the current client."""
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    sql = """
        SELECT *
        FROM on24master.event
        WHERE event_id = $1
          AND client_id = ANY($2::bigint[])
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, event_id, client_ids, timeout=_QUERY_TIMEOUT)
    return dict(row) if row else None


async def query_attendees(
    event_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Get attendees for an event using dw_attendee — verifies client ownership."""
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    sql = """
        SELECT
            da.event_user_id,
            da.engagement_score,
            da.live_minutes,
            da.archive_minutes,
            da.answered_polls,
            da.asked_questions,
            da.resources_downloaded
        FROM on24master.dw_attendee da
        JOIN on24master.event e
          ON da.event_id = e.event_id
         AND e.client_id = ANY($2::bigint[])
        WHERE da.event_id = $1
        ORDER BY da.engagement_score DESC NULLS LAST
        LIMIT $3 OFFSET $4
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, event_id, client_ids, limit, offset,
                                timeout=_QUERY_TIMEOUT)
    return [dict(row) for row in rows]


async def compute_event_kpis(event_id: int) -> dict:
    """Compute KPIs for one event using dw_event_session (pre-aggregated).

    dw_event_session has registrant_count, attendee_count, engagement_score_avg,
    conversion_percent per event session. Aggregate across sessions for the event.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    sql = """
        SELECT
            SUM(des.registrant_count)                    AS total_registrants,
            SUM(des.attendee_count)                      AS total_attendees,
            AVG(des.engagement_score_avg)                AS avg_engagement,
            ROUND(
                SUM(des.attendee_mins)::numeric
                / NULLIF(SUM(des.attendee_count), 0), 1
            )                                            AS avg_live_minutes,
            AVG(des.conversion_percent)                  AS conversion_rate
        FROM on24master.dw_event_session des
        JOIN on24master.event e
          ON des.event_id = e.event_id
         AND e.client_id = ANY($2::bigint[])
        WHERE des.event_id = $1
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, event_id, client_ids, timeout=_QUERY_TIMEOUT)

    if row is None or row["total_registrants"] is None:
        return {
            "event_id": event_id,
            "total_registrants": 0,
            "total_attendees": 0,
            "avg_engagement": None,
            "avg_live_minutes": None,
            "conversion_rate": None,
        }

    result = dict(row)
    result["event_id"] = event_id
    for field in ("avg_engagement", "avg_live_minutes", "conversion_rate"):
        if result.get(field) is not None:
            result[field] = round(float(result[field]), 2)
    return result


async def compute_client_kpis(months: int = 1) -> dict:
    """Compute platform-wide KPIs. Default window: last 1 month. Max: 24 months.

    Uses dw_event_session pre-aggregated counts — avoids event_user scan.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()
    months = _clamp_months(months)

    sql = """
        SELECT
            COUNT(DISTINCT e.event_id)           AS total_events,
            COALESCE(SUM(des.registrant_count), 0) AS total_registrants,
            COALESCE(SUM(des.attendee_count), 0)   AS total_attendees,
            AVG(des.engagement_score_avg)          AS avg_engagement
        FROM on24master.event e
        LEFT JOIN on24master.dw_event_session des
          ON des.event_id = e.event_id
        WHERE e.client_id = ANY($1::bigint[])
          AND e.goodafter >= NOW() - ($2 || ' months')::INTERVAL
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, client_ids, str(months), timeout=_QUERY_TIMEOUT)

    if row is None:
        return {"total_events": 0, "total_registrants": 0, "total_attendees": 0, "avg_engagement": None}

    result = dict(row)
    if result.get("avg_engagement") is not None:
        result["avg_engagement"] = round(float(result["avg_engagement"]), 2)
    return result


async def query_polls(event_id: int) -> list[dict]:
    """Get poll questions and answer distributions for an event.

    Note: question.description holds the question text (not question_text).
    Poll answers are in question_x_answer joined to event_user_x_answer.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    questions_sql = """
        SELECT q.question_id, q.description AS question_text, q.question_type_cd, q.create_timestamp
        FROM on24master.question q
        JOIN on24master.event e
          ON q.event_id = e.event_id
         AND e.client_id = ANY($2::bigint[])
        WHERE q.event_id = $1
          AND q.question_type_cd = 'POLL'
        ORDER BY q.question_id
    """

    answers_sql = """
        SELECT
            qa.question_id,
            qa.answer_id,
            qa.answer_text,
            COUNT(eua.event_user_id) AS response_count
        FROM on24master.question_x_answer qa
        JOIN on24master.question q
          ON qa.question_id = q.question_id
        JOIN on24master.event e
          ON q.event_id = e.event_id
         AND e.client_id = ANY($2::bigint[])
        LEFT JOIN on24master.event_user_x_answer eua
          ON eua.answer_id = qa.answer_id
         AND eua.question_id = qa.question_id
        WHERE q.event_id = $1
          AND q.question_type_cd = 'POLL'
        GROUP BY qa.question_id, qa.answer_id, qa.answer_text
        ORDER BY qa.question_id, qa.answer_id
    """

    async with pool.acquire() as conn:
        q_rows = await conn.fetch(questions_sql, event_id, client_ids, timeout=_QUERY_TIMEOUT)
        a_rows = await conn.fetch(answers_sql, event_id, client_ids, timeout=_QUERY_TIMEOUT)

    answers_by_question: dict[int, list[dict[str, Any]]] = {}
    for a in a_rows:
        qid = a["question_id"]
        answers_by_question.setdefault(qid, []).append({
            "answer_id": a["answer_id"],
            "answer_text": a["answer_text"],
            "response_count": a["response_count"],
        })

    results = []
    for q in q_rows:
        qid = q["question_id"]
        results.append({
            "question_id": qid,
            "question_text": q["question_text"],
            "question_type_cd": q["question_type_cd"],
            "create_timestamp": q["create_timestamp"],
            "answers": answers_by_question.get(qid, []),
        })

    return results


async def query_top_events(
    limit: int = 10,
    sort_by: str = "attendees",
    months: int = 1,
) -> list[dict]:
    """Top events by attendee count or engagement. Default: last 1 month, max 24.

    Uses dw_event_session aggregate columns (attendee_count, engagement_score_avg).
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()
    limit = max(1, min(limit, 50))
    months = _clamp_months(months)

    _sort_map = {
        "attendees": "total_attendees",
        "engagement": "avg_engagement",
    }
    order_col = _sort_map.get(sort_by, "total_attendees")

    sql = f"""
        SELECT
            e.event_id,
            e.event_name,
            e.event_type,
            e.goodafter,
            e.is_active,
            COALESCE(SUM(des.attendee_count), 0)   AS total_attendees,
            AVG(des.engagement_score_avg)           AS avg_engagement
        FROM on24master.event e
        LEFT JOIN on24master.dw_event_session des
          ON des.event_id = e.event_id
        WHERE e.client_id = ANY($1::bigint[])
          AND e.goodafter >= NOW() - ($2 || ' months')::INTERVAL
        GROUP BY e.event_id, e.event_name, e.event_type, e.goodafter, e.is_active
        ORDER BY {order_col} DESC NULLS LAST
        LIMIT $3
    """  # order_col from allow-list above

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, client_ids, str(months), limit, timeout=_QUERY_TIMEOUT)

    results = []
    for row in rows:
        r = dict(row)
        if r.get("avg_engagement") is not None:
            r["avg_engagement"] = round(float(r["avg_engagement"]), 2)
        results.append(r)
    return results


async def query_attendance_trends(months: int = 1) -> list[dict]:
    """Monthly attendance and registration trends. Default: last 1 month, max 24.

    Uses dw_event_session registrant_count / attendee_count per event.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()
    months = _clamp_months(months)

    sql = """
        SELECT
            DATE_TRUNC('month', e.goodafter)             AS period,
            COUNT(DISTINCT e.event_id)                   AS event_count,
            COALESCE(SUM(des.registrant_count), 0)       AS total_registrants,
            COALESCE(SUM(des.attendee_count), 0)         AS total_attendees,
            AVG(des.engagement_score_avg)                AS avg_engagement
        FROM on24master.event e
        LEFT JOIN on24master.dw_event_session des
          ON des.event_id = e.event_id
        WHERE e.client_id = ANY($1::bigint[])
          AND e.goodafter >= NOW() - ($2 || ' months')::INTERVAL
        GROUP BY DATE_TRUNC('month', e.goodafter)
        ORDER BY period ASC
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, client_ids, str(months), timeout=_QUERY_TIMEOUT)

    results = []
    for row in rows:
        r = dict(row)
        if r.get("avg_engagement") is not None:
            r["avg_engagement"] = round(float(r["avg_engagement"]), 2)
        results.append(r)
    return results


async def query_audience_companies(
    limit: int = 20,
    months: int = 1,
) -> list[dict]:
    """Top companies by attendance. Default: last 1 month, max 24.

    Uses dw_attendee (has event_user_id + engagement_score) joined to event_user
    for company name. Date-scoped to limit event_user scan.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()
    months = _clamp_months(months)

    sql = """
        SELECT
            eu.company,
            COUNT(DISTINCT eu.event_id)         AS events_attended,
            COUNT(eu.event_user_id)             AS total_registrants,
            COUNT(da.event_user_id)             AS total_attendees,
            AVG(da.engagement_score)            AS avg_engagement
        FROM on24master.event_user eu
        JOIN on24master.event e
          ON eu.event_id = e.event_id
         AND e.client_id = ANY($1::bigint[])
         AND e.goodafter >= NOW() - ($3 || ' months')::INTERVAL
        LEFT JOIN on24master.dw_attendee da
          ON da.event_user_id = eu.event_user_id
         AND da.event_id = eu.event_id
        WHERE eu.company IS NOT NULL
          AND eu.company <> ''
        GROUP BY eu.company
        ORDER BY total_attendees DESC NULLS LAST
        LIMIT $2
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, client_ids, limit, str(months), timeout=_QUERY_TIMEOUT)

    results = []
    for row in rows:
        r = dict(row)
        if r.get("avg_engagement") is not None:
            r["avg_engagement"] = round(float(r["avg_engagement"]), 2)
        results.append(r)
    return results


async def query_resources(event_id: int, limit: int = 50) -> list[dict]:
    """Resource click/download activity for an event.

    resource_hit_track columns: event_id, event_user_id, resource_id, timestamp, partnerref.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    sql = """
        SELECT
            rht.resource_id,
            rht.event_user_id,
            rht.timestamp        AS hit_timestamp,
            rht.partnerref
        FROM on24master.resource_hit_track rht
        JOIN on24master.event e
          ON rht.event_id = e.event_id
         AND e.client_id = ANY($2::bigint[])
        WHERE rht.event_id = $1
        ORDER BY rht.timestamp DESC NULLS LAST
        LIMIT $3
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, event_id, client_ids, limit, timeout=_QUERY_TIMEOUT)
    return [dict(row) for row in rows]
