"""Direct-DB analytics query functions for the ON24 MCP server.

Maps to the 8 analytics tools exposed via MCP:
  list_events, get_event_detail, get_event_kpis, get_top_events,
  get_attendance_trends, get_audience_companies, get_polls, get_ai_content

All query functions:
- Call get_tenant_client_ids() internally — client_id is never a parameter.
- Use parameterized $N placeholders — never string interpolation for user data.
- Apply 8-second per-query timeout.
- Default date window: 1 month.  Max: 24 months.

Column facts (verified against on24master schema):
- event.goodafter = start time, event.goodtill = end time, event.description = title
- dw_event_session: registrant_count, attendee_count, engagement_score_avg, attendee_mins
- dw_attendee: per-attendee; has event_user_id, engagement_score, live_minutes
- question.description = poll text; question_type_cd = 'POLL'/'SURVEY'/'QA'
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from db import get_pool, get_tenant_client_ids

logger = logging.getLogger(__name__)

_QUERY_TIMEOUT = 8.0

# Data quality filters: exclude test events and low-signal events (<= 5 registrants).
# These are hardcoded SQL fragments (no user input) — safe to include in f-strings.
_EXCL_TEST = "AND e.description NOT ILIKE '%test%'"
_MIN_REGS_SUBQ = """
    AND COALESCE((
        SELECT SUM(r.registrant_count)
        FROM on24master.dw_event_session r
        WHERE r.event_id = e.event_id
    ), 0) > 5"""

_AI_CONTENT_TYPES = {
    "BLOG": "AUTOGEN_BLOG",
    "EBOOK": "AUTOGEN_EBOOK",
    "FAQ": "AUTOGEN_FAQ",
    "FAQS": "AUTOGEN_FAQ",
    "KEYTAKEAWAYS": "AUTOGEN_KEYTAKEAWAYS",
    "KEY TAKEAWAYS": "AUTOGEN_KEYTAKEAWAYS",
    "FOLLOWUPEMAIL": "AUTOGEN_FOLLOWUPEMAIL",
    "FOLLOW UP EMAIL": "AUTOGEN_FOLLOWUPEMAIL",
    "SOCIALMEDIA": "AUTOGEN_SOCIALMEDIA",
    "SOCIAL MEDIA": "AUTOGEN_SOCIALMEDIA",
    "TRANSCRIPT": "AUTOGEN_TRANSCRIPT",
}


def _clamp_months(months: int, max_months: int = 24) -> int:
    return max(1, min(months, max_months))


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


async def list_events(
    limit: int = 20,
    offset: int = 0,
    event_type: Optional[str] = None,
    is_active: Optional[str] = None,
    search: Optional[str] = None,
    past_only: bool = False,
    months: Optional[int] = None,
) -> list[dict]:
    """List events for the current tenant.

    Args:
        limit: Max results (1-100).
        offset: Pagination offset.
        event_type: Filter by event type (e.g. 'WEBINAR').
        is_active: Filter by is_active flag ('Y'/'N').
        search: Search in event title/description (ILIKE).
        past_only: If True, only return events that have already started.
        months: If set, only return events within last N months (max 24).
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    date_clause = ""
    params: list = [client_ids, event_type, is_active, search, past_only]
    if months is not None:
        m = _clamp_months(months)
        date_clause = f"AND e.goodafter >= NOW() - ('{m} months')::INTERVAL"

    sql = f"""
        SELECT
            e.event_id,
            e.description,
            e.event_type,
            e.goodafter,
            e.goodtill,
            e.is_active,
            e.create_timestamp,
            e.last_modified
        FROM on24master.event e
        WHERE e.client_id = ANY($1::bigint[])
          AND ($2::text IS NULL OR e.event_type = $2)
          AND ($3::text IS NULL OR e.is_active = $3)
          AND ($4::text IS NULL OR e.description ILIKE '%' || $4 || '%')
          AND ($5 = false OR e.goodafter <= NOW())
          {date_clause}
          {_EXCL_TEST}
          {_MIN_REGS_SUBQ}
        ORDER BY e.goodafter DESC NULLS LAST
        LIMIT $6 OFFSET $7
    """
    params.extend([limit, offset])

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params, timeout=_QUERY_TIMEOUT)
    return [_serialize(dict(row)) for row in rows]


async def get_event_detail(event_id: int) -> Optional[dict]:
    """Get full detail for a single event — verifies it belongs to the current tenant."""
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    sql = f"""
        SELECT *
        FROM on24master.event e
        WHERE e.event_id = $1
          AND e.client_id = ANY($2::bigint[])
          {_EXCL_TEST}
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, event_id, client_ids, timeout=_QUERY_TIMEOUT)
    return _serialize(dict(row)) if row else None


async def get_event_kpis(event_id: int) -> dict:
    """Compute KPIs for one event using dw_event_session (pre-aggregated).

    Returns: total_registrants, total_attendees, avg_engagement,
             avg_live_minutes, conversion_rate, ai_content (if any).
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

    # Check for AI-ACE generated content
    ai_sql = """
        SELECT COUNT(*) AS cnt
        FROM on24master.video_library vl
        WHERE vl.source_event_id = $1
          AND vl.source LIKE 'AUTO%'
          AND vl.client_id = ANY($2::bigint[])
    """
    async with pool.acquire() as conn:
        ai_row = await conn.fetchrow(ai_sql, event_id, client_ids, timeout=_QUERY_TIMEOUT)
    ai_count = int(ai_row["cnt"]) if ai_row else 0
    if ai_count > 0:
        result["ai_content"] = {"count": ai_count}

    return _serialize(result)


async def get_top_events(
    limit: int = 10,
    sort_by: str = "attendees",
    months: int = 1,
) -> list[dict]:
    """Top events by attendee count or engagement score.

    Args:
        limit: Max results (1-50).
        sort_by: 'attendees' or 'engagement'.
        months: Look-back window in months (default 1, max 24).

    Returns list of events with total_attendees, total_registrants, avg_engagement.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()
    limit = max(1, min(limit, 50))
    months = _clamp_months(months)

    _sort_map = {"attendees": "total_attendees", "engagement": "avg_engagement"}
    order_col = _sort_map.get(sort_by, "total_attendees")
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
    """  # order_col from allowlist + asserted above

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, client_ids, str(months), limit, timeout=_QUERY_TIMEOUT)

    results = []
    for row in rows:
        r = dict(row)
        if r.get("avg_engagement") is not None:
            r["avg_engagement"] = round(float(r["avg_engagement"]), 2)
        results.append(_serialize(r))
    return results


async def get_attendance_trends(months: int = 12) -> list[dict]:
    """Monthly attendance and registration trends.

    Args:
        months: Look-back window in months (default 12, max 24).

    Returns list of monthly periods with event_count, total_registrants,
    total_attendees, avg_engagement.
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


async def get_audience_companies(
    limit: int = 20,
    months: int = 1,
    event_id: Optional[int] = None,
) -> list[dict]:
    """Top companies by attendance count.

    Args:
        limit: Max companies to return (1-100).
        months: Look-back window in months (ignored when event_id is set).
        event_id: If provided, scope to a single event.

    Returns list of companies with attendee_count, avg_engagement, event_count.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()
    limit = max(1, min(limit, 100))
    months = _clamp_months(months)

    if event_id is not None:
        sql = f"""
            SELECT
                eu.company,
                COUNT(DISTINCT da.event_user_id)  AS attendee_count,
                AVG(da.engagement_score)           AS avg_engagement,
                1                                 AS event_count
            FROM on24master.dw_attendee da
            JOIN on24master.event_user eu
              ON eu.event_user_id = da.event_user_id
            JOIN on24master.event e
              ON e.event_id = da.event_id
             AND e.client_id = ANY($2::bigint[])
            WHERE da.event_id = $1
              AND eu.company IS NOT NULL
              AND TRIM(eu.company) <> ''
              {_EXCL_TEST}
            GROUP BY eu.company
            ORDER BY attendee_count DESC NULLS LAST
            LIMIT $3
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, event_id, client_ids, limit, timeout=_QUERY_TIMEOUT)
    else:
        sql = f"""
            SELECT
                eu.company,
                COUNT(DISTINCT da.event_user_id)  AS attendee_count,
                AVG(da.engagement_score)           AS avg_engagement,
                COUNT(DISTINCT da.event_id)        AS event_count
            FROM on24master.dw_attendee da
            JOIN on24master.event_user eu
              ON eu.event_user_id = da.event_user_id
            JOIN on24master.event e
              ON e.event_id = da.event_id
             AND e.client_id = ANY($1::bigint[])
            WHERE e.goodafter >= NOW() - ($2 || ' months')::INTERVAL
              AND e.goodafter <= NOW()
              AND eu.company IS NOT NULL
              AND TRIM(eu.company) <> ''
              {_EXCL_TEST}
            GROUP BY eu.company
            ORDER BY attendee_count DESC NULLS LAST
            LIMIT $3
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, client_ids, str(months), limit, timeout=_QUERY_TIMEOUT)

    results = []
    for row in rows:
        r = dict(row)
        if r.get("avg_engagement") is not None:
            r["avg_engagement"] = round(float(r["avg_engagement"]), 2)
        results.append(_serialize(r))
    return results


async def get_polls(event_id: int) -> list[dict]:
    """Get poll questions and answer distributions for an event.

    Returns list of questions. Multiple-choice questions include an 'answers'
    list with answer_cd, answer_text, response_count. Open-text questions
    include response_count and sample_answers.
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    # Multiple-choice / rated questions
    mc_sql = """
        SELECT
            MU.MEDIA_URL_ID                           AS poll_id,
            Q.QUESTION_ID                             AS question_id,
            Q.DESCRIPTION                             AS question_text,
            Q.QUESTION_TYPE_CD                        AS question_type_cd,
            QA.ANSWER_CD                              AS answer_cd,
            QA.ANSWER                                 AS answer_text,
            COUNT(DISTINCT EUA.EVENT_USER_ID)         AS response_count
        FROM on24master.event_user_x_answer EUA
        JOIN on24master.event_user EU
          ON EU.EVENT_USER_ID = EUA.EVENT_USER_ID
        JOIN on24master.event E
          ON E.EVENT_ID = EU.EVENT_ID
         AND E.CLIENT_ID = ANY($2::bigint[])
        JOIN on24master.media_url MU
          ON MU.MEDIA_URL_ID = EUA.MEDIA_URL_ID
        JOIN on24master.question Q
          ON Q.QUESTION_ID = EUA.QUESTION_ID
        JOIN on24master.question_x_answer QA
          ON QA.QUESTION_ID = Q.QUESTION_ID
         AND (EUA.ANSWER_CD = QA.ANSWER_CD OR Q.QUESTION_TYPE_CD = 'npsrating')
        WHERE EU.EVENT_ID = $1
          AND MU.MEDIA_URL_CD = 'poll'
          AND MU.MEDIA_URL_NAME NOT LIKE '%<!--##test##-->%'
          AND MU.MEDIA_URL_NAME NOT LIKE '%<!--##survey##-->%'
          AND Q.QUESTION_TYPE_CD NOT IN ('singletext', 'singleanswer')
        GROUP BY MU.MEDIA_URL_ID, Q.QUESTION_ID, Q.DESCRIPTION,
                 Q.QUESTION_TYPE_CD, QA.ANSWER_CD, QA.ANSWER
        ORDER BY Q.QUESTION_ID, response_count DESC
    """

    # Open-text questions
    text_sql = """
        SELECT
            Q.QUESTION_ID                             AS question_id,
            Q.DESCRIPTION                             AS question_text,
            Q.QUESTION_TYPE_CD                        AS question_type_cd,
            COUNT(DISTINCT EUA.EVENT_USER_ID)         AS response_count,
            (ARRAY_AGG(DISTINCT EUA.ANSWER))[1:5]     AS sample_answers
        FROM on24master.event_user_x_answer EUA
        JOIN on24master.event_user EU
          ON EU.EVENT_USER_ID = EUA.EVENT_USER_ID
        JOIN on24master.event E
          ON E.EVENT_ID = EU.EVENT_ID
         AND E.CLIENT_ID = ANY($2::bigint[])
        JOIN on24master.media_url MU
          ON MU.MEDIA_URL_ID = EUA.MEDIA_URL_ID
        JOIN on24master.question Q
          ON Q.QUESTION_ID = EUA.QUESTION_ID
        WHERE EU.EVENT_ID = $1
          AND MU.MEDIA_URL_CD = 'poll'
          AND MU.MEDIA_URL_NAME NOT LIKE '%<!--##test##-->%'
          AND MU.MEDIA_URL_NAME NOT LIKE '%<!--##survey##-->%'
          AND Q.QUESTION_TYPE_CD IN ('singletext', 'singleanswer')
          AND EUA.ANSWER IS NOT NULL
          AND TRIM(EUA.ANSWER) <> ''
        GROUP BY Q.QUESTION_ID, Q.DESCRIPTION, Q.QUESTION_TYPE_CD
        ORDER BY Q.QUESTION_ID
    """

    async with pool.acquire() as conn:
        mc_rows = await conn.fetch(mc_sql, event_id, client_ids, timeout=_QUERY_TIMEOUT)
        text_rows = await conn.fetch(text_sql, event_id, client_ids, timeout=_QUERY_TIMEOUT)

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


async def get_ai_content(
    content_type: Optional[str] = None,
    limit: int = 3,
) -> list[dict]:
    """Fetch AI-ACE generated articles from video_library (Media Manager).

    Args:
        content_type: BLOG, EBOOK, FAQ, KEYTAKEAWAYS, FOLLOWUPEMAIL,
                      SOCIALMEDIA, TRANSCRIPT — or None/empty for all types.
        limit: Max articles to return (default 3, max 10).

    Returns deduplicated list (longest article per event+type).
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()
    limit = max(1, min(limit, 10))

    if content_type:
        ct_upper = content_type.strip().upper()
        source_filter = (
            _AI_CONTENT_TYPES.get(ct_upper)
            or _AI_CONTENT_TYPES.get(ct_upper.replace("-", " ").replace("_", " "))
            or (f"AUTOGEN_{ct_upper}" if not ct_upper.startswith("AUTOGEN_") else ct_upper)
        )
        source_clause = "AND vl.source = $2"
        params: list = [client_ids, source_filter, limit]
        param_limit = "$3"
    else:
        source_clause = "AND vl.source LIKE 'AUTO%'"
        params = [client_ids, limit]
        param_limit = "$2"

    sql = f"""
        SELECT
            replace(vl.source, 'AUTOGEN_', '')        AS content_type,
            vl.media_content                           AS content,
            vl.source_event_id                         AS event_id,
            e.description                              AS event_title,
            vl.creation_timestamp                      AS created_at
        FROM on24master.video_library vl
        LEFT JOIN on24master.event e ON e.event_id = vl.source_event_id
        WHERE vl.client_id = ANY($1::bigint[])
          {source_clause}
        ORDER BY vl.creation_timestamp DESC
        LIMIT {param_limit}
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params, timeout=_QUERY_TIMEOUT)

    # Deduplicate: keep longest article per (event_id, content_type)
    best: dict[tuple, dict] = {}
    for row in rows:
        ct = row["content_type"] or ""
        if not ct:
            continue
        key = (row["event_id"], ct)
        article = {
            "content_type": ct,
            "title": row["event_title"] or "",
            "content": (row["content"] or "")[:50000],
            "event_id": row["event_id"],
            "event_title": row["event_title"] or "",
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        existing = best.get(key)
        if not existing or len(article["content"]) > len(existing["content"]):
            best[key] = article

    return list(best.values())
