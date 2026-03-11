"""ETL sync service: pulls data from ON24 API and upserts into PostgreSQL."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models import Attendee, Event, Registrant, SyncLog
from app.services.on24_client import ON24APIError, ON24Client

logger = logging.getLogger(__name__)


def _parse_datetime(value: Any) -> Optional[datetime]:
    """Parse ON24 datetime strings to timezone-aware datetime.

    ON24 returns dates in several formats depending on the field.
    All parsed datetimes are normalised to UTC.
    """
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(str(value), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    logger.warning("Could not parse datetime value: %s", value)
    return None


def _safe_int(value: Any, default: int = 0) -> int:
    """Coerce a value to int, returning *default* on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


class SyncService:
    """Orchestrates pulling data from ON24 and upserting into PostgreSQL."""

    def __init__(self, client: ON24Client | None = None) -> None:
        self.client = client or ON24Client()

    # ── Internal helpers ─────────────────────────────────────────────

    async def _create_sync_log(
        self,
        session: AsyncSession,
        entity_type: str,
        event_id: int | None = None,
    ) -> SyncLog:
        sync_log = SyncLog(
            entity_type=entity_type,
            on24_event_id=event_id,
            status="running",
            records_synced=0,
        )
        session.add(sync_log)
        await session.flush()
        return sync_log

    async def _complete_sync_log(
        self,
        session: AsyncSession,
        sync_log: SyncLog,
        records: int,
        error: str | None = None,
    ) -> None:
        sync_log.status = "failed" if error else "completed"
        sync_log.records_synced = records
        sync_log.completed_at = datetime.now(timezone.utc)
        sync_log.error_message = error

    # ── Events ───────────────────────────────────────────────────────

    async def sync_events(self) -> int:
        """Sync all events from ON24 to the database.

        Returns:
            Number of event records upserted.
        """
        async with async_session_factory() as session:
            sync_log = await self._create_sync_log(session, "events")
            try:
                events_data = await self.client.paginate(
                    "event", items_key="events", items_per_page=100
                )

                count = 0
                now = datetime.now(timezone.utc)
                for ev in events_data:
                    analytics = ev.get("eventanalytics") or {}
                    values = {
                        "on24_event_id": ev.get("eventid"),
                        "client_id": ev.get("clientid"),
                        "title": ev.get("eventname", "Untitled"),
                        "description": ev.get("description"),
                        "event_type": ev.get("eventtype"),
                        "content_type": ev.get("contenttype"),
                        "language": ev.get("languagecd"),
                        "timezone": ev.get("timezone"),
                        "is_active": ev.get("isactive", "Y") == "Y",
                        "registration_required": ev.get("regrequired", "Y") == "Y",
                        "live_start": _parse_datetime(ev.get("livestart")),
                        "live_end": _parse_datetime(ev.get("liveend")),
                        "archive_start": _parse_datetime(ev.get("archivestart")),
                        "archive_end": _parse_datetime(ev.get("archiveend")),
                        "start_time": _parse_datetime(ev.get("goodafter")),
                        "end_time": _parse_datetime(ev.get("goodtill")),
                        "on24_created": _parse_datetime(ev.get("createtimestamp")),
                        "on24_last_modified": _parse_datetime(ev.get("lastmodified")),
                        "total_registrants": _safe_int(analytics.get("totalregistrants")),
                        "total_attendees": _safe_int(analytics.get("totalattendees")),
                        "live_attendees": _safe_int(analytics.get("liveattendees")),
                        "on_demand_attendees": _safe_int(analytics.get("ondemandattendees")),
                        "no_show_count": _safe_int(analytics.get("noshowcount")),
                        "engagement_score": analytics.get("engagementscore"),
                        "audience_url": ev.get("audienceurl"),
                        "report_url": ev.get("reporturl"),
                        "tags": ev.get("tags"),
                        "raw_json": ev,
                        "synced_at": now,
                    }

                    update_values = {
                        k: v
                        for k, v in values.items()
                        if k not in ("on24_event_id", "client_id")
                    }

                    stmt = (
                        pg_insert(Event)
                        .values(**values)
                        .on_conflict_do_update(
                            index_elements=["on24_event_id"],
                            set_=update_values,
                        )
                    )
                    await session.execute(stmt)
                    count += 1

                await self._complete_sync_log(session, sync_log, count)
                await session.commit()
                logger.info("Synced %d events", count)
                return count

            except ON24APIError as exc:
                await self._complete_sync_log(session, sync_log, 0, str(exc))
                await session.commit()
                logger.error("Failed to sync events: %s", exc)
                raise
            except Exception as exc:
                await self._complete_sync_log(session, sync_log, 0, str(exc))
                await session.commit()
                logger.error("Unexpected error syncing events: %s", exc)
                raise

    # ── Attendees ────────────────────────────────────────────────────

    async def sync_event_attendees(self, event_id: int) -> int:
        """Sync attendees for a specific event from ON24 to the database.

        Args:
            event_id: The ON24 event ID.

        Returns:
            Number of attendee records upserted.
        """
        async with async_session_factory() as session:
            sync_log = await self._create_sync_log(session, "attendees", event_id)
            try:
                attendees_data = await self.client.paginate(
                    f"event/{event_id}/attendee",
                    items_key="attendees",
                    items_per_page=100,
                )

                count = 0
                now = datetime.now(timezone.utc)
                for att in attendees_data:
                    values = {
                        "on24_attendee_id": att.get("eventuserid"),
                        "on24_event_id": event_id,
                        "email": att.get("email", ""),
                        "first_name": att.get("firstname"),
                        "last_name": att.get("lastname"),
                        "company": att.get("company"),
                        "join_time": _parse_datetime(att.get("jointime")),
                        "leave_time": _parse_datetime(att.get("leavetime")),
                        "live_minutes": _safe_int(att.get("liveminutes"), 0),
                        "archive_minutes": _safe_int(att.get("archiveminutes"), 0),
                        "cumulative_live_minutes": _safe_int(
                            att.get("cumulativeliveminutes"), 0
                        ),
                        "cumulative_archive_minutes": _safe_int(
                            att.get("cumulativearchiveminutes"), 0
                        ),
                        "engagement_score": att.get("engagementscore"),
                        "asked_questions": _safe_int(att.get("askedquestions")),
                        "resources_downloaded": _safe_int(att.get("resourcesdownloaded")),
                        "answered_polls": _safe_int(att.get("answeredpolls")),
                        "answered_surveys": _safe_int(att.get("answeredsurveys")),
                        "launch_mode": att.get("launchmode"),
                        "questions": att.get("questions"),
                        "polls": att.get("polls"),
                        "resources": att.get("resources"),
                        "surveys": att.get("surveys"),
                        "call_to_actions": att.get("calltoactions"),
                        "raw_json": att,
                        "synced_at": now,
                    }

                    # Fields to update on conflict (everything except the unique key pair)
                    update_values = {
                        k: v
                        for k, v in values.items()
                        if k not in ("on24_attendee_id", "on24_event_id")
                    }

                    stmt = (
                        pg_insert(Attendee)
                        .values(**values)
                        .on_conflict_do_update(
                            constraint="uq_attendee_event",
                            set_=update_values,
                        )
                    )
                    await session.execute(stmt)
                    count += 1

                await self._complete_sync_log(session, sync_log, count)
                await session.commit()
                logger.info("Synced %d attendees for event %d", count, event_id)
                return count

            except ON24APIError as exc:
                await self._complete_sync_log(session, sync_log, 0, str(exc))
                await session.commit()
                logger.error(
                    "Failed to sync attendees for event %d: %s", event_id, exc
                )
                raise
            except Exception as exc:
                await self._complete_sync_log(session, sync_log, 0, str(exc))
                await session.commit()
                logger.error(
                    "Unexpected error syncing attendees for event %d: %s",
                    event_id,
                    exc,
                )
                raise

    # ── Registrants ──────────────────────────────────────────────────

    async def sync_event_registrants(self, event_id: int) -> int:
        """Sync registrants for a specific event from ON24 to the database.

        Args:
            event_id: The ON24 event ID.

        Returns:
            Number of registrant records upserted.
        """
        async with async_session_factory() as session:
            sync_log = await self._create_sync_log(session, "registrants", event_id)
            try:
                registrants_data = await self.client.paginate(
                    f"event/{event_id}/registrant",
                    items_key="registrants",
                    items_per_page=100,
                )

                count = 0
                now = datetime.now(timezone.utc)
                for reg in registrants_data:
                    # Collect ON24 standard custom fields (std1-std10) into JSONB
                    custom_fields: dict[str, Any] = {}
                    for i in range(1, 11):
                        key = f"std{i}"
                        val = reg.get(key)
                        if val is not None:
                            custom_fields[key] = val
                    if not custom_fields:
                        custom_fields = None  # type: ignore[assignment]

                    values = {
                        "on24_registrant_id": reg.get("eventuserid"),
                        "on24_event_id": event_id,
                        "email": reg.get("email", ""),
                        "first_name": reg.get("firstname"),
                        "last_name": reg.get("lastname"),
                        "company": reg.get("company"),
                        "job_title": reg.get("jobtitle"),
                        "job_function": reg.get("jobfunction"),
                        "city": reg.get("city"),
                        "state": reg.get("state"),
                        "country": reg.get("country"),
                        "zip_code": reg.get("zipcode"),
                        "work_phone": reg.get("workphone"),
                        "company_industry": reg.get("companyindustry"),
                        "company_size": reg.get("companysize"),
                        "partner_ref": reg.get("partnerref"),
                        "registration_status": reg.get("registrationstatus"),
                        "registration_date": _parse_datetime(
                            reg.get("registrationdate")
                        ),
                        "last_activity": _parse_datetime(reg.get("lastactivity")),
                        "utm_source": reg.get("utmsource"),
                        "utm_medium": reg.get("utmmedium"),
                        "utm_campaign": reg.get("utmcampaign"),
                        "custom_fields": custom_fields,
                        "raw_json": reg,
                        "synced_at": now,
                    }

                    update_values = {
                        k: v
                        for k, v in values.items()
                        if k not in ("on24_registrant_id", "on24_event_id")
                    }

                    stmt = (
                        pg_insert(Registrant)
                        .values(**values)
                        .on_conflict_do_update(
                            constraint="uq_registrant_event",
                            set_=update_values,
                        )
                    )
                    await session.execute(stmt)
                    count += 1

                await self._complete_sync_log(session, sync_log, count)
                await session.commit()
                logger.info("Synced %d registrants for event %d", count, event_id)
                return count

            except ON24APIError as exc:
                await self._complete_sync_log(session, sync_log, 0, str(exc))
                await session.commit()
                logger.error(
                    "Failed to sync registrants for event %d: %s", event_id, exc
                )
                raise
            except Exception as exc:
                await self._complete_sync_log(session, sync_log, 0, str(exc))
                await session.commit()
                logger.error(
                    "Unexpected error syncing registrants for event %d: %s",
                    event_id,
                    exc,
                )
                raise

    # ── Full sync orchestrator ───────────────────────────────────────

    async def sync_all(self) -> dict[str, int]:
        """Run a full sync: events first, then attendees and registrants per event.

        Errors on individual events are logged and skipped so that one
        failing event does not block the rest of the sync run.

        Returns:
            Dict with counts ``{"events": N, "attendees": N, "registrants": N}``.
        """
        results: dict[str, int] = {"events": 0, "attendees": 0, "registrants": 0}

        # 1. Sync events
        results["events"] = await self.sync_events()

        # 2. Fetch active event IDs from the database
        async with async_session_factory() as session:
            result = await session.execute(
                select(Event.on24_event_id).where(Event.is_active.is_(True))
            )
            event_ids: list[int] = [row[0] for row in result.fetchall()]

        # 3. Sync attendees and registrants for each event
        for eid in event_ids:
            try:
                att_count = await self.sync_event_attendees(eid)
                results["attendees"] += att_count
            except Exception as exc:
                logger.error("Failed to sync attendees for event %d: %s", eid, exc)

            try:
                reg_count = await self.sync_event_registrants(eid)
                results["registrants"] += reg_count
            except Exception as exc:
                logger.error("Failed to sync registrants for event %d: %s", eid, exc)

        logger.info("Full sync complete: %s", results)
        return results
