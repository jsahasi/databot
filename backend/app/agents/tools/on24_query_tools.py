"""Query tools that read directly from the ON24 master PostgreSQL database.

SECURITY: Every function calls get_tenant_client_ids() internally to scope all
queries to the current tenant (including sub-clients). client_id is NEVER
accepted as a function parameter.
All queries use parameterised $N placeholders — never string interpolation.
"""

import logging
from typing import Any

from app.db.on24_db import get_pool, get_tenant_client_ids

logger = logging.getLogger(__name__)


async def query_events(
    limit: int = 20,
    offset: int = 0,
    event_type: str | None = None,
    is_active: str | None = None,  # 'Y' or 'N'
    search: str | None = None,     # searches event_name with ILIKE
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
        rows = await conn.fetch(sql, client_ids, event_type, is_active, search, limit, offset)
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
        row = await conn.fetchrow(sql, event_id, client_ids)
    return dict(row) if row else None


async def query_attendees(
    event_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Get attendees for an event — verifies the event belongs to the current client."""
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    sql = """
        SELECT
            eu.event_user_id,
            eu.firstname,
            eu.lastname,
            eu.email,
            eu.company,
            eu.job_title,
            eu.country,
            eu.utm_source,
            eu.create_timestamp,
            da.engagement_score,
            da.live_minutes,
            da.archive_minutes
        FROM on24master.event_user eu
        JOIN on24master.event e
          ON eu.event_id = e.event_id
        LEFT JOIN on24master.dw_attendee da
          ON da.event_user_id = eu.event_user_id
         AND da.event_id = eu.event_id
        WHERE eu.event_id = $1
          AND e.client_id = ANY($2::bigint[])
        LIMIT $3 OFFSET $4
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, event_id, client_ids, limit, offset)
    return [dict(row) for row in rows]


async def compute_event_kpis(event_id: int) -> dict:
    """Compute KPIs for one event — verifies client ownership.

    Uses dw_event_session (pre-aggregated) for attendee metrics to avoid
    scanning event_user (585M rows). Registrant count from event table directly.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    sql = """
        SELECT
            e.num_registered                                                      AS total_registrants,
            COUNT(des.event_user_id)                                              AS total_attendees,
            AVG(des.engagement_score)                                             AS avg_engagement,
            AVG(des.live_duration)                                                AS avg_live_minutes,
            COUNT(des.event_user_id)::float
              / NULLIF(e.num_registered, 0) * 100                                 AS conversion_rate
        FROM on24master.event e
        LEFT JOIN on24master.dw_event_session des
          ON des.event_id = e.event_id
        WHERE e.event_id = $1
          AND e.client_id = ANY($2::bigint[])
        GROUP BY e.num_registered
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, event_id, client_ids)

    if row is None:
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


async def compute_client_kpis() -> dict:
    """Compute platform-wide KPIs across all events for the current client.

    Uses dw_event_session (pre-aggregated per attendee session) joined to
    event for client scoping — avoids the 585M-row event_user table entirely.
    Registrant totals summed from event.num_registered.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    sql = """
        SELECT
            COUNT(DISTINCT e.event_id)       AS total_events,
            COALESCE(SUM(e.num_registered), 0) AS total_registrants,
            COUNT(des.event_user_id)         AS total_attendees,
            AVG(des.engagement_score)        AS avg_engagement
        FROM on24master.event e
        LEFT JOIN on24master.dw_event_session des
          ON des.event_id = e.event_id
        WHERE e.client_id = ANY($1::bigint[])
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, client_ids)

    if row is None:
        return {
            "total_events": 0,
            "total_registrants": 0,
            "total_attendees": 0,
            "avg_engagement": None,
        }

    result = dict(row)
    if result.get("avg_engagement") is not None:
        result["avg_engagement"] = round(float(result["avg_engagement"]), 2)
    return result


async def query_polls(event_id: int) -> list[dict]:
    """Get poll questions and answer distributions for an event."""
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    # Fetch poll questions, verifying client ownership via the event join
    questions_sql = """
        SELECT q.question_id, q.question_text, q.question_type_cd, q.create_timestamp
        FROM on24master.question q
        JOIN on24master.event e
          ON q.event_id = e.event_id
         AND e.client_id = ANY($2::bigint[])
        WHERE q.event_id = $1
          AND q.question_type_cd = 'POLL'
        ORDER BY q.question_id
    """

    # Fetch answers for those poll questions
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
        q_rows = await conn.fetch(questions_sql, event_id, client_ids)
        a_rows = await conn.fetch(answers_sql, event_id, client_ids)

    # Group answers by question_id
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
    sort_by: str = "attendees",  # "attendees" | "engagement"
    months: int = 24,
) -> list[dict]:
    """Top events for the current client by chosen metric (recent events only).

    Uses dw_event_session (pre-aggregated per attendee session) — avoids
    scanning event_user (585M rows). Scopes to last `months` months.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()
    limit = max(1, min(limit, 50))
    months = max(1, min(months, 60))

    _sort_map = {
        "attendees": "total_attendees",
        "engagement": "avg_engagement",
    }
    order_col = _sort_map.get(sort_by, "total_attendees")

    # Aggregate dw_event_session scoped to client + date window — no event_user scan
    sql = f"""
        SELECT
            e.event_id,
            e.event_name,
            e.event_type,
            e.goodafter,
            e.is_active,
            COALESCE(agg.total_attendees, 0) AS total_attendees,
            agg.avg_engagement
        FROM on24master.event e
        LEFT JOIN (
            SELECT
                event_id,
                COUNT(*)              AS total_attendees,
                AVG(engagement_score) AS avg_engagement
            FROM on24master.dw_event_session
            WHERE event_id = ANY(
                SELECT event_id FROM on24master.event
                WHERE client_id = ANY($1::bigint[])
                  AND goodafter >= NOW() - ($2 || ' months')::INTERVAL
            )
            GROUP BY event_id
        ) agg ON agg.event_id = e.event_id
        WHERE e.client_id = ANY($1::bigint[])
          AND e.goodafter >= NOW() - ($2 || ' months')::INTERVAL
        ORDER BY {order_col} DESC NULLS LAST
        LIMIT $3
    """  # order_col comes from allow-list above

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, client_ids, str(months), limit)

    results = []
    for row in rows:
        r = dict(row)
        if r.get("avg_engagement") is not None:
            r["avg_engagement"] = round(float(r["avg_engagement"]), 2)
        results.append(r)
    return results


async def query_attendance_trends(months: int = 12) -> list[dict]:
    """Monthly attendance and registration trends for the current client.

    Uses dw_event_session for attendee counts and event.num_registered for
    registration totals — avoids the 585M-row event_user table.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    months = max(1, min(months, 120))

    sql = """
        SELECT
            DATE_TRUNC('month', e.goodafter)       AS period,
            COUNT(DISTINCT e.event_id)              AS event_count,
            COALESCE(SUM(e.num_registered), 0)      AS total_registrants,
            COUNT(des.event_user_id)                AS total_attendees,
            AVG(des.engagement_score)               AS avg_engagement
        FROM on24master.event e
        LEFT JOIN on24master.dw_event_session des
          ON des.event_id = e.event_id
        WHERE e.client_id = ANY($1::bigint[])
          AND e.goodafter >= NOW() - ($2 || ' months')::INTERVAL
        GROUP BY DATE_TRUNC('month', e.goodafter)
        ORDER BY period ASC
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, client_ids, str(months))

    results = []
    for row in rows:
        r = dict(row)
        if r.get("avg_engagement") is not None:
            r["avg_engagement"] = round(float(r["avg_engagement"]), 2)
        results.append(r)
    return results


async def query_audience_companies(
    limit: int = 20,
    months: int = 24,
) -> list[dict]:
    """Top companies attending the current client's events (cross-event).

    Scoped to last `months` months and uses dw_event_session for attendee
    metrics — reduces event_user scan from all-time to a manageable window.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()
    months = max(1, min(months, 60))

    sql = """
        SELECT
            eu.company,
            COUNT(DISTINCT eu.event_id)         AS events_attended,
            COUNT(eu.event_user_id)             AS total_registrants,
            COUNT(des.event_user_id)            AS total_attendees,
            AVG(des.engagement_score)           AS avg_engagement
        FROM on24master.event_user eu
        JOIN on24master.event e
          ON eu.event_id = e.event_id
         AND e.client_id = ANY($1::bigint[])
         AND e.goodafter >= NOW() - ($3 || ' months')::INTERVAL
        LEFT JOIN on24master.dw_event_session des
          ON des.event_user_id = eu.event_user_id
         AND des.event_id = eu.event_id
        WHERE eu.company IS NOT NULL
          AND eu.company <> ''
        GROUP BY eu.company
        ORDER BY total_attendees DESC NULLS LAST
        LIMIT $2
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, client_ids, limit, str(months))

    results = []
    for row in rows:
        r = dict(row)
        if r.get("avg_engagement") is not None:
            r["avg_engagement"] = round(float(r["avg_engagement"]), 2)
        results.append(r)
    return results


async def query_resources(event_id: int, limit: int = 50) -> list[dict]:
    """Resource download activity for an event — verifies client ownership."""
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    sql = """
        SELECT
            rht.resource_hit_track_id,
            rht.resource_id,
            rht.resource_name,
            rht.event_user_id,
            rht.hit_timestamp,
            rht.resource_type
        FROM on24master.resource_hit_track rht
        JOIN on24master.event e
          ON rht.event_id = e.event_id
         AND e.client_id = ANY($2::bigint[])
        WHERE rht.event_id = $1
        ORDER BY rht.hit_timestamp DESC NULLS LAST
        LIMIT $3
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, event_id, client_ids, limit)
    return [dict(row) for row in rows]
