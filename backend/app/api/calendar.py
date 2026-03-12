"""Calendar API — returns events grouped by month for the calendar UI."""

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Query

from app.db.on24_db import get_pool, get_tenant_client_ids

logger = logging.getLogger(__name__)
router = APIRouter()

_QUERY_TIMEOUT = 10.0


def _is_future(start_time) -> bool:
    if start_time is None:
        return False
    now = datetime.now(timezone.utc)
    if hasattr(start_time, "tzinfo") and start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    return start_time > now


def _serialize_event(row: dict, include_kpis: bool) -> dict:
    e = dict(row)
    st = e.get("start_time")
    et = e.get("end_time")
    result = {
        "event_id": e.get("event_id"),
        "title": e.get("title") or "",
        "abstract": e.get("abstract") or "",
        "start_time": st.isoformat() if st else None,
        "end_time": et.isoformat() if et else None,
        "event_type": e.get("event_type") or "",
        "is_future": _is_future(st),
    }
    if include_kpis and not result["is_future"]:
        reg = e.get("registrant_count")
        att = e.get("attendee_count")
        conv = None
        if reg and att and reg > 0:
            conv = round(att / reg * 100, 1)
        result["registrant_count"] = int(reg) if reg is not None else None
        result["attendee_count"] = int(att) if att is not None else None
        result["conversion_rate"] = conv
    return result


@router.get("/calendar")
async def get_calendar(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
):
    """Return all events for a given year/month with KPIs for past events."""
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    # Month window — use naive datetimes (goodafter is timezone-naive in on24master)
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    sql = """
        SELECT
            e.event_id,
            e.description                     AS title,
            e.seo_abstract                    AS abstract,
            e.goodafter                       AS start_time,
            e.goodtill                        AS end_time,
            e.event_type                      AS event_type,
            SUM(s.registrant_count)           AS registrant_count,
            SUM(s.attendee_count)             AS attendee_count
        FROM on24master.event e
        LEFT JOIN on24master.dw_event_session s
               ON s.event_id = e.event_id
        WHERE e.client_id = ANY($1::bigint[])
          AND e.goodafter >= $2
          AND e.goodafter <  $3
          AND LOWER(e.description) NOT LIKE '%test%'
        GROUP BY e.event_id, e.description, e.seo_abstract,
                 e.goodafter, e.goodtill, e.event_type
        HAVING COALESCE(SUM(s.registrant_count), 0) >= 6
            OR e.goodafter > NOW()
        ORDER BY e.goodafter
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, client_ids, start, end, timeout=_QUERY_TIMEOUT)

    return [_serialize_event(dict(r), include_kpis=True) for r in rows]


@router.get("/calendar/event/{event_id}")
async def get_calendar_event(event_id: int):
    """Return summary for a single event (for the detail popover).
    Includes poll and survey response counts (excluded if zero).
    """
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    sql = """
        SELECT
            e.event_id,
            e.description                     AS title,
            e.seo_abstract                    AS abstract,
            e.goodafter                       AS start_time,
            e.goodtill                        AS end_time,
            e.event_type                      AS event_type,
            SUM(s.registrant_count)           AS registrant_count,
            SUM(s.attendee_count)             AS attendee_count
        FROM on24master.event e
        LEFT JOIN on24master.dw_event_session s
               ON s.event_id = e.event_id
        WHERE e.event_id = $1
          AND e.client_id = ANY($2::bigint[])
        GROUP BY e.event_id, e.description, e.seo_abstract,
                 e.goodafter, e.goodtill, e.event_type
        LIMIT 1
    """

    # COUNT DISTINCT event_user_id — a user may submit the same poll multiple times;
    # we count unique respondents, not raw answer rows.
    poll_sql = """
        SELECT COUNT(DISTINCT euxa.event_user_id) AS cnt
        FROM on24master.event_user_x_answer euxa
        JOIN on24master.event_user eu  ON eu.event_user_id  = euxa.event_user_id
        JOIN on24master.media_url mu   ON mu.media_url_id   = euxa.media_url_id
        WHERE eu.event_id = $1
          AND mu.media_url_cd = 'poll'
          AND mu.media_url_name NOT LIKE '%<!--##test##-->%'
          AND mu.media_url_name NOT LIKE '%<!--##survey##-->%'
    """

    survey_sql = """
        SELECT COUNT(DISTINCT euxa.event_user_id) AS cnt
        FROM on24master.event_user_x_answer euxa
        JOIN on24master.event_user eu  ON eu.event_user_id  = euxa.event_user_id
        JOIN on24master.media_url mu   ON mu.media_url_id   = euxa.media_url_id
        WHERE eu.event_id = $1
          AND mu.media_url_cd = 'survey'
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, event_id, client_ids, timeout=_QUERY_TIMEOUT)
        if not rows:
            raise HTTPException(status_code=404, detail="Event not found")

        result = _serialize_event(dict(rows[0]), include_kpis=True)

        # Only fetch response counts for past events
        if not result["is_future"]:
            try:
                poll_row = await conn.fetchrow(poll_sql, event_id, timeout=_QUERY_TIMEOUT)
                result["poll_response_count"] = int(poll_row["cnt"]) if poll_row else 0
            except Exception:
                result["poll_response_count"] = 0

            try:
                survey_row = await conn.fetchrow(survey_sql, event_id, timeout=_QUERY_TIMEOUT)
                result["survey_response_count"] = int(survey_row["cnt"]) if survey_row else 0
            except Exception:
                result["survey_response_count"] = 0

            try:
                resource_sql = """
                    SELECT COUNT(DISTINCT ct.event_user_id) AS cnt
                    FROM on24master.content_hit_track_details ct
                    WHERE ct.event_id = $1
                      AND ct.action = 'TotalHits'
                      AND COALESCE(ct.media_url_id, 0) != 0
                      AND COALESCE(ct.media_category_cd, 'xxx') NOT LIKE 'custom_icon%'
                      AND ct.event_user_id != 305999
                      AND (
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
                        EXISTS (
                            SELECT 1
                            FROM on24master.video_library vl
                            WHERE vl.portal_event_id = ct.event_id
                              AND vl.type = 'pdf'
                        )
                      )
                """
                resource_row = await conn.fetchrow(resource_sql, event_id, timeout=_QUERY_TIMEOUT)
                result["resource_download_count"] = int(resource_row["cnt"]) if resource_row else 0
            except Exception:
                result["resource_download_count"] = 0

    return result
