"""Analytics dashboard endpoints with KPI summaries and trend data."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models import Event
from app.schemas.event import DashboardKPI, TopEvent, TrendPoint

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
    conversion_rate = (
        round((total_attendees / total_registrants) * 100, 2)
        if total_registrants > 0
        else None
    )

    return DashboardKPI(
        total_events=row.total_events,
        total_attendees=total_attendees,
        total_registrants=total_registrants,
        avg_engagement_score=(
            round(float(row.avg_engagement_score), 2)
            if row.avg_engagement_score is not None
            else None
        ),
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
            avg_engagement=(
                round(float(row.avg_engagement), 2)
                if row.avg_engagement is not None
                else None
            ),
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

    query = (
        select(Event)
        .order_by(sort_col.desc().nullslast())
        .limit(limit)
    )

    result = await db.execute(query)
    events = result.scalars().all()

    return [
        TopEvent(
            on24_event_id=e.on24_event_id,
            title=e.title,
            total_attendees=e.total_attendees,
            engagement_score=(
                float(e.engagement_score) if e.engagement_score is not None else None
            ),
            live_start=e.live_start,
        )
        for e in events
    ]
