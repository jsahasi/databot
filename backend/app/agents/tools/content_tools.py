"""Content analysis tools for the Content Agent."""
import logging
from typing import Any
from sqlalchemy import func, select, desc, case
from app.db.session import async_session_factory
from app.models import Attendee, Event, PollResponse, SurveyResponse, Registrant

logger = logging.getLogger(__name__)


async def analyze_topic_performance(
    tag: str | None = None,
    min_events: int = 3,
    limit: int = 20,
) -> dict[str, Any]:
    """Analyze which event types/topics drive the highest engagement and attendance."""
    async with async_session_factory() as session:
        stmt = select(
            Event.event_type,
            func.count(Event.id).label("event_count"),
            func.avg(Event.total_attendees).label("avg_attendees"),
            func.avg(Event.engagement_score).label("avg_engagement"),
            func.avg(
                case(
                    (Event.total_registrants > 0,
                     Event.total_attendees * 100.0 / Event.total_registrants),
                    else_=None
                )
            ).label("avg_conversion_rate"),
        ).where(
            Event.event_type.isnot(None),
            Event.total_registrants > 0,
        ).group_by(Event.event_type).having(
            func.count(Event.id) >= min_events
        ).order_by(desc("avg_engagement")).limit(limit)

        result = await session.execute(stmt)
        rows = result.fetchall()

        return {
            "analysis": [
                {
                    "event_type": r.event_type,
                    "event_count": r.event_count,
                    "avg_attendees": round(float(r.avg_attendees or 0), 0),
                    "avg_engagement": round(float(r.avg_engagement or 0), 2),
                    "avg_conversion_rate": round(float(r.avg_conversion_rate or 0), 1),
                }
                for r in rows
            ],
            "insight": f"Analyzed {len(rows)} event types with at least {min_events} events each.",
        }


async def compare_event_performance(
    event_ids: list[int],
) -> dict[str, Any]:
    """Side-by-side performance comparison for a list of event IDs."""
    async with async_session_factory() as session:
        stmt = select(Event).where(Event.on24_event_id.in_(event_ids))
        result = await session.execute(stmt)
        events = result.scalars().all()

        comparisons = []
        for e in events:
            conv = (
                round(e.total_attendees / e.total_registrants * 100, 1)
                if e.total_registrants > 0 else None
            )
            comparisons.append({
                "event_id": e.on24_event_id,
                "title": e.title,
                "date": e.live_start.isoformat() if e.live_start else None,
                "registrants": e.total_registrants,
                "attendees": e.total_attendees,
                "no_shows": e.no_show_count,
                "engagement_score": float(e.engagement_score) if e.engagement_score else None,
                "conversion_rate": conv,
            })

        # Sort by engagement score desc
        comparisons.sort(key=lambda x: x["engagement_score"] or 0, reverse=True)
        return {"comparisons": comparisons, "count": len(comparisons)}


async def analyze_scheduling_patterns(
) -> dict[str, Any]:
    """Find the best day of week and time of day for scheduling events."""
    async with async_session_factory() as session:
        # Group by day of week
        dow_stmt = select(
            func.extract("dow", Event.live_start).label("day_of_week"),
            func.count(Event.id).label("event_count"),
            func.avg(Event.total_attendees).label("avg_attendees"),
            func.avg(Event.engagement_score).label("avg_engagement"),
        ).where(
            Event.live_start.isnot(None),
            Event.total_registrants > 0,
        ).group_by("day_of_week").order_by("day_of_week")

        dow_result = await session.execute(dow_stmt)
        dow_rows = dow_result.fetchall()

        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        by_day = [
            {
                "day": day_names[int(r.day_of_week)],
                "event_count": r.event_count,
                "avg_attendees": round(float(r.avg_attendees or 0), 0),
                "avg_engagement": round(float(r.avg_engagement or 0), 2),
            }
            for r in dow_rows
        ]

        # Group by hour of day
        hour_stmt = select(
            func.extract("hour", Event.live_start).label("hour"),
            func.count(Event.id).label("event_count"),
            func.avg(Event.total_attendees).label("avg_attendees"),
            func.avg(Event.engagement_score).label("avg_engagement"),
        ).where(
            Event.live_start.isnot(None),
            Event.total_registrants > 0,
        ).group_by("hour").order_by("hour")

        hour_result = await session.execute(hour_stmt)
        hour_rows = hour_result.fetchall()

        by_hour = [
            {
                "hour": f"{int(r.hour):02d}:00",
                "event_count": r.event_count,
                "avg_attendees": round(float(r.avg_attendees or 0), 0),
                "avg_engagement": round(float(r.avg_engagement or 0), 2),
            }
            for r in hour_rows
        ]

        # Find best day and hour
        best_day = max(by_day, key=lambda x: x["avg_engagement"], default=None)
        best_hour = max(by_hour, key=lambda x: x["avg_engagement"], default=None)

        return {
            "by_day_of_week": by_day,
            "by_hour": by_hour,
            "recommendation": {
                "best_day": best_day["day"] if best_day else None,
                "best_hour": best_hour["hour"] if best_hour else None,
            },
        }


async def suggest_topics(
    based_on: str = "engagement",
    limit: int = 5,
) -> dict[str, Any]:
    """Generate topic suggestions based on historical performance data."""
    async with async_session_factory() as session:
        # Get top performing events as seed
        sort_col = Event.engagement_score if based_on == "engagement" else Event.total_attendees
        stmt = select(Event).where(
            Event.title.isnot(None),
            Event.engagement_score.isnot(None),
        ).order_by(desc(sort_col)).limit(limit * 3)

        result = await session.execute(stmt)
        top_events = result.scalars().all()

        suggestions = []
        for e in top_events[:limit]:
            suggestions.append({
                "based_on_event": e.title,
                "event_id": e.on24_event_id,
                "engagement_score": float(e.engagement_score) if e.engagement_score else None,
                "attendees": e.total_attendees,
                "recommendation": f"Consider a follow-up or series based on '{e.title}' — it achieved {float(e.engagement_score or 0):.1f} engagement",
            })

        return {
            "suggestions": suggestions,
            "methodology": f"Based on top {based_on} scores from your event history",
        }
