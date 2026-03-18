"""Analytics dashboard endpoints with KPI summaries and trend data."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Float, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models import Attendee, Event, Registrant
from app.schemas.event import (
    AudienceAnalytics,
    CompanyAudience,
    ContentPerformance,
    ContentTypePerformance,
    DashboardKPI,
    HeatmapPoint,
    TopEvent,
    TrendPoint,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /analytics/dashboard – KPI summary
# ---------------------------------------------------------------------------


@router.get("/dashboard", response_model=DashboardKPI)
async def dashboard(db: AsyncSession = Depends(get_db)):
    """Return high-level KPI metrics for the analytics dashboard."""
    result = await db.execute(
        select(
            func.count(Event.id).label("total_events"),
            func.coalesce(func.sum(Event.total_attendees), 0).label("total_attendees"),
            func.coalesce(func.sum(Event.total_registrants), 0).label("total_registrants"),
            func.avg(Event.engagement_score).label("avg_engagement_score"),
        )
    )
    row = result.one()

    total_registrants = int(row.total_registrants)
    total_attendees = int(row.total_attendees)
    conversion_rate = round((total_attendees / total_registrants) * 100, 2) if total_registrants > 0 else None

    return DashboardKPI(
        total_events=row.total_events,
        total_attendees=total_attendees,
        total_registrants=total_registrants,
        avg_engagement_score=(round(float(row.avg_engagement_score), 2) if row.avg_engagement_score is not None else None),
        conversion_rate=conversion_rate,
    )


# ---------------------------------------------------------------------------
# GET /analytics/trends – time-series data
# ---------------------------------------------------------------------------


@router.get("/trends", response_model=list[TrendPoint])
async def trends(
    months: int = Query(12, ge=1, le=60, description="Number of months to look back"),
    db: AsyncSession = Depends(get_db),
):
    """Return time-series trend data grouped by month."""
    # Build a period label like '2025-03'
    period_expr = func.to_char(Event.live_start, "YYYY-MM")

    query = (
        select(
            period_expr.label("period"),
            func.count(Event.id).label("events"),
            func.coalesce(func.sum(Event.total_attendees), 0).label("attendees"),
            func.avg(Event.engagement_score).label("avg_engagement"),
        )
        .where(Event.live_start.isnot(None))
        .group_by(period_expr)
        .order_by(period_expr.desc())
        .limit(months)
    )

    result = await db.execute(query)
    rows = result.all()

    # Reverse so oldest period is first (chronological order)
    return [
        TrendPoint(
            period=row.period,
            events=row.events,
            attendees=int(row.attendees),
            avg_engagement=(round(float(row.avg_engagement), 2) if row.avg_engagement is not None else None),
        )
        for row in reversed(rows)
    ]


# ---------------------------------------------------------------------------
# GET /analytics/top-events – top events by attendance or engagement
# ---------------------------------------------------------------------------


@router.get("/top-events", response_model=list[TopEvent])
async def top_events(
    limit: int = Query(10, ge=1, le=100, description="Number of top events to return"),
    sort_by: str = Query(
        "total_attendees",
        description="Rank by: total_attendees or engagement_score",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Return top events ranked by attendance or engagement score."""
    sort_column_map = {
        "total_attendees": Event.total_attendees,
        "engagement_score": Event.engagement_score,
    }
    sort_col = sort_column_map.get(sort_by, Event.total_attendees)

    query = select(Event).order_by(sort_col.desc().nullslast()).limit(limit)

    result = await db.execute(query)
    events = result.scalars().all()

    return [
        TopEvent(
            on24_event_id=e.on24_event_id,
            title=e.title,
            total_attendees=e.total_attendees,
            engagement_score=(float(e.engagement_score) if e.engagement_score is not None else None),
            live_start=e.live_start,
        )
        for e in events
    ]


# ---------------------------------------------------------------------------
# GET /analytics/audiences – cross-event audience analytics
# ---------------------------------------------------------------------------


@router.get("/audiences", response_model=AudienceAnalytics)
async def audiences(db: AsyncSession = Depends(get_db)):
    """Return cross-event audience analytics including company breakdown,
    registration sources, and country distribution."""

    # Top companies by total attendances and unique events attended
    company_query = (
        select(
            Attendee.company.label("company"),
            func.count(func.distinct(Attendee.on24_event_id)).label("events_attended"),
            func.count(Attendee.id).label("total_attendances"),
            func.avg(Attendee.engagement_score).label("avg_engagement"),
        )
        .where(Attendee.company.isnot(None), Attendee.company != "")
        .group_by(Attendee.company)
        .order_by(func.count(Attendee.id).desc())
        .limit(20)
    )
    company_result = await db.execute(company_query)
    company_rows = company_result.all()

    top_companies = [
        CompanyAudience(
            company=row.company,
            events_attended=row.events_attended,
            total_attendances=row.total_attendances,
            avg_engagement=(round(float(row.avg_engagement), 2) if row.avg_engagement is not None else None),
        )
        for row in company_rows
    ]

    # Registration source breakdown (utm_source counts)
    utm_query = (
        select(
            func.coalesce(Registrant.utm_source, "(direct)").label("utm_source"),
            func.count(Registrant.id).label("count"),
        )
        .group_by(func.coalesce(Registrant.utm_source, "(direct)"))
        .order_by(func.count(Registrant.id).desc())
        .limit(20)
    )
    utm_result = await db.execute(utm_query)
    registration_sources = [{"utm_source": row.utm_source, "count": row.count} for row in utm_result.all()]

    # Country distribution
    country_query = (
        select(
            func.coalesce(Registrant.country, "Unknown").label("country"),
            func.count(Registrant.id).label("count"),
        )
        .group_by(func.coalesce(Registrant.country, "Unknown"))
        .order_by(func.count(Registrant.id).desc())
        .limit(30)
    )
    country_result = await db.execute(country_query)
    country_distribution = [{"country": row.country, "count": row.count} for row in country_result.all()]

    return AudienceAnalytics(
        top_companies=top_companies,
        registration_sources=registration_sources,
        country_distribution=country_distribution,
    )


# ---------------------------------------------------------------------------
# GET /analytics/content-performance – content metrics by type and top events
# ---------------------------------------------------------------------------


@router.get("/content-performance", response_model=ContentPerformance)
async def content_performance(db: AsyncSession = Depends(get_db)):
    """Return content performance metrics grouped by event type plus top 10
    performing events and a month-over-month engagement trend."""

    # Events by type with aggregate metrics
    type_query = (
        select(
            func.coalesce(Event.event_type, "Unknown").label("event_type"),
            func.count(Event.id).label("event_count"),
            func.avg(Event.total_attendees).label("avg_attendees"),
            func.avg(Event.engagement_score).label("avg_engagement"),
            func.avg(cast(Event.total_attendees, Float) / func.nullif(cast(Event.total_registrants, Float), 0) * 100).label("avg_conversion_rate"),
        )
        .group_by(func.coalesce(Event.event_type, "Unknown"))
        .order_by(func.count(Event.id).desc())
    )
    type_result = await db.execute(type_query)

    by_type = [
        ContentTypePerformance(
            event_type=row.event_type,
            event_count=row.event_count,
            avg_attendees=round(float(row.avg_attendees), 1) if row.avg_attendees is not None else 0.0,
            avg_engagement=(round(float(row.avg_engagement), 2) if row.avg_engagement is not None else None),
            avg_conversion_rate=(round(float(row.avg_conversion_rate), 2) if row.avg_conversion_rate is not None else None),
        )
        for row in type_result.all()
    ]

    # Top 10 events by engagement score
    top_query = select(Event).where(Event.engagement_score.isnot(None)).order_by(Event.engagement_score.desc()).limit(10)
    top_result = await db.execute(top_query)
    top_events_list = [
        TopEvent(
            on24_event_id=e.on24_event_id,
            title=e.title,
            total_attendees=e.total_attendees,
            engagement_score=float(e.engagement_score),
            live_start=e.live_start,
        )
        for e in top_result.scalars().all()
    ]

    return ContentPerformance(
        by_type=by_type,
        top_events=top_events_list,
    )


# ---------------------------------------------------------------------------
# GET /analytics/engagement-heatmap – engagement by day-of-week × hour-of-day
# ---------------------------------------------------------------------------


@router.get("/engagement-heatmap", response_model=list[HeatmapPoint])
async def engagement_heatmap(db: AsyncSession = Depends(get_db)):
    """Return engagement aggregated by day-of-week (0=Mon…6=Sun) and hour-of-day
    for use in a heatmap visualisation."""

    # PostgreSQL: EXTRACT(DOW ...) returns 0=Sunday…6=Saturday.
    # We normalise to ISO convention (0=Monday…6=Sunday) in Python.
    dow_expr = func.extract("dow", Event.live_start).label("dow")
    hour_expr = func.extract("hour", Event.live_start).label("hour")

    query = (
        select(
            dow_expr,
            hour_expr,
            func.avg(Event.engagement_score).label("avg_engagement"),
            func.count(Event.id).label("event_count"),
        )
        .where(
            Event.live_start.isnot(None),
            Event.engagement_score.isnot(None),
        )
        .group_by(dow_expr, hour_expr)
        .order_by(dow_expr, hour_expr)
    )

    result = await db.execute(query)
    rows = result.all()

    points: list[HeatmapPoint] = []
    for row in rows:
        # Convert PostgreSQL Sunday=0 → ISO Monday=0
        pg_dow = int(row.dow)
        iso_day = (pg_dow - 1) % 7  # Sun(0)->6, Mon(1)->0, …, Sat(6)->5
        points.append(
            HeatmapPoint(
                day=iso_day,
                hour=int(row.hour),
                avg_engagement=round(float(row.avg_engagement), 2),
                event_count=row.event_count,
            )
        )

    return points
