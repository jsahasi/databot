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
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.db.on24_db import get_pool, get_tenant_client_ids


def _serialize(obj: Any) -> Any:
    """Recursively convert asyncpg/Decimal/datetime types to JSON-safe primitives."""
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return obj

logger = logging.getLogger(__name__)

_QUERY_TIMEOUT = 8.0

# Data quality filters applied globally to all event-returning queries.
# Excludes: (1) test/staging events — description contains "test" (case-insensitive)
#           (2) low-signal events — 5 or fewer registrants
# These are hardcoded SQL fragments (no user input) so f-string inclusion is safe.
_EXCL_TEST = "AND e.description NOT ILIKE '%test%'"
_MIN_REGS_SUBQ = """
    AND COALESCE((
        SELECT SUM(r.registrant_count)
        FROM on24master.dw_event_session r
        WHERE r.event_id = e.event_id
    ), 0) > 5"""


def _clamp_months(months: int, max_months: int = 24) -> int:
    return max(1, min(months, min(max_months, 24)))


async def query_events(
    limit: int = 20,
    offset: int = 0,
    event_type: str | None = None,
    is_active: str | None = None,
    search: str | None = None,
    past_only: bool = False,  # True to restrict to events with goodafter <= NOW()
) -> list[dict]:
    """List events for the current client.

    Set past_only=True when the user asks for 'last event' or 'most recent event'
    to exclude future-dated events.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    sql = f"""
        SELECT
            event_id,
            description,
            event_type,
            goodafter,
            goodtill,
            is_active,
            create_timestamp,
            last_modified
        FROM on24master.event e
        WHERE e.client_id = ANY($1::bigint[])
          AND ($2::text IS NULL OR e.event_type = $2)
          AND ($3::text IS NULL OR e.is_active = $3)
          AND ($4::text IS NULL OR e.description ILIKE '%' || $4 || '%')
          AND ($5 = false OR e.goodafter <= NOW())
          {_EXCL_TEST}
          {_MIN_REGS_SUBQ}
        ORDER BY e.goodafter DESC NULLS LAST
        LIMIT $6 OFFSET $7
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, client_ids, event_type, is_active, search, past_only, limit, offset,
                                timeout=_QUERY_TIMEOUT)
    return [_serialize(dict(row)) for row in rows]


async def get_event_detail(event_id: int) -> dict | None:
    """Get a single event — verifies it belongs to the current client."""
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    sql = f"""
        SELECT *
        FROM on24master.event e
        WHERE e.event_id = $1
          AND e.client_id = ANY($2::bigint[])
          {_EXCL_TEST}
          {_MIN_REGS_SUBQ}
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, event_id, client_ids, timeout=_QUERY_TIMEOUT)
    return _serialize(dict(row)) if row else None


async def query_attendees(
    event_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Get attendees for an event using dw_attendee — verifies client ownership."""
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    sql = f"""
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
          {_EXCL_TEST}
        ORDER BY da.engagement_score DESC NULLS LAST
        LIMIT $3 OFFSET $4
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, event_id, client_ids, limit, offset,
                                timeout=_QUERY_TIMEOUT)
    return [_serialize(dict(row)) for row in rows]


async def compute_event_kpis(event_id: int) -> dict:
    """Compute KPIs for one event using dw_event_session (pre-aggregated).

    dw_event_session has registrant_count, attendee_count, engagement_score_avg,
    conversion_percent per event session. Aggregate across sessions for the event.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    sql = f"""
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
          {_EXCL_TEST}
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

    sql = f"""
        SELECT
            COUNT(DISTINCT e.event_id)             AS total_events,
            COALESCE(SUM(des.registrant_count), 0) AS total_registrants,
            COALESCE(SUM(des.attendee_count), 0)   AS total_attendees,
            AVG(des.engagement_score_avg)          AS avg_engagement
        FROM on24master.event e
        LEFT JOIN on24master.dw_event_session des
          ON des.event_id = e.event_id
        WHERE e.client_id = ANY($1::bigint[])
          AND e.goodafter >= NOW() - ($2 || ' months')::INTERVAL
          AND e.goodafter <= NOW()
          {_EXCL_TEST}
          {_MIN_REGS_SUBQ}
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

    Uses the correct join chain:
      event_x_media_url (EXMU) → media_url (MU) → media_url_x_question (MUQ)
      → question (Q) → question_x_answer (QA) → event_user_x_answer (EUA)
      → event_user (EU) → event (E) for tenant scoping

    Deduplicates re-submissions via COUNT DISTINCT event_user_id.
    EXMU.SESSION_ID = 1 scopes to the live event session.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    # Multiple-choice / rated questions: aggregate answer option counts
    mc_sql = """
        SELECT
            MU.MEDIA_URL_ID                           AS poll_id,
            Q.QUESTION_ID                             AS question_id,
            Q.DESCRIPTION                             AS question_text,
            Q.QUESTION_TYPE_CD                        AS question_type_cd,
            QA.ANSWER_CD                              AS answer_cd,
            QA.DESCRIPTION                            AS answer_text,
            COUNT(DISTINCT EUA.EVENT_USER_ID)         AS response_count
        FROM on24master.event_x_media_url EXMU
        JOIN on24master.media_url MU
          ON MU.MEDIA_URL_ID = EXMU.MEDIA_URL_ID
        JOIN on24master.media_url_x_question MUQ
          ON MUQ.MEDIA_URL_ID = MU.MEDIA_URL_ID
        JOIN on24master.question Q
          ON Q.QUESTION_ID = MUQ.QUESTION_ID
        JOIN on24master.question_x_answer QA
          ON QA.QUESTION_ID = Q.QUESTION_ID
        JOIN on24master.event_user_x_answer EUA
          ON EUA.MEDIA_URL_ID = EXMU.MEDIA_URL_ID
         AND EUA.QUESTION_ID  = QA.QUESTION_ID
         AND (EUA.ANSWER_CD = QA.ANSWER_CD OR Q.QUESTION_TYPE_CD = 'npsrating')
        JOIN on24master.event_user EU
          ON EU.EVENT_USER_ID = EUA.EVENT_USER_ID
        JOIN on24master.event E
          ON E.EVENT_ID = EU.EVENT_ID
         AND E.CLIENT_ID = ANY($2::bigint[])
        WHERE EU.EVENT_ID = $1
          AND EXMU.SESSION_ID = 1
          AND MU.MEDIA_URL_CD = 'poll'
          AND MU.MEDIA_URL_NAME NOT LIKE '%<!--##test##-->%'
          AND MU.MEDIA_URL_NAME NOT LIKE '%<!--##survey##-->%'
        GROUP BY MU.MEDIA_URL_ID, Q.QUESTION_ID, Q.DESCRIPTION,
                 Q.QUESTION_TYPE_CD, QA.ANSWER_CD, QA.DESCRIPTION
        ORDER BY Q.QUESTION_ID, response_count DESC
    """

    # Open-text questions (singletext): return respondent count + up to 5 sample answers
    text_sql = """
        SELECT
            Q.QUESTION_ID                             AS question_id,
            Q.DESCRIPTION                             AS question_text,
            Q.QUESTION_TYPE_CD                        AS question_type_cd,
            COUNT(DISTINCT EUA.EVENT_USER_ID)         AS response_count,
            ARRAY_AGG(DISTINCT EUA.ANSWER ORDER BY EUA.ANSWER)[1:5] AS sample_answers
        FROM on24master.event_x_media_url EXMU
        JOIN on24master.media_url MU
          ON MU.MEDIA_URL_ID = EXMU.MEDIA_URL_ID
        JOIN on24master.media_url_x_question MUQ
          ON MUQ.MEDIA_URL_ID = MU.MEDIA_URL_ID
        JOIN on24master.question Q
          ON Q.QUESTION_ID = MUQ.QUESTION_ID
        JOIN on24master.event_user_x_answer EUA
          ON EUA.MEDIA_URL_ID = EXMU.MEDIA_URL_ID
         AND EUA.QUESTION_ID  = Q.QUESTION_ID
         AND EUA.ANSWER IS NOT NULL
         AND TRIM(EUA.ANSWER) <> ''
        JOIN on24master.event_user EU
          ON EU.EVENT_USER_ID = EUA.EVENT_USER_ID
        JOIN on24master.event E
          ON E.EVENT_ID = EU.EVENT_ID
         AND E.CLIENT_ID = ANY($2::bigint[])
        WHERE EU.EVENT_ID = $1
          AND EXMU.SESSION_ID = 1
          AND MU.MEDIA_URL_CD = 'poll'
          AND MU.MEDIA_URL_NAME NOT LIKE '%<!--##test##-->%'
          AND MU.MEDIA_URL_NAME NOT LIKE '%<!--##survey##-->%'
          AND Q.QUESTION_TYPE_CD IN ('singletext', 'singleanswer')
        GROUP BY Q.QUESTION_ID, Q.DESCRIPTION, Q.QUESTION_TYPE_CD
        ORDER BY Q.QUESTION_ID
    """

    async with pool.acquire() as conn:
        mc_rows = await conn.fetch(mc_sql, event_id, client_ids, timeout=_QUERY_TIMEOUT)
        text_rows = await conn.fetch(text_sql, event_id, client_ids, timeout=_QUERY_TIMEOUT)

    # Group multiple-choice answers by question_id
    questions: dict[int, dict] = {}
    for r in mc_rows:
        qid = r["question_id"]
        if qid not in questions:
            questions[qid] = {
                "question_id": qid,
                "question_text": r["question_text"],
                "question_type_cd": r["question_type_cd"],
                "answers": [],
            }
        questions[qid]["answers"].append({
            "answer_cd": r["answer_cd"],
            "answer_text": r["answer_text"],
            "response_count": int(r["response_count"]),
        })

    # Open-text questions
    for r in text_rows:
        qid = r["question_id"]
        questions[qid] = {
            "question_id": qid,
            "question_text": r["question_text"],
            "question_type_cd": r["question_type_cd"],
            "response_count": int(r["response_count"]),
            "sample_answers": list(r["sample_answers"] or []),
        }

    return _serialize(list(questions.values()))


async def query_top_events_by_polls(limit: int = 10) -> list[dict]:
    """Top events ranked by number of poll questions asked."""
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()
    limit = max(1, min(limit, 50))

    sql = f"""
        SELECT
            e.event_id,
            e.description,
            e.goodafter,
            COUNT(DISTINCT q.question_id) AS poll_count
        FROM on24master.event e
        JOIN on24master.question q
          ON q.event_id = e.event_id
         AND q.question_type_cd IN ('singleoption', 'multioption')
        WHERE e.client_id = ANY($1::bigint[])
          {_EXCL_TEST}
        GROUP BY e.event_id, e.description, e.goodafter
        ORDER BY poll_count DESC NULLS LAST
        LIMIT $2
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, client_ids, limit, timeout=_QUERY_TIMEOUT)
    return [_serialize(dict(row)) for row in rows]


async def query_poll_overview(months: int = 24) -> list[dict]:
    """Cross-event poll summary: events with polls, question count, and total responses.

    Scoped to past N months. Sorted by total responses descending.
    Avoids correlated subquery on large tables by using a date filter.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()
    months = _clamp_months(months)

    sql = f"""
        SELECT
            e.event_id,
            e.description,
            e.goodafter,
            COUNT(DISTINCT q.question_id)    AS poll_count,
            COUNT(eua.event_user_id)         AS total_responses
        FROM on24master.event e
        JOIN on24master.question q
          ON q.event_id = e.event_id
         AND q.question_type_cd IN ('singleoption', 'multioption')
        LEFT JOIN on24master.event_user_x_answer eua
          ON eua.question_id = q.question_id
        WHERE e.client_id = ANY($1::bigint[])
          AND e.goodafter >= NOW() - ($2 || ' months')::INTERVAL
          AND e.goodafter <= NOW()
          {_EXCL_TEST}
        GROUP BY e.event_id, e.description, e.goodafter
        HAVING COUNT(DISTINCT q.question_id) > 0
        ORDER BY total_responses DESC NULLS LAST
        LIMIT 20
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, client_ids, str(months), timeout=_QUERY_TIMEOUT)
    return [_serialize(dict(row)) for row in rows]


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
    # Hard assert: order_col must be one of the two known safe column aliases.
    assert order_col in ("total_attendees", "avg_engagement"), f"Unexpected order_col: {order_col}"

    sql = f"""
        SELECT
            e.event_id,
            e.description,
            e.event_type,
            e.goodafter,
            e.is_active,
            COALESCE(SUM(des.attendee_count), 0)   AS total_attendees,
            COALESCE(SUM(des.registrant_count), 0) AS total_registrants,
            AVG(des.engagement_score_avg)           AS avg_engagement
        FROM on24master.event e
        LEFT JOIN on24master.dw_event_session des
          ON des.event_id = e.event_id
        WHERE e.client_id = ANY($1::bigint[])
          AND e.goodafter >= NOW() - ($2 || ' months')::INTERVAL
          AND e.goodafter <= NOW()
          {_EXCL_TEST}
        GROUP BY e.event_id, e.description, e.event_type, e.goodafter, e.is_active
        HAVING COALESCE(SUM(des.registrant_count), 0) > 5
        ORDER BY {order_col} DESC NULLS LAST
        LIMIT $3
    """  # order_col sourced from allowlist + asserted above

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, client_ids, str(months), limit, timeout=_QUERY_TIMEOUT)

    results = []
    for row in rows:
        r = dict(row)
        if r.get("avg_engagement") is not None:
            r["avg_engagement"] = round(float(r["avg_engagement"]), 2)
        results.append(_serialize(r))
    return results


async def query_attendance_trends(months: int = 12) -> list[dict]:
    """Monthly attendance and registration trends. Default: last 12 months, max 24.

    Uses dw_event_session registrant_count / attendee_count per event.
    Only includes events that pass the test-exclusion and min-registrant filters.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()
    months = _clamp_months(months)

    sql = f"""
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
          AND e.goodafter <= NOW()
          {_EXCL_TEST}
          {_MIN_REGS_SUBQ}
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
        results.append(_serialize(r))
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

    sql = f"""
        SELECT
            MODE() WITHIN GROUP (ORDER BY eu.company) AS company,
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
          {_EXCL_TEST}
          {_MIN_REGS_SUBQ}
        GROUP BY LOWER(TRIM(eu.company))
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
        results.append(_serialize(r))
    return results


async def query_audience_sources(
    event_id: int | None = None,
    limit: int = 20,
) -> list[dict]:
    """Audience traffic sources via partnerref on event_user.

    partnerref is a URL parameter embedded in the registration link that identifies
    the campaign or source site that drove the registrant.

    If event_id is given, scopes to that event. Otherwise returns sources across
    all client events. Returns empty list if no partnerref data exists.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    if event_id is not None:
        sql = f"""
            SELECT
                eu.partnerref       AS source,
                COUNT(eu.event_user_id)             AS registrant_count,
                COUNT(da.event_user_id)             AS attendee_count
            FROM on24master.event_user eu
            JOIN on24master.event e
              ON eu.event_id = e.event_id
             AND e.client_id = ANY($1::bigint[])
             AND e.event_id = $3
            LEFT JOIN on24master.dw_attendee da
              ON da.event_user_id = eu.event_user_id
             AND da.event_id = eu.event_id
            WHERE eu.partnerref IS NOT NULL
              AND TRIM(eu.partnerref) <> ''
            GROUP BY eu.partnerref
            ORDER BY registrant_count DESC
            LIMIT $2
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, client_ids, limit, event_id, timeout=_QUERY_TIMEOUT)
    else:
        sql = f"""
            SELECT
                eu.partnerref       AS source,
                COUNT(eu.event_user_id)             AS registrant_count,
                COUNT(da.event_user_id)             AS attendee_count
            FROM on24master.event_user eu
            JOIN on24master.event e
              ON eu.event_id = e.event_id
             AND e.client_id = ANY($1::bigint[])
            LEFT JOIN on24master.dw_attendee da
              ON da.event_user_id = eu.event_user_id
             AND da.event_id = eu.event_id
            WHERE eu.partnerref IS NOT NULL
              AND TRIM(eu.partnerref) <> ''
            GROUP BY eu.partnerref
            ORDER BY registrant_count DESC
            LIMIT $2
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, client_ids, limit, timeout=_QUERY_TIMEOUT)

    return [_serialize(dict(row)) for row in rows]


async def query_resources(event_id: int, limit: int = 50) -> list[dict]:
    """Resource download activity for an event, grouped by resource name.

    Uses content_hit_track_details (action='TotalHits') scoped to resources that
    appear in the event's resource-list widget (display_element_value_cd='resourcelist')
    or are PDF portal resources (video_library).
    Returns per-resource download counts (COUNT DISTINCT event_user_id for dedup).
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()
    limit = max(1, min(limit, 100))

    sql = """
        SELECT
            ct.content_name                           AS resource_name,
            COUNT(DISTINCT ct.event_user_id)          AS downloader_count,
            COUNT(*)                                  AS total_hits
        FROM on24master.content_hit_track_details ct
        JOIN on24master.event e
          ON e.event_id = ct.event_id
         AND e.client_id = ANY($2::bigint[])
        WHERE ct.event_id = $1
          AND ct.action = 'TotalHits'
          AND COALESCE(ct.media_url_id, 0) != 0
          AND COALESCE(ct.media_category_cd, 'xxx') NOT LIKE 'custom_icon%'
          AND ct.event_user_id != 305999
          AND (
            -- Resource is in a valid (not deleted) resource-list widget for this event
            EXISTS (
                SELECT 1
                FROM on24master.display_profile_x_event dpxe
                JOIN on24master.display_profile dp
                  ON dp.display_profile_id = dpxe.display_profile_id
                JOIN on24master.display_element de
                  ON de.display_element_id = dp.display_element_id
                WHERE dpxe.event_id = ct.event_id
                  AND dpxe.display_type_cd = 'player'
                  AND de.display_element_value_cd = 'resourcelist'
                  AND de.display_element_value ~ '<param name="persistenceStatus" type="String">PersistenceStatusSaveComplete</param>'
                  AND de.display_element_value !~ '<param name="persistenceState" type="String">PersistenceStateDelete</param>'
                  AND dp.display_element_id = ct.display_element_id
            )
            OR
            -- Resource is a PDF in the portal video library
            EXISTS (
                SELECT 1
                FROM on24master.video_library vl
                WHERE vl.portal_event_id = ct.event_id
                  AND vl.type = 'pdf'
            )
          )
        GROUP BY ct.content_name
        ORDER BY downloader_count DESC
        LIMIT $3
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, event_id, client_ids, limit, timeout=_QUERY_TIMEOUT)
    return [_serialize(dict(row)) for row in rows]


async def generate_chart_data(
    data: list[dict],
    chart_type: str = "bar",
    x_key: str = "",
    y_keys: list[str] | None = None,
    title: str = "",
    y_label: str = "",
) -> dict:
    """Format tool result data for the frontend chart renderer.

    Pass the raw list returned by a previous tool (get_attendance_trends,
    get_top_events, etc.), specify x_key (the label field) and optionally
    y_keys (the metric fields to plot). Returns a chart payload.

    chart_type: 'bar' or 'line'
    x_key: field to use as x-axis label (e.g. 'period', 'description')
    y_keys: fields to plot as series (defaults to all non-x_key numeric fields)
    title: chart title shown above the chart
    y_label: optional y-axis label
    """
    if not data:
        return {}

    if not x_key and data:
        x_key = list(data[0].keys())[0]

    if not y_keys:
        sample = data[0]
        y_keys = [k for k, v in sample.items() if k != x_key and isinstance(v, (int, float))]

    # Pie charts use {name, value} pairs — first y_key only
    if chart_type == "pie":
        chart_rows = [
            {"name": str(row.get(x_key, "")), "value": row.get(y_keys[0], 0)}
            for row in data
            if row.get(y_keys[0]) is not None
        ]
        return {"type": "pie", "data": chart_rows, "title": title}

    chart_rows = []
    for row in data:
        point: dict[str, Any] = {x_key: row.get(x_key, "")}
        for k in y_keys:
            point[k] = row.get(k)
        chart_rows.append(point)

    result: dict[str, Any] = {
        "type": chart_type if chart_type in ("bar", "line") else "bar",
        "data": chart_rows,
        "title": title,
    }
    if y_label:
        result["yLabel"] = y_label
    return result
