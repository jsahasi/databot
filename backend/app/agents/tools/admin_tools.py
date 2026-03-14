"""Admin tool handlers for the Admin Agent — ON24 write operations."""

import logging
from typing import Any

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models import Event
from app.services.on24_client import ON24Client

logger = logging.getLogger(__name__)


def _get_on24_client() -> ON24Client:
    """Return a new ON24Client using settings defaults."""
    return ON24Client()


async def create_event(
    title: str,
    event_type: str,
    start_time: str,
    end_time: str,
    description: str | None = None,
) -> dict[str, Any]:
    """Create a new ON24 event and return its ID."""
    from app.config import settings
    if settings.mcp_enabled and "create_event" not in settings.mcp_blocklist:
        from app.services.mcp_client import call_mcp_tool
        return await call_mcp_tool("create_event", {
            "title": title, "event_type": event_type,
            "start_time": start_time, "end_time": end_time,
            "description": description or "",
        })
    client = _get_on24_client()
    try:
        response = await client.create_event(
            title=title, event_type=event_type,
            start_time=start_time, end_time=end_time, description=description,
        )
        logger.info(f"Created ON24 event: {response}")
        on24_event_id = response.get("eventId") or response.get("on24EventId") or response.get("id")
        return {
            "success": True, "on24_event_id": on24_event_id,
            "message": f"Event '{title}' created successfully.", "raw_response": response,
        }
    except Exception as e:
        logger.error(f"create_event failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def update_event(
    on24_event_id: int,
    title: str | None = None,
    description: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict[str, Any]:
    """Update fields on an existing ON24 event."""
    from app.config import settings
    if settings.mcp_enabled and "update_event" not in settings.mcp_blocklist:
        from app.services.mcp_client import call_mcp_tool
        return await call_mcp_tool("update_event", {
            "on24_event_id": on24_event_id,
            "title": title or "", "description": description or "",
            "start_time": start_time or "", "end_time": end_time or "",
        })
    client = _get_on24_client()
    try:
        response = await client.update_event(
            event_id=on24_event_id,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
        )
        logger.info(f"Updated ON24 event {on24_event_id}: {response}")
        return {
            "success": True,
            "on24_event_id": on24_event_id,
            "message": f"Event {on24_event_id} updated successfully.",
            "raw_response": response,
        }
    except Exception as e:
        logger.error(f"update_event failed for {on24_event_id}: {e}")
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def add_registrant(
    on24_event_id: int,
    email: str,
    first_name: str,
    last_name: str,
    company: str | None = None,
    job_title: str | None = None,
) -> dict[str, Any]:
    """Register a person for an ON24 event."""
    from app.config import settings
    if settings.mcp_enabled and "add_registrant" not in settings.mcp_blocklist:
        from app.services.mcp_client import call_mcp_tool
        return await call_mcp_tool("add_registrant", {
            "on24_event_id": on24_event_id, "email": email,
            "first_name": first_name, "last_name": last_name,
            "company": company or "", "job_title": job_title or "",
        })
    client = _get_on24_client()
    try:
        response = await client.register_attendee(
            event_id=on24_event_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            company=company,
            job_title=job_title,
        )
        logger.info(f"Registered {email} for event {on24_event_id}: {response}")
        return {
            "success": True,
            "on24_event_id": on24_event_id,
            "email": email,
            "message": f"{first_name} {last_name} ({email}) registered for event {on24_event_id}.",
            "raw_response": response,
        }
    except Exception as e:
        logger.error(f"add_registrant failed for {email} / event {on24_event_id}: {e}")
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def remove_registrant(
    on24_event_id: int,
    email: str,
) -> dict[str, Any]:
    """Remove a registrant from an ON24 event."""
    from app.config import settings
    if settings.mcp_enabled and "remove_registrant" not in settings.mcp_blocklist:
        from app.services.mcp_client import call_mcp_tool
        return await call_mcp_tool("remove_registrant", {
            "on24_event_id": on24_event_id, "email": email,
        })
    client = _get_on24_client()
    try:
        response = await client.remove_registration(event_id=on24_event_id, email=email)
        logger.info(f"Removed registrant {email} from event {on24_event_id}: {response}")
        return {
            "success": True,
            "on24_event_id": on24_event_id,
            "email": email,
            "message": f"Registration for {email} removed from event {on24_event_id}.",
            "raw_response": response,
        }
    except Exception as e:
        logger.error(f"remove_registrant failed for {email} / event {on24_event_id}: {e}")
        return {"success": False, "error": str(e)}
    finally:
        await client.close()


async def get_event_summary(on24_event_id: int) -> dict[str, Any]:
    """Return a summary of an event from the local DB for confirmation display."""
    async with async_session_factory() as session:
        stmt = select(Event).where(Event.on24_event_id == on24_event_id)
        result = await session.execute(stmt)
        event = result.scalar_one_or_none()

        if event is None:
            return {
                "found": False,
                "on24_event_id": on24_event_id,
                "message": f"No local record found for event ID {on24_event_id}.",
            }

        return {
            "found": True,
            "on24_event_id": event.on24_event_id,
            "title": event.title,
            "event_type": event.event_type,
            "is_active": event.is_active,
            "live_start": event.live_start.isoformat() if event.live_start else None,
            "live_end": event.live_end.isoformat() if event.live_end else None,
            "total_registrants": event.total_registrants,
            "total_attendees": event.total_attendees,
            "engagement_score": float(event.engagement_score) if event.engagement_score else None,
        }
