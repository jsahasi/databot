"""ON24 MCP Server — exposes the full ON24 REST API (70+ methods) plus direct-DB analytics as MCP tools.

Tools are grouped by prefix:
  events_*      — event CRUD and queries
  attendees_*   — attendee data
  registrants_* — registrant management
  leads_*       — lead / PEP data
  media_*       — Media Manager / content
  account_*     — account / client config
  admin_*       — write operations (create / update / delete)
  db_*          — direct ON24 DB analytics (read-only, asyncpg)

Write operations are prefixed with [WRITE] in their description.
"""

import json as _json
import logging

from mcp.server.fastmcp import FastMCP

from config import settings
from on24_client import ON24Client, ON24APIError
import analytics as _analytics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("on24-api", stateless_http=True)

BLOCKLIST: set[str] = settings.blocklist


def _client() -> ON24Client:
    return ON24Client(
        client_id=settings.on24_client_id,
        token_key=settings.on24_access_token_key,
        token_secret=settings.on24_access_token_secret,
        base_url=settings.on24_base_url,
    )


# ──────────────────────────────────────────────────────────────────────────────
# events_* — event queries (read)
# ──────────────────────────────────────────────────────────────────────────────

if "events_list" not in BLOCKLIST:
    @mcp.tool()
    async def events_list(
        start_date: str = "",
        end_date: str = "",
        include_inactive: bool = False,
        content_type: str = "all",
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict:
        """List ON24 webinar events with optional date filters.

        Args:
            start_date: ISO 8601 date string (YYYY-MM-DD), optional.
            end_date: ISO 8601 date string (YYYY-MM-DD), optional.
            include_inactive: If true, include inactive events.
            content_type: Filter by content type ('all', 'live', 'simuLive', 'onDemand').
            page_offset: Pagination offset (0-based page number).
            items_per_page: Number of results per page (max 100).
        """
        try:
            return await _client().list_events(
                start_date=start_date or None,
                end_date=end_date or None,
                include_inactive=include_inactive,
                content_type=content_type,
                page_offset=page_offset,
                items_per_page=items_per_page,
            )
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "events_get" not in BLOCKLIST:
    @mcp.tool()
    async def events_get(event_id: int) -> dict:
        """Get event metadata and usage summary for a single ON24 event.

        Args:
            event_id: The ON24 event ID.
        """
        try:
            return await _client().get_event(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "events_get_polls" not in BLOCKLIST:
    @mcp.tool()
    async def events_get_polls(event_id: int) -> dict:
        """Get poll questions and responses for an ON24 event.

        Args:
            event_id: The ON24 event ID.
        """
        try:
            return await _client().get_event_polls(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "events_get_surveys" not in BLOCKLIST:
    @mcp.tool()
    async def events_get_surveys(event_id: int) -> dict:
        """Get survey questions and responses for an ON24 event.

        Args:
            event_id: The ON24 event ID.
        """
        try:
            return await _client().get_event_surveys(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "events_get_resources" not in BLOCKLIST:
    @mcp.tool()
    async def events_get_resources(event_id: int) -> dict:
        """Get resources viewed during an ON24 event.

        Args:
            event_id: The ON24 event ID.
        """
        try:
            return await _client().get_event_resources(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "events_get_ctas" not in BLOCKLIST:
    @mcp.tool()
    async def events_get_ctas(event_id: int) -> dict:
        """Get call-to-action (CTA) activity for an ON24 event.

        Args:
            event_id: The ON24 event ID.
        """
        try:
            return await _client().get_event_ctas(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "events_get_group_chat" not in BLOCKLIST:
    @mcp.tool()
    async def events_get_group_chat(event_id: int) -> dict:
        """Get group chat activity for an ON24 event.

        Args:
            event_id: The ON24 event ID.
        """
        try:
            return await _client().get_event_group_chat(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "events_get_email_stats" not in BLOCKLIST:
    @mcp.tool()
    async def events_get_email_stats(event_id: int) -> dict:
        """Get email delivery statistics (opens, clicks, bounces) for an ON24 event.

        Args:
            event_id: The ON24 event ID.
        """
        try:
            return await _client().get_event_email_stats(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "events_get_certifications" not in BLOCKLIST:
    @mcp.tool()
    async def events_get_certifications(event_id: int) -> dict:
        """Get certification completions for an ON24 event.

        Args:
            event_id: The ON24 event ID.
        """
        try:
            return await _client().get_event_certifications(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "events_get_content_activity" not in BLOCKLIST:
    @mcp.tool()
    async def events_get_content_activity(event_id: int) -> dict:
        """Get Engagement Hub content activity for an ON24 event.

        Args:
            event_id: The ON24 event ID.
        """
        try:
            return await _client().get_event_content_activity(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "events_get_presenters" not in BLOCKLIST:
    @mcp.tool()
    async def events_get_presenters(event_id: int) -> dict:
        """Get presenter list for an ON24 event.

        Args:
            event_id: The ON24 event ID.
        """
        try:
            return await _client().get_event_presenters(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "events_get_calendar_reminder" not in BLOCKLIST:
    @mcp.tool()
    async def events_get_calendar_reminder(event_id: int) -> dict:
        """Get calendar reminder configuration for an ON24 event.

        Args:
            event_id: The ON24 event ID.
        """
        try:
            return await _client().get_event_calendar_reminder(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "events_get_email" not in BLOCKLIST:
    @mcp.tool()
    async def events_get_email(event_id: int) -> dict:
        """Get email notification configuration for an ON24 event.

        Args:
            event_id: The ON24 event ID.
        """
        try:
            return await _client().get_event_email(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "events_get_presenter_chat" not in BLOCKLIST:
    @mcp.tool()
    async def events_get_presenter_chat(event_id: int) -> dict:
        """Get presenter (backstage) chat logs for an ON24 event.

        Args:
            event_id: The ON24 event ID.
        """
        try:
            return await _client().get_event_presenter_chat(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "events_get_slides" not in BLOCKLIST:
    @mcp.tool()
    async def events_get_slides(event_id: int) -> dict:
        """Get slide listing for an ON24 event.

        Args:
            event_id: The ON24 event ID.
        """
        try:
            return await _client().get_event_slides(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "events_get_registration_fields" not in BLOCKLIST:
    @mcp.tool()
    async def events_get_registration_fields(event_id: int) -> dict:
        """Get custom registration fields configured for an ON24 event.

        Args:
            event_id: The ON24 event ID.
        """
        try:
            return await _client().get_registration_fields(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


# ──────────────────────────────────────────────────────────────────────────────
# attendees_* — attendee data (read)
# ──────────────────────────────────────────────────────────────────────────────

if "attendees_list_client" not in BLOCKLIST:
    @mcp.tool()
    async def attendees_list_client(
        start_date: str = "",
        end_date: str = "",
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict:
        """List attendees across all events for the client.

        Args:
            start_date: Filter by attendance date start (YYYY-MM-DD).
            end_date: Filter by attendance date end (YYYY-MM-DD).
            page_offset: Pagination offset.
            items_per_page: Results per page (max 100).
        """
        try:
            return await _client().list_client_attendees(
                start_date=start_date or None,
                end_date=end_date or None,
                page_offset=page_offset,
                items_per_page=items_per_page,
            )
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "attendees_list_event" not in BLOCKLIST:
    @mcp.tool()
    async def attendees_list_event(
        event_id: int,
        start_date: str = "",
        end_date: str = "",
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict:
        """List attendees for a specific ON24 event.

        Args:
            event_id: The ON24 event ID.
            start_date: Filter by attendance date start (YYYY-MM-DD).
            end_date: Filter by attendance date end (YYYY-MM-DD).
            page_offset: Pagination offset.
            items_per_page: Results per page (max 100).
        """
        try:
            return await _client().list_event_attendees(
                event_id=event_id,
                start_date=start_date or None,
                end_date=end_date or None,
                page_offset=page_offset,
                items_per_page=items_per_page,
            )
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "attendees_get_by_email" not in BLOCKLIST:
    @mcp.tool()
    async def attendees_get_by_email(email: str) -> dict:
        """Get the most recent attendance record for an email address.

        Args:
            email: Attendee email address.
        """
        try:
            return await _client().get_attendee_by_email(email)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "attendees_get_all_events" not in BLOCKLIST:
    @mcp.tool()
    async def attendees_get_all_events(
        email: str,
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict:
        """Get attendance records across all events for an email address.

        Args:
            email: Attendee email address.
            page_offset: Pagination offset.
            items_per_page: Results per page (max 100).
        """
        try:
            return await _client().get_attendee_all_events(
                email=email,
                page_offset=page_offset,
                items_per_page=items_per_page,
            )
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "attendees_get_viewing_sessions" not in BLOCKLIST:
    @mcp.tool()
    async def attendees_get_viewing_sessions(
        event_id: int,
        session_type: str = "all",
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict:
        """Get attendee viewing session records for an ON24 event.

        Args:
            event_id: The ON24 event ID.
            session_type: 'all', 'live', or 'archive'.
            page_offset: Pagination offset.
            items_per_page: Results per page (max 100).
        """
        try:
            return await _client().get_event_viewing_sessions(
                event_id=event_id,
                session_type=session_type,
                page_offset=page_offset,
                items_per_page=items_per_page,
            )
        except ON24APIError as e:
            return {"success": False, "error": e.message}


# ──────────────────────────────────────────────────────────────────────────────
# registrants_* — registrant management
# ──────────────────────────────────────────────────────────────────────────────

if "registrants_list_client" not in BLOCKLIST:
    @mcp.tool()
    async def registrants_list_client(
        start_date: str = "",
        end_date: str = "",
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict:
        """List registrants across all events for the client.

        Args:
            start_date: Filter by registration date start (YYYY-MM-DD).
            end_date: Filter by registration date end (YYYY-MM-DD).
            page_offset: Pagination offset.
            items_per_page: Results per page (max 100).
        """
        try:
            return await _client().list_client_registrants(
                start_date=start_date or None,
                end_date=end_date or None,
                page_offset=page_offset,
                items_per_page=items_per_page,
            )
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "registrants_list_event" not in BLOCKLIST:
    @mcp.tool()
    async def registrants_list_event(
        event_id: int,
        start_date: str = "",
        end_date: str = "",
        page_offset: int = 0,
        items_per_page: int = 100,
        noshow: bool = False,
    ) -> dict:
        """List registrants for a specific ON24 event.

        Args:
            event_id: The ON24 event ID.
            start_date: Filter by registration date start (YYYY-MM-DD).
            end_date: Filter by registration date end (YYYY-MM-DD).
            page_offset: Pagination offset.
            items_per_page: Results per page (max 100).
            noshow: If true, return only no-show registrants.
        """
        try:
            return await _client().list_event_registrants(
                event_id=event_id,
                start_date=start_date or None,
                end_date=end_date or None,
                page_offset=page_offset,
                items_per_page=items_per_page,
                noshow=noshow,
            )
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "registrants_get_by_email" not in BLOCKLIST:
    @mcp.tool()
    async def registrants_get_by_email(
        email: str,
        event_id: int = 0,
        partnerref: str = "",
    ) -> dict:
        """Get registration record(s) for an email address.

        Args:
            email: Registrant email address.
            event_id: Optionally scope to a specific event (0 = all events).
            partnerref: Optional partner reference filter.
        """
        try:
            return await _client().get_registrant_by_email(
                email=email,
                event_id=event_id if event_id else None,
                partnerref=partnerref or None,
            )
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "registrants_get_all_events" not in BLOCKLIST:
    @mcp.tool()
    async def registrants_get_all_events(
        email: str,
        exclude_subaccounts: bool = False,
        subaccounts: str = "",
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict:
        """Get all registrations across events for an email address.

        Args:
            email: Registrant email address.
            exclude_subaccounts: If true, exclude sub-account registrations.
            subaccounts: Comma-separated list of sub-account IDs to include.
            page_offset: Pagination offset.
            items_per_page: Results per page (max 100).
        """
        try:
            return await _client().get_registrant_all_events(
                email=email,
                exclude_subaccounts=exclude_subaccounts,
                subaccounts=subaccounts or None,
                page_offset=page_offset,
                items_per_page=items_per_page,
            )
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "registrants_add" not in BLOCKLIST:
    @mcp.tool()
    async def registrants_add(
        event_id: int,
        email: str,
        first_name: str,
        last_name: str,
        company: str = "",
        job_title: str = "",
    ) -> dict:
        """[WRITE] Register a person for an ON24 event.

        Args:
            event_id: The ON24 event ID.
            email: Registrant email address.
            first_name: First name.
            last_name: Last name.
            company: Company name (optional).
            job_title: Job title (optional).
        """
        try:
            resp = await _client().register_attendee(
                event_id=event_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                company=company or None,
                job_title=job_title or None,
            )
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "registrants_remove" not in BLOCKLIST:
    @mcp.tool()
    async def registrants_remove(event_id: int, email: str) -> dict:
        """[WRITE] Remove a registrant from an ON24 event.

        Args:
            event_id: The ON24 event ID.
            email: Email address of the registrant to remove.
        """
        try:
            resp = await _client().remove_registration(event_id=event_id, email=email)
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "registrants_update_event" not in BLOCKLIST:
    @mcp.tool()
    async def registrants_update_event(
        event_id: int,
        email: str,
        firstname: str = "",
        lastname: str = "",
        company: str = "",
        jobtitle: str = "",
        jobfunction: str = "",
    ) -> dict:
        """[WRITE] Update a registrant's profile at the event level.

        Args:
            event_id: The ON24 event ID.
            email: Email identifying the registrant (required).
            firstname: Updated first name (optional).
            lastname: Updated last name (optional).
            company: Updated company (optional).
            jobtitle: Updated job title (optional).
            jobfunction: Updated job function (optional).
        """
        try:
            resp = await _client().update_event_registrant(
                event_id=event_id,
                email=email,
                firstname=firstname or None,
                lastname=lastname or None,
                company=company or None,
                jobtitle=jobtitle or None,
                jobfunction=jobfunction or None,
            )
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "registrants_update_client" not in BLOCKLIST:
    @mcp.tool()
    async def registrants_update_client(
        email: str,
        firstname: str = "",
        lastname: str = "",
        new_email: str = "",
        company: str = "",
        jobtitle: str = "",
    ) -> dict:
        """[WRITE] Update a registrant's profile at the client level (all events).

        Args:
            email: Current email identifying the registrant.
            firstname: Updated first name (optional).
            lastname: Updated last name (optional).
            new_email: New email address to assign (optional).
            company: Updated company (optional).
            jobtitle: Updated job title (optional).
        """
        try:
            resp = await _client().update_client_registrant(
                email=email,
                firstname=firstname or None,
                lastname=lastname or None,
                new_email=new_email or None,
                company=company or None,
                jobtitle=jobtitle or None,
            )
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "registrants_forget" not in BLOCKLIST:
    @mcp.tool()
    async def registrants_forget(email: str, event_id: int = 0) -> dict:
        """[WRITE] GDPR: Nullify all PII for one or more registrants. IRREVERSIBLE.

        Args:
            email: Email address(es) to forget. Comma-separate multiple addresses.
            event_id: Scope to a specific event (0 = all events).
        """
        try:
            resp = await _client().forget_registrant(
                email=email,
                event_id=event_id if event_id else None,
            )
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "registrants_forget_all_event" not in BLOCKLIST:
    @mcp.tool()
    async def registrants_forget_all_event(event_id: int) -> dict:
        """[WRITE] GDPR: Nullify PII for ALL registrants in an event. IRREVERSIBLE.

        Args:
            event_id: The ON24 event ID whose registrants will be anonymised.
        """
        try:
            resp = await _client().forget_all_event_registrants(event_id=event_id)
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "registrants_forget_all_workspace" not in BLOCKLIST:
    @mcp.tool()
    async def registrants_forget_all_workspace() -> dict:
        """[WRITE] GDPR: Nullify PII for ALL registrants across the entire workspace. EXTREMELY DESTRUCTIVE — use with extreme caution."""
        try:
            resp = await _client().forget_all_workspace_registrants()
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


# ──────────────────────────────────────────────────────────────────────────────
# leads_* — lead / PEP data (read)
# ──────────────────────────────────────────────────────────────────────────────

if "leads_list" not in BLOCKLIST:
    @mcp.tool()
    async def leads_list(
        start_date: str = "",
        end_date: str = "",
        page_offset: int = 0,
        items_per_page: int = 50,
    ) -> dict:
        """List leads for the client.

        Args:
            start_date: Filter by lead date start (YYYY-MM-DD).
            end_date: Filter by lead date end (YYYY-MM-DD).
            page_offset: Pagination offset.
            items_per_page: Results per page (max 50).
        """
        try:
            return await _client().list_client_leads(
                start_date=start_date or None,
                end_date=end_date or None,
                page_offset=page_offset,
                items_per_page=items_per_page,
            )
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "leads_get_pep" not in BLOCKLIST:
    @mcp.tool()
    async def leads_get_pep(email: str) -> dict:
        """Get the Prospect Engagement Profile (PEP) for an email address.

        Args:
            email: The prospect's email address.
        """
        try:
            return await _client().get_pep(email)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "leads_get_engaged_accounts" not in BLOCKLIST:
    @mcp.tool()
    async def leads_get_engaged_accounts() -> dict:
        """Get the top engaged accounts from the last 90 days (max 100 accounts)."""
        try:
            return await _client().get_engaged_accounts()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


# ──────────────────────────────────────────────────────────────────────────────
# media_* — Media Manager / Engagement Hub content
# ──────────────────────────────────────────────────────────────────────────────

if "media_list" not in BLOCKLIST:
    @mcp.tool()
    async def media_list(
        start_date: str = "",
        end_date: str = "",
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict:
        """List Media Manager derivative content items.

        Args:
            start_date: Filter by creation date start (YYYY-MM-DD).
            end_date: Filter by creation date end (YYYY-MM-DD).
            page_offset: Pagination offset.
            items_per_page: Results per page (max 100).
        """
        try:
            return await _client().list_media_manager_content(
                start_date=start_date or None,
                end_date=end_date or None,
                page_offset=page_offset,
                items_per_page=items_per_page,
            )
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "media_get" not in BLOCKLIST:
    @mcp.tool()
    async def media_get(media_id: int) -> dict:
        """Get a single Media Manager derivative content item.

        Args:
            media_id: The media item ID.
        """
        try:
            return await _client().get_media_manager_content(media_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "media_get_ehub_content" not in BLOCKLIST:
    @mcp.tool()
    async def media_get_ehub_content(gateway_id: int) -> dict:
        """Get content listing for an Engagement Hub gateway.

        Args:
            gateway_id: The Engagement Hub gateway ID.
        """
        try:
            return await _client().get_ehub_content(gateway_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "media_upload_document" not in BLOCKLIST:
    @mcp.tool()
    async def media_upload_document(
        file_path: str,
        title: str = "",
        media_id: str = "",
    ) -> dict:
        """[WRITE] Upload a document file to ON24 Media Manager.

        Reads the file from the local filesystem and uploads it as multipart/form-data.

        Args:
            file_path: Absolute path to the document file to upload.
            title: Optional display title for the document.
            media_id: Optional existing media ID to update (leave empty to create new).
        """
        import mimetypes
        import os
        try:
            if not os.path.isfile(file_path):
                return {"success": False, "error": f"File not found: {file_path}"}
            filename = os.path.basename(file_path)
            mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            with open(file_path, "rb") as fh:
                file_bytes = fh.read()
            file_tuple = (filename, file_bytes, mime)
            metadata: dict | None = None
            if title or media_id:
                metadata = {}
                if title:
                    metadata["title"] = title
                if media_id:
                    metadata["id"] = media_id
            resp = await _client().upload_document(file=file_tuple, metadata=metadata)
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}
        except OSError as e:
            return {"success": False, "error": str(e)}


if "media_upload_video" not in BLOCKLIST:
    @mcp.tool()
    async def media_upload_video(
        file_path: str,
        title: str = "",
        media_id: str = "",
    ) -> dict:
        """[WRITE] Upload a video file to ON24 Media Manager.

        Reads the video from the local filesystem and uploads it as multipart/form-data.

        Args:
            file_path: Absolute path to the video file to upload.
            title: Optional display title for the video.
            media_id: Optional existing media ID to update (leave empty to create new).
        """
        import mimetypes
        import os
        try:
            if not os.path.isfile(file_path):
                return {"success": False, "error": f"File not found: {file_path}"}
            filename = os.path.basename(file_path)
            mime = mimetypes.guess_type(filename)[0] or "video/mp4"
            with open(file_path, "rb") as fh:
                file_bytes = fh.read()
            file_tuple = (filename, file_bytes, mime)
            metadata: dict | None = None
            if title or media_id:
                metadata = {}
                if title:
                    metadata["title"] = title
                if media_id:
                    metadata["id"] = media_id
            resp = await _client().upload_video(file=file_tuple, metadata=metadata)
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}
        except OSError as e:
            return {"success": False, "error": str(e)}


if "media_upload_slides" not in BLOCKLIST:
    @mcp.tool()
    async def media_upload_slides(event_id: int, file_path: str) -> dict:
        """[WRITE] Upload a PowerPoint file as slides for an ON24 event.

        Args:
            event_id: The ON24 event ID.
            file_path: Absolute path to the .pptx or .ppt file to upload.
        """
        import mimetypes
        import os
        try:
            if not os.path.isfile(file_path):
                return {"success": False, "error": f"File not found: {file_path}"}
            filename = os.path.basename(file_path)
            mime = mimetypes.guess_type(filename)[0] or "application/vnd.ms-powerpoint"
            with open(file_path, "rb") as fh:
                file_bytes = fh.read()
            file_tuple = (filename, file_bytes, mime)
            resp = await _client().upload_slides(event_id=event_id, file=file_tuple)
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}
        except OSError as e:
            return {"success": False, "error": str(e)}


if "media_upload_related_content" not in BLOCKLIST:
    @mcp.tool()
    async def media_upload_related_content(
        event_id: int,
        matchname: str,
        name: str,
        content_type: str,
        url: str = "",
        file_path: str = "",
    ) -> dict:
        """[WRITE] Upload or link related content for an ON24 event.

        Args:
            event_id: The ON24 event ID.
            matchname: Internal match name for the content item.
            name: Display name shown to attendees.
            content_type: 'Resource' for file uploads, 'URL' for link content.
            url: URL string for URL-type content (leave empty for file uploads).
            file_path: Local path to file for Resource uploads (leave empty for URLs).
        """
        import mimetypes
        import os
        try:
            file_tuple = None
            if file_path:
                if not os.path.isfile(file_path):
                    return {"success": False, "error": f"File not found: {file_path}"}
                filename = os.path.basename(file_path)
                mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                with open(file_path, "rb") as fh:
                    file_bytes = fh.read()
                file_tuple = (filename, file_bytes, mime)
            resp = await _client().upload_related_content(
                event_id=event_id,
                matchname=matchname,
                name=name,
                content_type=content_type,
                file=file_tuple,
                url=url or None,
            )
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}
        except OSError as e:
            return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────────────────────
# account_* — account / client config (read)
# ──────────────────────────────────────────────────────────────────────────────

if "account_list_sub_clients" not in BLOCKLIST:
    @mcp.tool()
    async def account_list_sub_clients() -> dict:
        """List sub-client accounts under the configured root client."""
        try:
            return await _client().list_sub_clients()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "account_list_users" not in BLOCKLIST:
    @mcp.tool()
    async def account_list_users() -> dict:
        """List platform users (admin accounts) for the client."""
        try:
            return await _client().list_users()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "account_list_presenters" not in BLOCKLIST:
    @mcp.tool()
    async def account_list_presenters() -> dict:
        """List all presenters configured in the client account."""
        try:
            return await _client().list_client_presenters()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "account_get_survey_library" not in BLOCKLIST:
    @mcp.tool()
    async def account_get_survey_library() -> dict:
        """Get the survey question library for the client account."""
        try:
            return await _client().get_survey_library()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "account_get_custom_tags" not in BLOCKLIST:
    @mcp.tool()
    async def account_get_custom_tags() -> dict:
        """Get custom account tags configured for the client."""
        try:
            return await _client().get_custom_account_tags()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "account_get_managers" not in BLOCKLIST:
    @mcp.tool()
    async def account_get_managers() -> dict:
        """Get account manager contacts for the client."""
        try:
            return await _client().get_account_managers()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "account_get_event_managers" not in BLOCKLIST:
    @mcp.tool()
    async def account_get_event_managers() -> dict:
        """Get event manager contacts for the client."""
        try:
            return await _client().get_event_managers()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "account_get_event_profiles" not in BLOCKLIST:
    @mcp.tool()
    async def account_get_event_profiles() -> dict:
        """Get event profile templates configured for the client."""
        try:
            return await _client().get_event_profiles()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "account_get_event_types" not in BLOCKLIST:
    @mcp.tool()
    async def account_get_event_types() -> dict:
        """Get available ON24 event type codes."""
        try:
            return await _client().get_event_types()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "account_get_languages" not in BLOCKLIST:
    @mcp.tool()
    async def account_get_languages() -> dict:
        """Get available language codes for ON24 events."""
        try:
            return await _client().get_languages()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "account_get_timezones" not in BLOCKLIST:
    @mcp.tool()
    async def account_get_timezones() -> dict:
        """Get available timezone codes for ON24 events."""
        try:
            return await _client().get_timezones()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "account_get_replacement_tokens" not in BLOCKLIST:
    @mcp.tool()
    async def account_get_replacement_tokens(context: str = "") -> dict:
        """Get dynamic replacement tokens used in email templates.

        Args:
            context: Optional context filter (e.g. 'email', 'registration').
        """
        try:
            return await _client().get_replacement_tokens(context=context or None)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "account_get_sales_reps" not in BLOCKLIST:
    @mcp.tool()
    async def account_get_sales_reps() -> dict:
        """Get sales representative contact list."""
        try:
            return await _client().get_sales_reps()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "account_get_signal_contacts" not in BLOCKLIST:
    @mcp.tool()
    async def account_get_signal_contacts() -> dict:
        """Get signal contact list."""
        try:
            return await _client().get_signal_contacts()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "account_get_technical_reps" not in BLOCKLIST:
    @mcp.tool()
    async def account_get_technical_reps() -> dict:
        """Get technical representative contact list."""
        try:
            return await _client().get_technical_reps()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "account_get_realtime_questions" not in BLOCKLIST:
    @mcp.tool()
    async def account_get_realtime_questions(
        email_filter: str = "",
        start_date: str = "",
        end_date: str = "",
        exclude_subaccounts: bool = False,
    ) -> dict:
        """Get real-time user questions submitted in the last 5 minutes across live events.

        Args:
            email_filter: Optional email to filter questions by submitter.
            start_date: Optional start date filter (YYYY-MM-DD).
            end_date: Optional end date filter (YYYY-MM-DD).
            exclude_subaccounts: If true, exclude sub-account events.
        """
        try:
            return await _client().get_realtime_user_questions(
                exclude_subaccounts=exclude_subaccounts,
                email_filter=email_filter or None,
                start_date=start_date or None,
                end_date=end_date or None,
            )
        except ON24APIError as e:
            return {"success": False, "error": e.message}


# ──────────────────────────────────────────────────────────────────────────────
# admin_* — write operations (create / update / delete events and content)
# ──────────────────────────────────────────────────────────────────────────────

if "admin_create_event" not in BLOCKLIST:
    @mcp.tool()
    async def admin_create_event(
        title: str,
        event_type: str,
        start_time: str,
        end_time: str,
        description: str = "",
    ) -> dict:
        """[WRITE] Create a new ON24 event (JSON body).

        Args:
            title: Event display title.
            event_type: ON24 event type code (use account_get_event_types for valid values).
            start_time: Event start time in ISO 8601 format.
            end_time: Event end time in ISO 8601 format.
            description: Optional event description.
        """
        try:
            resp = await _client().create_event(
                title=title,
                event_type=event_type,
                start_time=start_time,
                end_time=end_time,
                description=description or None,
            )
            event_id = resp.get("eventId") or resp.get("id")
            return {"success": True, "on24_event_id": event_id, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "admin_update_event" not in BLOCKLIST:
    @mcp.tool()
    async def admin_update_event(
        event_id: int,
        title: str = "",
        description: str = "",
        start_time: str = "",
        end_time: str = "",
    ) -> dict:
        """[WRITE] Update fields on an existing ON24 event (JSON PATCH). Only pass fields to change.

        Args:
            event_id: The ON24 event ID to update.
            title: New event title (optional).
            description: New event description (optional).
            start_time: New start time in ISO 8601 (optional).
            end_time: New end time in ISO 8601 (optional).
        """
        try:
            resp = await _client().update_event(
                event_id=event_id,
                title=title or None,
                description=description or None,
                start_time=start_time or None,
                end_time=end_time or None,
            )
            return {"success": True, "on24_event_id": event_id, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "admin_create_webinar" not in BLOCKLIST:
    @mcp.tool()
    async def admin_create_webinar(
        title: str,
        live_start: str,
        live_duration: int,
        event_type: str,
        language_cd: str,
        time_zone: str,
        event_abstract: str = "",
        campaign_code: str = "",
        country_cd: str = "",
        tag_campaign: str = "",
        custom_account_tag: str = "",
        archive_available: str = "",
        promotional_summary: str = "",
        testevent: str = "",
        hybrid: str = "",
        venue: str = "",
        address: str = "",
    ) -> dict:
        """[WRITE] Create a webinar using form-urlencoded parameters. Required: title, live_start, live_duration, event_type, language_cd, time_zone.

        Args:
            title: Webinar title.
            live_start: Start datetime string (e.g. '2026-06-01 14:00:00').
            live_duration: Duration in minutes.
            event_type: Event type code.
            language_cd: Language code (use account_get_languages).
            time_zone: Timezone code (use account_get_timezones).
            event_abstract: Optional event description/abstract.
            campaign_code: Optional campaign code.
            country_cd: Optional country code.
            tag_campaign: Optional tag campaign value.
            custom_account_tag: Optional custom account tag.
            archive_available: Optional archive availability flag ('Y'/'N').
            promotional_summary: Optional promotional summary text.
            testevent: Optional test event flag.
            hybrid: Optional hybrid event flag.
            venue: Optional venue name for hybrid events.
            address: Optional venue address for hybrid events.
        """
        try:
            resp = await _client().create_webinar(
                title=title,
                live_start=live_start,
                live_duration=live_duration,
                event_type=event_type,
                language_cd=language_cd,
                time_zone=time_zone,
                event_abstract=event_abstract or None,
                campaign_code=campaign_code or None,
                country_cd=country_cd or None,
                tag_campaign=tag_campaign or None,
                custom_account_tag=custom_account_tag or None,
                archive_available=archive_available or None,
                promotional_summary=promotional_summary or None,
                testevent=testevent or None,
                hybrid=hybrid or None,
                venue=venue or None,
                address=address or None,
            )
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "admin_update_webinar" not in BLOCKLIST:
    @mcp.tool()
    async def admin_update_webinar(
        event_id: int,
        title: str = "",
        live_start: str = "",
        live_duration: int = 0,
        event_type: str = "",
        language_cd: str = "",
        country_cd: str = "",
        time_zone: str = "",
        tag_campaign: str = "",
        campaign_code: str = "",
        archive_available: str = "",
        promotional_summary: str = "",
        custom_account_tag: str = "",
        enable_registration: str = "",
    ) -> dict:
        """[WRITE] Update a webinar's fields (partial PUT — only pass fields to change).

        Args:
            event_id: The ON24 event ID to update.
            title: New title (optional).
            live_start: New start datetime string (optional).
            live_duration: New duration in minutes (0 = skip).
            event_type: New event type code (optional).
            language_cd: New language code (optional).
            country_cd: New country code (optional).
            time_zone: New timezone code (optional).
            tag_campaign: Updated tag campaign value (optional).
            campaign_code: Updated campaign code (optional).
            archive_available: Archive flag 'Y'/'N' (optional).
            promotional_summary: Updated promotional summary (optional).
            custom_account_tag: Updated custom account tag (optional).
            enable_registration: Enable/disable registration 'Y'/'N' (optional).
        """
        try:
            resp = await _client().update_webinar(
                event_id=event_id,
                title=title or None,
                live_start=live_start or None,
                live_duration=live_duration if live_duration else None,
                event_type=event_type or None,
                language_cd=language_cd or None,
                country_cd=country_cd or None,
                time_zone=time_zone or None,
                tag_campaign=tag_campaign or None,
                campaign_code=campaign_code or None,
                archive_available=archive_available or None,
                promotional_summary=promotional_summary or None,
                custom_account_tag=custom_account_tag or None,
                enable_registration=enable_registration or None,
            )
            return {"success": True, "on24_event_id": event_id, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "admin_edit_webinar" not in BLOCKLIST:
    @mcp.tool()
    async def admin_edit_webinar(
        event_id: int,
        title: str,
        live_start: str,
        live_duration: int,
        event_type: str,
        language_cd: str,
        campaign_code: str = "",
        country_cd: str = "",
    ) -> dict:
        """[WRITE] Full PUT replacement of a webinar. ALL required fields must be provided.

        Args:
            event_id: The ON24 event ID.
            title: Webinar title (required).
            live_start: Start datetime string (required).
            live_duration: Duration in minutes (required).
            event_type: Event type code (required).
            language_cd: Language code (required).
            campaign_code: Optional campaign code.
            country_cd: Optional country code.
        """
        try:
            resp = await _client().edit_webinar(
                event_id=event_id,
                title=title,
                live_start=live_start,
                live_duration=live_duration,
                event_type=event_type,
                language_cd=language_cd,
                campaign_code=campaign_code or None,
                country_cd=country_cd or None,
            )
            return {"success": True, "on24_event_id": event_id, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "admin_delete_webinar" not in BLOCKLIST:
    @mcp.tool()
    async def admin_delete_webinar(event_id: int) -> dict:
        """[WRITE] Permanently delete an ON24 webinar. IRREVERSIBLE.

        Args:
            event_id: The ON24 event ID to delete.
        """
        try:
            resp = await _client().delete_webinar(event_id=event_id)
            return {"success": True, "on24_event_id": event_id, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "admin_copy_webinar" not in BLOCKLIST:
    @mcp.tool()
    async def admin_copy_webinar(
        source_event_id: int,
        live_start: str,
        live_duration: int = 0,
        title: str = "",
        language_cd: str = "",
        time_zone: str = "",
        campaign_code: str = "",
        tag_campaign: str = "",
        custom_account_tag: str = "",
        archive_available: str = "",
        testevent: str = "",
        hybrid: str = "",
        venue: str = "",
        address: str = "",
        promotional_summary: str = "",
        country_cd: str = "",
    ) -> dict:
        """[WRITE] Copy an existing ON24 webinar to a new date/time.

        Args:
            source_event_id: The ON24 event ID to copy from.
            live_start: New start datetime for the copy (required).
            live_duration: New duration in minutes (0 = inherit from source).
            title: New title for the copy (empty = inherit from source).
            language_cd: Language code override (empty = inherit).
            time_zone: Timezone code override (empty = inherit).
            campaign_code: Campaign code override.
            tag_campaign: Tag campaign override.
            custom_account_tag: Custom account tag override.
            archive_available: Archive flag 'Y'/'N'.
            testevent: Test event flag.
            hybrid: Hybrid event flag.
            venue: Venue name for hybrid events.
            address: Venue address for hybrid events.
            promotional_summary: Promotional summary override.
            country_cd: Country code override.
        """
        try:
            resp = await _client().copy_webinar(
                source_event_id=source_event_id,
                live_start=live_start,
                live_duration=live_duration if live_duration else None,
                title=title or None,
                language_cd=language_cd or None,
                time_zone=time_zone or None,
                campaign_code=campaign_code or None,
                tag_campaign=tag_campaign or None,
                custom_account_tag=custom_account_tag or None,
                archive_available=archive_available or None,
                testevent=testevent or None,
                hybrid=hybrid or None,
                venue=venue or None,
                address=address or None,
                promotional_summary=promotional_summary or None,
                country_cd=country_cd or None,
            )
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "admin_create_survey_questions" not in BLOCKLIST:
    @mcp.tool()
    async def admin_create_survey_questions(
        event_id: int, survey_questions_json: str
    ) -> dict:
        """[WRITE] Create survey questions for an ON24 event.

        Args:
            event_id: The ON24 event ID.
            survey_questions_json: JSON array string of question objects. Each object should have
                fields like 'questionText', 'questionType', 'answers' per ON24 API spec.
        """
        try:
            questions = _json.loads(survey_questions_json)
            resp = await _client().create_survey_questions(
                event_id=event_id, survey_questions=questions
            )
            return {"success": True, "response": resp}
        except _json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {e}"}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "admin_create_speaker_bio" not in BLOCKLIST:
    @mcp.tool()
    async def admin_create_speaker_bio(
        event_id: int,
        metadata_json: str,
        file_path: str = "",
    ) -> dict:
        """[WRITE] Create or update a speaker bio for an ON24 event.

        Args:
            event_id: The ON24 event ID.
            metadata_json: JSON object string containing speaker bio fields
                (e.g. name, title, company, bio text per ON24 API spec).
            file_path: Optional absolute path to a speaker headshot image file.
        """
        import mimetypes
        import os
        try:
            metadata = _json.loads(metadata_json)
            file_tuple = None
            if file_path:
                if not os.path.isfile(file_path):
                    return {"success": False, "error": f"File not found: {file_path}"}
                filename = os.path.basename(file_path)
                mime = mimetypes.guess_type(filename)[0] or "image/jpeg"
                with open(file_path, "rb") as fh:
                    file_bytes = fh.read()
                file_tuple = (filename, file_bytes, mime)
            resp = await _client().create_speaker_bio(
                event_id=event_id, metadata=metadata, file=file_tuple
            )
            return {"success": True, "response": resp}
        except _json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {e}"}
        except ON24APIError as e:
            return {"success": False, "error": e.message}
        except OSError as e:
            return {"success": False, "error": str(e)}


if "admin_delete_speaker_bios" not in BLOCKLIST:
    @mcp.tool()
    async def admin_delete_speaker_bios(event_id: int) -> dict:
        """[WRITE] Delete all speaker bios for an ON24 event. IRREVERSIBLE.

        Args:
            event_id: The ON24 event ID.
        """
        try:
            resp = await _client().delete_speaker_bios(event_id=event_id)
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "admin_delete_vtt_files" not in BLOCKLIST:
    @mcp.tool()
    async def admin_delete_vtt_files(event_id: int) -> dict:
        """[WRITE] Delete all VTT caption/transcript files for an ON24 event. IRREVERSIBLE.

        Args:
            event_id: The ON24 event ID.
        """
        try:
            resp = await _client().delete_vtt_files(event_id=event_id)
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "admin_update_calendar_reminder" not in BLOCKLIST:
    @mcp.tool()
    async def admin_update_calendar_reminder(
        event_id: int,
        reminder: str = "",
        subject: str = "",
        location: str = "",
        body: str = "",
    ) -> dict:
        """[WRITE] Update the calendar reminder email for an ON24 event.

        Args:
            event_id: The ON24 event ID.
            reminder: Reminder timing setting (optional).
            subject: Email subject line (optional).
            location: Meeting location text (optional).
            body: Email body content (optional).
        """
        try:
            resp = await _client().update_calendar_reminder(
                event_id=event_id,
                reminder=reminder or None,
                subject=subject or None,
                location=location or None,
                body=body or None,
            )
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "admin_update_email_notification" not in BLOCKLIST:
    @mcp.tool()
    async def admin_update_email_notification(
        event_id: int,
        email_id: int,
        activated: str = "",
        whentosend: str = "",
        goodafter: str = "",
        fromlabel: str = "",
        replyto: str = "",
        subject: str = "",
        body: str = "",
    ) -> dict:
        """[WRITE] Update an email notification for an ON24 event.

        Args:
            event_id: The ON24 event ID.
            email_id: The email notification ID to update.
            activated: Activation status ('Y'/'N') (optional).
            whentosend: When-to-send value (optional).
            goodafter: Send-after datetime string (optional).
            fromlabel: From display label (optional).
            replyto: Reply-to email address (optional).
            subject: Email subject line (optional).
            body: Email HTML body content (optional).
        """
        try:
            resp = await _client().update_email_notification(
                event_id=event_id,
                email_id=email_id,
                activated=activated or None,
                whentosend=whentosend or None,
                goodafter=goodafter or None,
                fromlabel=fromlabel or None,
                replyto=replyto or None,
                subject=subject or None,
                body=body or None,
            )
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "admin_update_text_with_banner" not in BLOCKLIST:
    @mcp.tool()
    async def admin_update_text_with_banner(event_id: int, metadata: str) -> dict:
        """[WRITE] Update the text-with-banner widget for an ON24 event.

        Args:
            event_id: The ON24 event ID.
            metadata: JSON string containing widget configuration per ON24 API spec.
        """
        try:
            resp = await _client().update_text_with_banner(
                event_id=event_id, metadata=metadata
            )
            return {"success": True, "response": resp}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


# ──────────────────────────────────────────────────────────────────────────────
# db_* — direct ON24 DB analytics (read-only, asyncpg)
# These tools query the ON24 master database directly.
# They require ON24_DB_URL and ON24_CLIENT_ID env vars.
# Tenant safety: client_id is always sourced from config, never from callers.
# ──────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def db_list_events(
    limit: int = 20,
    offset: int = 0,
    event_type: str = "",
    is_active: str = "",
    search: str = "",
    past_only: bool = False,
    months: int = 0,
) -> dict:
    """Search and filter ON24 events from the analytics database.

    Args:
        limit: Max results (1-100, default 20).
        offset: Pagination offset (default 0).
        event_type: Filter by event type e.g. 'WEBINAR' (empty = all).
        is_active: Filter by active flag 'Y' or 'N' (empty = all).
        search: Search in event title/description.
        past_only: If true, only return events that have already started.
        months: Limit to last N months (0 = no date filter, max 24).
    """
    try:
        results = await _analytics.list_events(
            limit=limit,
            offset=offset,
            event_type=event_type or None,
            is_active=is_active or None,
            search=search or None,
            past_only=past_only,
            months=months if months > 0 else None,
        )
        return {"success": True, "count": len(results), "events": results}
    except Exception as e:
        logger.exception("db_list_events failed")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def db_get_event_detail(event_id: int) -> dict:
    """Get full details for a single ON24 event by its event_id.

    Verifies the event belongs to the configured tenant before returning data.
    Returns all event columns including description (title), goodafter (start),
    goodtill (end), event_type, is_active.
    """
    try:
        result = await _analytics.get_event_detail(event_id)
        if result is None:
            return {"success": False, "error": f"Event {event_id} not found or not in tenant"}
        return {"success": True, "event": result}
    except Exception as e:
        logger.exception("db_get_event_detail failed")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def db_get_event_kpis(event_id: int) -> dict:
    """Get key performance indicators for a single ON24 event.

    Returns: total_registrants, total_attendees, avg_engagement (0-100),
    avg_live_minutes, conversion_rate (%), and ai_content count if AI-ACE
    content was generated for this event.
    """
    try:
        result = await _analytics.get_event_kpis(event_id)
        return {"success": True, "kpis": result}
    except Exception as e:
        logger.exception("db_get_event_kpis failed")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def db_get_top_events(
    limit: int = 10,
    sort_by: str = "attendees",
    months: int = 1,
) -> dict:
    """Get top ON24 events ranked by attendance or engagement.

    Args:
        limit: Max events to return (1-50, default 10).
        sort_by: 'attendees' (default) or 'engagement'.
        months: Look-back window in months (default 1, max 24).

    Returns events with total_attendees, total_registrants, avg_engagement,
    event_id, description (title), goodafter (date).
    """
    try:
        results = await _analytics.get_top_events(limit=limit, sort_by=sort_by, months=months)
        return {"success": True, "count": len(results), "events": results}
    except Exception as e:
        logger.exception("db_get_top_events failed")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def db_get_attendance_trends(months: int = 12) -> dict:
    """Get monthly attendance and registration trends.

    Args:
        months: Look-back window in months (default 12, max 24).

    Returns a time-series list ordered by month (ascending) with:
    period (ISO date), event_count, total_registrants, total_attendees,
    avg_engagement.
    """
    try:
        results = await _analytics.get_attendance_trends(months=months)
        return {"success": True, "count": len(results), "trends": results}
    except Exception as e:
        logger.exception("db_get_attendance_trends failed")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def db_get_audience_companies(
    limit: int = 20,
    months: int = 1,
    event_id: int = 0,
) -> dict:
    """Get top companies by attendance count.

    Args:
        limit: Max companies to return (1-100, default 20).
        months: Look-back window in months (default 1, max 24). Ignored if event_id set.
        event_id: If non-zero, scope results to a single event.

    Returns companies with attendee_count, avg_engagement, event_count.
    """
    try:
        results = await _analytics.get_audience_companies(
            limit=limit,
            months=months,
            event_id=event_id if event_id > 0 else None,
        )
        return {"success": True, "count": len(results), "companies": results}
    except Exception as e:
        logger.exception("db_get_audience_companies failed")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def db_get_polls(event_id: int) -> dict:
    """Get poll questions and answer distributions for an ON24 event (from analytics DB).

    Args:
        event_id: The ON24 event ID to query polls for.

    Returns list of questions. Multiple-choice questions include an 'answers'
    array with answer_cd, answer_text, response_count. Open-text questions
    include response_count and sample_answers.
    """
    try:
        results = await _analytics.get_polls(event_id)
        return {"success": True, "count": len(results), "polls": results}
    except Exception as e:
        logger.exception("db_get_polls failed")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def db_get_ai_content(
    content_type: str = "",
    limit: int = 3,
) -> dict:
    """Get AI-ACE generated content articles from ON24 Media Manager.

    Args:
        content_type: One of BLOG, EBOOK, FAQ, KEYTAKEAWAYS, FOLLOWUPEMAIL,
                      SOCIALMEDIA, TRANSCRIPT — or empty for all types.
        limit: Max articles to return (1-10, default 3).

    Returns deduplicated articles (longest version per event+type) with
    content_type, title, content (truncated at 50k chars), event_id,
    event_title, created_at.
    """
    try:
        results = await _analytics.get_ai_content(
            content_type=content_type or None,
            limit=limit,
        )
        return {"success": True, "count": len(results), "articles": results}
    except Exception as e:
        logger.exception("db_get_ai_content failed")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    logger.info(f"Starting ON24 MCP server. Blocklist: {BLOCKLIST or 'none'}")
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = 8001
    mcp.run(transport="streamable-http")
