"""Database query tools for the Data Agent."""

import logging
from typing import Any

from sqlalchemy import asc, desc, func, select

from app.db.session import async_session_factory
from app.models import Attendee, Event, Registrant

logger = logging.getLogger(__name__)


async def query_events(
    search: str | None = None,
    event_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = "live_start",
    sort_order: str = "desc",
    limit: int = 20,
) -> dict[str, Any]:
    """Query events from the database with optional filters."""
    async with async_session_factory() as session:
        stmt = select(Event)

        if search:
            stmt = stmt.where(Event.title.ilike(f"%{search}%"))
        if event_type:
            stmt = stmt.where(Event.event_type == event_type)
        if date_from:
            stmt = stmt.where(Event.live_start >= date_from)
        if date_to:
            stmt = stmt.where(Event.live_start <= date_to)

        order_col = getattr(Event, sort_by, Event.live_start)
        stmt = stmt.order_by(desc(order_col) if sort_order == "desc" else asc(order_col))
        stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        events = result.scalars().all()
        return {
            "events": [e.to_dict() for e in events],
            "count": len(events),
        }


async def query_attendees(
    event_id: int | None = None,
    email: str | None = None,
    company: str | None = None,
    min_engagement: float | None = None,
    sort_by: str = "engagement_score",
    limit: int = 50,
) -> dict[str, Any]:
    """Query attendees with optional filters."""
    async with async_session_factory() as session:
        stmt = select(Attendee)

        if event_id:
            stmt = stmt.where(Attendee.on24_event_id == event_id)
        if email:
            stmt = stmt.where(Attendee.email.ilike(f"%{email}%"))
        if company:
            stmt = stmt.where(Attendee.company.ilike(f"%{company}%"))
        if min_engagement is not None:
            stmt = stmt.where(Attendee.engagement_score >= min_engagement)

        order_col = getattr(Attendee, sort_by, Attendee.engagement_score)
        stmt = stmt.order_by(desc(order_col)).limit(limit)

        result = await session.execute(stmt)
        attendees = result.scalars().all()
        return {
            "attendees": [a.to_dict() for a in attendees],
            "count": len(attendees),
        }


async def query_registrants(
    event_id: int | None = None,
    company: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Query registrants with optional filters."""
    async with async_session_factory() as session:
        stmt = select(Registrant)

        if event_id:
            stmt = stmt.where(Registrant.on24_event_id == event_id)
        if company:
            stmt = stmt.where(Registrant.company.ilike(f"%{company}%"))

        stmt = stmt.order_by(desc(Registrant.registration_date)).limit(limit)

        result = await session.execute(stmt)
        registrants = result.scalars().all()
        return {
            "registrants": [r.to_dict() for r in registrants],
            "count": len(registrants),
        }


async def compute_kpis(
    event_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """Compute analytics KPIs, optionally scoped to an event or date range."""
    async with async_session_factory() as session:
        # Base event query
        event_stmt = select(Event)
        if event_id:
            event_stmt = event_stmt.where(Event.on24_event_id == event_id)
        if date_from:
            event_stmt = event_stmt.where(Event.live_start >= date_from)
        if date_to:
            event_stmt = event_stmt.where(Event.live_start <= date_to)

        result = await session.execute(event_stmt)
        events = result.scalars().all()

        total_events = len(events)
        total_registrants = sum(e.total_registrants for e in events)
        total_attendees = sum(e.total_attendees for e in events)
        total_no_shows = sum(e.no_show_count for e in events)

        engagement_scores = [float(e.engagement_score) for e in events if e.engagement_score]
        avg_engagement = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0

        conversion_rate = (total_attendees / total_registrants * 100) if total_registrants > 0 else 0

        return {
            "total_events": total_events,
            "total_registrants": total_registrants,
            "total_attendees": total_attendees,
            "total_no_shows": total_no_shows,
            "avg_engagement_score": round(avg_engagement, 2),
            "conversion_rate": round(conversion_rate, 1),
            "no_show_rate": round(total_no_shows / total_registrants * 100, 1) if total_registrants > 0 else 0,
        }


async def generate_chart_data(
    chart_type: str,
    metric: str = "attendees",
    group_by: str = "month",
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 12,
) -> dict[str, Any]:
    """Generate data formatted for frontend chart rendering.

    chart_type: 'line', 'bar', 'pie'
    metric: 'attendees', 'registrants', 'engagement', 'events'
    group_by: 'month', 'week', 'event_type', 'company'
    """
    async with async_session_factory() as session:
        if group_by == "month" and chart_type in ("line", "bar"):
            # Time-series data grouped by month
            stmt = select(
                func.to_char(Event.live_start, "YYYY-MM").label("period"),
                func.count(Event.id).label("event_count"),
                func.sum(Event.total_attendees).label("total_attendees"),
                func.sum(Event.total_registrants).label("total_registrants"),
                func.avg(Event.engagement_score).label("avg_engagement"),
            ).where(Event.live_start.isnot(None))

            if date_from:
                stmt = stmt.where(Event.live_start >= date_from)
            if date_to:
                stmt = stmt.where(Event.live_start <= date_to)

            stmt = stmt.group_by("period").order_by("period").limit(limit)
            result = await session.execute(stmt)
            rows = result.fetchall()

            data_points = []
            for row in rows:
                point = {
                    "period": row.period,
                    "event_count": row.event_count or 0,
                    "total_attendees": row.total_attendees or 0,
                    "total_registrants": row.total_registrants or 0,
                    "avg_engagement": round(float(row.avg_engagement or 0), 2),
                }
                data_points.append(point)

            return {
                "chart_type": chart_type,
                "data": data_points,
                "x_key": "period",
                "y_key": metric if metric != "engagement" else "avg_engagement",
                "title": f"{metric.replace('_', ' ').title()} by Month",
            }

        elif group_by == "event_type" and chart_type == "pie":
            stmt = (
                select(
                    Event.event_type,
                    func.count(Event.id).label("count"),
                )
                .where(Event.event_type.isnot(None))
                .group_by(Event.event_type)
                .limit(limit)
            )

            result = await session.execute(stmt)
            rows = result.fetchall()

            return {
                "chart_type": "pie",
                "data": [{"name": row.event_type, "value": row.count} for row in rows],
                "title": "Events by Type",
            }

        elif group_by == "company":
            stmt = (
                select(
                    Attendee.company,
                    func.count(Attendee.id).label("attendee_count"),
                    func.avg(Attendee.engagement_score).label("avg_engagement"),
                )
                .where(Attendee.company.isnot(None))
                .group_by(Attendee.company)
                .order_by(desc("attendee_count"))
                .limit(limit)
            )

            result = await session.execute(stmt)
            rows = result.fetchall()

            return {
                "chart_type": chart_type,
                "data": [{"company": row.company, "attendees": row.attendee_count, "avg_engagement": round(float(row.avg_engagement or 0), 2)} for row in rows],
                "x_key": "company",
                "y_key": "attendees",
                "title": "Top Companies by Attendance",
            }

        return {"chart_type": chart_type, "data": [], "title": "No data available"}


async def run_analytics_query(description: str, event_id: int | None = None) -> dict[str, Any]:
    """Run a predefined analytics query based on description.

    Supports: 'top_companies', 'engagement_distribution', 'registration_sources', 'no_show_analysis'
    """
    async with async_session_factory() as session:
        if description == "top_companies":
            stmt = select(
                Attendee.company,
                func.count(func.distinct(Attendee.on24_event_id)).label("events_attended"),
                func.count(Attendee.id).label("total_attendances"),
                func.avg(Attendee.engagement_score).label("avg_engagement"),
            ).where(Attendee.company.isnot(None))

            if event_id:
                stmt = stmt.where(Attendee.on24_event_id == event_id)

            stmt = stmt.group_by(Attendee.company).order_by(desc("total_attendances")).limit(20)
            result = await session.execute(stmt)
            rows = result.fetchall()

            return {
                "query": "top_companies",
                "results": [
                    {
                        "company": r.company,
                        "events_attended": r.events_attended,
                        "total_attendances": r.total_attendances,
                        "avg_engagement": round(float(r.avg_engagement or 0), 2),
                    }
                    for r in rows
                ],
            }

        elif description == "registration_sources":
            stmt = select(
                Registrant.utm_source,
                func.count(Registrant.id).label("count"),
            ).where(Registrant.utm_source.isnot(None))

            if event_id:
                stmt = stmt.where(Registrant.on24_event_id == event_id)

            stmt = stmt.group_by(Registrant.utm_source).order_by(desc("count")).limit(15)
            result = await session.execute(stmt)
            rows = result.fetchall()

            return {
                "query": "registration_sources",
                "results": [{"source": r.utm_source, "count": r.count} for r in rows],
            }

        elif description == "no_show_analysis":
            stmt = select(Event).where(Event.total_registrants > 0).order_by(desc(Event.live_start)).limit(50)
            result = await session.execute(stmt)
            events = result.scalars().all()

            return {
                "query": "no_show_analysis",
                "results": [
                    {
                        "event": e.title,
                        "registrants": e.total_registrants,
                        "attendees": e.total_attendees,
                        "no_shows": e.no_show_count,
                        "no_show_rate": round(e.no_show_count / e.total_registrants * 100, 1) if e.total_registrants > 0 else 0,
                    }
                    for e in events
                ],
            }

        return {"query": description, "results": [], "message": f"Unknown query: {description}"}
