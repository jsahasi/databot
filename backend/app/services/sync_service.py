"""ETL sync service: pulls data from ON24 API and upserts into PostgreSQL."""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models import (
    Attendee,
    CTAClick,
    EngagementProfile,
    Event,
    PollResponse,
    Registrant,
    ResourceViewed,
    SurveyResponse,
    SyncLog,
)
from app.services.on24_client import ON24APIError, ON24Client

logger = logging.getLogger(__name__)


def _parse_datetime(value: Any) -> datetime | None:
    """Parse ON24 datetime strings to timezone-aware datetime.

    ON24 returns dates in several formats depending on the field.
    All parsed datetimes are normalised to UTC.
    """
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
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
                dt = dt.replace(tzinfo=UTC)
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
        sync_log.completed_at = datetime.now(UTC)
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
                events_data = await self.client.paginate("event", items_key="events", items_per_page=100)

                count = 0
                now = datetime.now(UTC)
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

                    update_values = {k: v for k, v in values.items() if k not in ("on24_event_id", "client_id")}

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
                now = datetime.now(UTC)
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
                        "cumulative_live_minutes": _safe_int(att.get("cumulativeliveminutes"), 0),
                        "cumulative_archive_minutes": _safe_int(att.get("cumulativearchiveminutes"), 0),
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
                    update_values = {k: v for k, v in values.items() if k not in ("on24_attendee_id", "on24_event_id")}

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
                logger.error("Failed to sync attendees for event %d: %s", event_id, exc)
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
                now = datetime.now(UTC)
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
                        "registration_date": _parse_datetime(reg.get("registrationdate")),
                        "last_activity": _parse_datetime(reg.get("lastactivity")),
                        "utm_source": reg.get("utmsource"),
                        "utm_medium": reg.get("utmmedium"),
                        "utm_campaign": reg.get("utmcampaign"),
                        "custom_fields": custom_fields,
                        "raw_json": reg,
                        "synced_at": now,
                    }

                    update_values = {k: v for k, v in values.items() if k not in ("on24_registrant_id", "on24_event_id")}

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
                logger.error("Failed to sync registrants for event %d: %s", event_id, exc)
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

    # ── Poll responses ───────────────────────────────────────────────

    async def sync_event_polls(self, event_id: int) -> int:
        """Sync poll responses for a specific event from ON24 to the database.

        Flattens the ON24 poll structure (poll -> answers list) into individual
        PollResponse rows, one per email+question+answer combination.

        Args:
            event_id: The ON24 event ID.

        Returns:
            Number of poll response records inserted.
        """
        async with async_session_factory() as session:
            sync_log = await self._create_sync_log(session, "polls", event_id)
            try:
                response = await self.client.get_event_polls(event_id)
                polls_data = response.get("polls", [])

                count = 0
                now = datetime.now(UTC)
                for poll in polls_data:
                    poll_id = poll.get("pollid")
                    question = poll.get("question")
                    answers = poll.get("answers") or []
                    for answer_item in answers:
                        values = {
                            "on24_event_id": event_id,
                            "poll_id": poll_id,
                            "attendee_email": answer_item.get("email", ""),
                            "question": question,
                            "answer": answer_item.get("answer"),
                            "responded_at": _parse_datetime(answer_item.get("timestamp")),
                            "raw_json": answer_item,
                            "synced_at": now,
                        }
                        stmt = pg_insert(PollResponse).values(**values).on_conflict_do_nothing()
                        await session.execute(stmt)
                        count += 1

                await self._complete_sync_log(session, sync_log, count)
                await session.commit()
                logger.info("Synced %d poll responses for event %d", count, event_id)
                return count

            except ON24APIError as exc:
                await self._complete_sync_log(session, sync_log, 0, str(exc))
                await session.commit()
                logger.error("Failed to sync polls for event %d: %s", event_id, exc)
                raise
            except Exception as exc:
                await self._complete_sync_log(session, sync_log, 0, str(exc))
                await session.commit()
                logger.error("Unexpected error syncing polls for event %d: %s", event_id, exc)
                raise

    # ── Survey responses ─────────────────────────────────────────────

    async def sync_event_surveys(self, event_id: int) -> int:
        """Sync survey responses for a specific event from ON24 to the database.

        Flattens the ON24 survey structure (survey -> answers list) into individual
        SurveyResponse rows, one per email+question+answer combination.

        Args:
            event_id: The ON24 event ID.

        Returns:
            Number of survey response records inserted.
        """
        async with async_session_factory() as session:
            sync_log = await self._create_sync_log(session, "surveys", event_id)
            try:
                response = await self.client.get_event_surveys(event_id)
                surveys_data = response.get("surveys", [])

                count = 0
                now = datetime.now(UTC)
                for survey in surveys_data:
                    survey_id = survey.get("survey_id")
                    question = survey.get("question")
                    answers = survey.get("answers") or []
                    for answer_item in answers:
                        values = {
                            "on24_event_id": event_id,
                            "survey_id": survey_id,
                            "attendee_email": answer_item.get("email", ""),
                            "question": question,
                            "answer": answer_item.get("answer"),
                            "responded_at": _parse_datetime(answer_item.get("timestamp")),
                            "raw_json": answer_item,
                            "synced_at": now,
                        }
                        stmt = pg_insert(SurveyResponse).values(**values).on_conflict_do_nothing()
                        await session.execute(stmt)
                        count += 1

                await self._complete_sync_log(session, sync_log, count)
                await session.commit()
                logger.info("Synced %d survey responses for event %d", count, event_id)
                return count

            except ON24APIError as exc:
                await self._complete_sync_log(session, sync_log, 0, str(exc))
                await session.commit()
                logger.error("Failed to sync surveys for event %d: %s", event_id, exc)
                raise
            except Exception as exc:
                await self._complete_sync_log(session, sync_log, 0, str(exc))
                await session.commit()
                logger.error("Unexpected error syncing surveys for event %d: %s", event_id, exc)
                raise

    # ── Resources viewed ─────────────────────────────────────────────

    async def sync_event_resources(self, event_id: int) -> int:
        """Sync resource view records for a specific event from ON24 to the database.

        Args:
            event_id: The ON24 event ID.

        Returns:
            Number of resource viewed records inserted.
        """
        async with async_session_factory() as session:
            sync_log = await self._create_sync_log(session, "resources", event_id)
            try:
                response = await self.client.get_event_resources(event_id)
                resources_data = response.get("resources", [])

                count = 0
                now = datetime.now(UTC)
                for resource in resources_data:
                    values = {
                        "on24_event_id": event_id,
                        "attendee_email": resource.get("email", ""),
                        "resource_name": resource.get("resourcename"),
                        "resource_type": resource.get("resourcetype"),
                        "viewed_at": _parse_datetime(resource.get("viewtime")),
                        "raw_json": resource,
                        "synced_at": now,
                    }
                    stmt = pg_insert(ResourceViewed).values(**values).on_conflict_do_nothing()
                    await session.execute(stmt)
                    count += 1

                await self._complete_sync_log(session, sync_log, count)
                await session.commit()
                logger.info("Synced %d resource views for event %d", count, event_id)
                return count

            except ON24APIError as exc:
                await self._complete_sync_log(session, sync_log, 0, str(exc))
                await session.commit()
                logger.error("Failed to sync resources for event %d: %s", event_id, exc)
                raise
            except Exception as exc:
                await self._complete_sync_log(session, sync_log, 0, str(exc))
                await session.commit()
                logger.error("Unexpected error syncing resources for event %d: %s", event_id, exc)
                raise

    # ── CTA clicks ───────────────────────────────────────────────────

    async def sync_event_ctas(self, event_id: int) -> int:
        """Sync CTA click records for a specific event from ON24 to the database.

        Accepts either a "ctas" or "calltoactions" key in the ON24 response.

        Args:
            event_id: The ON24 event ID.

        Returns:
            Number of CTA click records inserted.
        """
        async with async_session_factory() as session:
            sync_log = await self._create_sync_log(session, "ctas", event_id)
            try:
                response = await self.client.get_event_ctas(event_id)
                ctas_data = response.get("ctas") or response.get("calltoactions", [])

                count = 0
                now = datetime.now(UTC)
                for cta in ctas_data:
                    values = {
                        "on24_event_id": event_id,
                        "attendee_email": cta.get("email", ""),
                        "cta_name": cta.get("ctaname"),
                        "cta_url": cta.get("url"),
                        "clicked_at": _parse_datetime(cta.get("clicktime")),
                        "raw_json": cta,
                        "synced_at": now,
                    }
                    stmt = pg_insert(CTAClick).values(**values).on_conflict_do_nothing()
                    await session.execute(stmt)
                    count += 1

                await self._complete_sync_log(session, sync_log, count)
                await session.commit()
                logger.info("Synced %d CTA clicks for event %d", count, event_id)
                return count

            except ON24APIError as exc:
                await self._complete_sync_log(session, sync_log, 0, str(exc))
                await session.commit()
                logger.error("Failed to sync CTAs for event %d: %s", event_id, exc)
                raise
            except Exception as exc:
                await self._complete_sync_log(session, sync_log, 0, str(exc))
                await session.commit()
                logger.error("Unexpected error syncing CTAs for event %d: %s", event_id, exc)
                raise

    # ── Engagement profile (PEP) ─────────────────────────────────────

    async def sync_engagement_profile(self, email: str) -> bool:
        """Fetch and upsert a PEP engagement profile for a single email address.

        Args:
            email: The attendee email address to look up in ON24 PEP.

        Returns:
            True if the profile was successfully synced, False otherwise.
        """
        async with async_session_factory() as session:
            sync_log = await self._create_sync_log(session, "engagement_profile")
            try:
                pep_data = await self.client.get_pep(email)

                now = datetime.now(UTC)
                values = {
                    "email": email,
                    "company": pep_data.get("company"),
                    "total_events_attended": _safe_int(pep_data.get("totaleventsattended"), 0),
                    "total_engagement_score": pep_data.get("totalengagementscore"),
                    "last_event_date": _parse_datetime(pep_data.get("lasteventdate")),
                    "pep_data": pep_data,
                    "synced_at": now,
                }

                update_values = {k: v for k, v in values.items() if k != "email"}

                stmt = (
                    pg_insert(EngagementProfile)
                    .values(**values)
                    .on_conflict_do_update(
                        index_elements=["email"],
                        set_=update_values,
                    )
                )
                await session.execute(stmt)
                await self._complete_sync_log(session, sync_log, 1)
                await session.commit()
                logger.info("Synced engagement profile for %s", email)
                return True

            except ON24APIError as exc:
                await self._complete_sync_log(session, sync_log, 0, str(exc))
                await session.commit()
                logger.error("Failed to sync engagement profile for %s: %s", email, exc)
                return False
            except Exception as exc:
                await self._complete_sync_log(session, sync_log, 0, str(exc))
                await session.commit()
                logger.error("Unexpected error syncing engagement profile for %s: %s", email, exc)
                return False

    # ── Full sync orchestrator ───────────────────────────────────────

    async def sync_all(self) -> dict[str, int]:
        """Run a full sync: events first, then attendees, registrants, polls,
        surveys, resources, and CTAs per event.

        Errors on individual events are logged and skipped so that one
        failing event does not block the rest of the sync run.

        Returns:
            Dict with counts for each synced entity type.
        """
        results: dict[str, int] = {
            "events": 0,
            "attendees": 0,
            "registrants": 0,
            "polls": 0,
            "surveys": 0,
            "resources": 0,
            "ctas": 0,
        }

        # 1. Sync events
        results["events"] = await self.sync_events()

        # 2. Fetch active event IDs from the database
        async with async_session_factory() as session:
            result = await session.execute(select(Event.on24_event_id).where(Event.is_active.is_(True)))
            event_ids: list[int] = [row[0] for row in result.fetchall()]

        # 3. Sync per-event data for each active event
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

            try:
                poll_count = await self.sync_event_polls(eid)
                results["polls"] += poll_count
            except Exception as exc:
                logger.error("Failed to sync polls for event %d: %s", eid, exc)

            try:
                survey_count = await self.sync_event_surveys(eid)
                results["surveys"] += survey_count
            except Exception as exc:
                logger.error("Failed to sync surveys for event %d: %s", eid, exc)

            try:
                resource_count = await self.sync_event_resources(eid)
                results["resources"] += resource_count
            except Exception as exc:
                logger.error("Failed to sync resources for event %d: %s", eid, exc)

            try:
                cta_count = await self.sync_event_ctas(eid)
                results["ctas"] += cta_count
            except Exception as exc:
                logger.error("Failed to sync CTAs for event %d: %s", eid, exc)

        logger.info("Full sync complete: %s", results)
        return results
