"""ON24 MCP Server — exposes ON24 REST API write operations as MCP tools."""
import logging
from mcp.server.fastmcp import FastMCP
from config import settings
from on24_client import ON24Client, ON24APIError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("on24-api", stateless_http=True)

BLOCKLIST = settings.blocklist


def _client() -> ON24Client:
    return ON24Client(
        client_id=settings.on24_client_id,
        token_key=settings.on24_access_token_key,
        token_secret=settings.on24_access_token_secret,
        base_url=settings.on24_base_url,
    )


if "create_event" not in BLOCKLIST:
    @mcp.tool()
    async def create_event(title: str, event_type: str, start_time: str, end_time: str, description: str = "") -> dict:
        """Create a new ON24 event. start_time/end_time in ISO 8601."""
        try:
            resp = await _client().create_event(title, event_type, start_time, end_time, description or None)
            eid = resp.get("eventId") or resp.get("id")
            return {"success": True, "on24_event_id": eid, "message": f"Event '{title}' created."}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "update_event" not in BLOCKLIST:
    @mcp.tool()
    async def update_event(on24_event_id: int, title: str = "", description: str = "", start_time: str = "", end_time: str = "") -> dict:
        """Update fields on an existing ON24 event. Pass only fields to change."""
        try:
            await _client().update_event(
                on24_event_id,
                title=title or None,
                description=description or None,
                start_time=start_time or None,
                end_time=end_time or None,
            )
            return {"success": True, "on24_event_id": on24_event_id, "message": f"Event {on24_event_id} updated."}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "add_registrant" not in BLOCKLIST:
    @mcp.tool()
    async def add_registrant(on24_event_id: int, email: str, first_name: str, last_name: str, company: str = "", job_title: str = "") -> dict:
        """Register a person for an ON24 event."""
        try:
            await _client().register_attendee(on24_event_id, email, first_name, last_name, company or None, job_title or None)
            return {"success": True, "message": f"{first_name} {last_name} ({email}) registered for event {on24_event_id}."}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "remove_registrant" not in BLOCKLIST:
    @mcp.tool()
    async def remove_registrant(on24_event_id: int, email: str) -> dict:
        """Remove a registrant from an ON24 event by email."""
        try:
            await _client().remove_registration(on24_event_id, email)
            return {"success": True, "message": f"Registration for {email} removed from event {on24_event_id}."}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


# ── Read Tools ──

if "list_events" not in BLOCKLIST:
    @mcp.tool()
    async def list_events(start_date: str = "", end_date: str = "", items_per_page: int = 100, page_offset: int = 0) -> dict:
        """List events for the client with optional date filters."""
        try:
            return await _client().list_events(start_date or None, end_date or None, items_per_page, page_offset)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event" not in BLOCKLIST:
    @mcp.tool()
    async def get_event(event_id: int) -> dict:
        """Get event metadata and usage summary."""
        try:
            return await _client().get_event(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "list_event_attendees" not in BLOCKLIST:
    @mcp.tool()
    async def list_event_attendees(event_id: int, items_per_page: int = 100, page_offset: int = 0) -> dict:
        """List attendees for a specific event."""
        try:
            return await _client().list_event_attendees(event_id, items_per_page, page_offset)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "list_event_registrants" not in BLOCKLIST:
    @mcp.tool()
    async def list_event_registrants(event_id: int, items_per_page: int = 100, page_offset: int = 0) -> dict:
        """List registrants for a specific event."""
        try:
            return await _client().list_event_registrants(event_id, items_per_page, page_offset)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "list_client_attendees" not in BLOCKLIST:
    @mcp.tool()
    async def list_client_attendees(start_date: str = "", end_date: str = "", items_per_page: int = 100, page_offset: int = 0) -> dict:
        """List attendees across all events."""
        try:
            return await _client().list_client_attendees(start_date or None, end_date or None, items_per_page, page_offset)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "list_client_registrants" not in BLOCKLIST:
    @mcp.tool()
    async def list_client_registrants(start_date: str = "", end_date: str = "", items_per_page: int = 100, page_offset: int = 0) -> dict:
        """List registrants across all events."""
        try:
            return await _client().list_client_registrants(start_date or None, end_date or None, items_per_page, page_offset)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "list_client_leads" not in BLOCKLIST:
    @mcp.tool()
    async def list_client_leads(start_date: str = "", end_date: str = "", items_per_page: int = 50, page_offset: int = 0) -> dict:
        """List leads across all events."""
        try:
            return await _client().list_client_leads(start_date or None, end_date or None, items_per_page, page_offset)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event_polls" not in BLOCKLIST:
    @mcp.tool()
    async def get_event_polls(event_id: int) -> dict:
        """Get poll questions and responses for an event."""
        try:
            return await _client().get_event_polls(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event_surveys" not in BLOCKLIST:
    @mcp.tool()
    async def get_event_surveys(event_id: int) -> dict:
        """Get survey questions and responses for an event."""
        try:
            return await _client().get_event_surveys(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event_resources" not in BLOCKLIST:
    @mcp.tool()
    async def get_event_resources(event_id: int) -> dict:
        """Get resources viewed for an event."""
        try:
            return await _client().get_event_resources(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event_types" not in BLOCKLIST:
    @mcp.tool()
    async def get_event_types() -> dict:
        """Get available event types."""
        try:
            return await _client().get_event_types()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_timezones" not in BLOCKLIST:
    @mcp.tool()
    async def get_timezones() -> dict:
        """Get available timezone codes."""
        try:
            return await _client().get_timezones()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_attendee_by_email" not in BLOCKLIST:
    @mcp.tool()
    async def get_attendee_by_email(email: str) -> dict:
        """Get most recent attendance for an email."""
        try:
            return await _client().get_attendee_by_email(email)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_attendee_all_events" not in BLOCKLIST:
    @mcp.tool()
    async def get_attendee_all_events(email: str, items_per_page: int = 100, page_offset: int = 0) -> dict:
        """Get attendance across all events for an email."""
        try:
            return await _client().get_attendee_all_events(email, items_per_page, page_offset)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_registrant_by_email" not in BLOCKLIST:
    @mcp.tool()
    async def get_registrant_by_email(email: str, event_id: int = 0) -> dict:
        """Get registration for an email. Pass event_id=0 to skip event filter."""
        try:
            return await _client().get_registrant_by_email(email, event_id if event_id else None)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_registrant_all_events" not in BLOCKLIST:
    @mcp.tool()
    async def get_registrant_all_events(email: str, items_per_page: int = 100, page_offset: int = 0) -> dict:
        """Get all registrations across events for an email."""
        try:
            return await _client().get_registrant_all_events(email, items_per_page, page_offset)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_survey_library" not in BLOCKLIST:
    @mcp.tool()
    async def get_survey_library() -> dict:
        """Get client survey library."""
        try:
            return await _client().get_survey_library()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_engaged_accounts" not in BLOCKLIST:
    @mcp.tool()
    async def get_engaged_accounts() -> dict:
        """Get top engaged accounts (last 90 days)."""
        try:
            return await _client().get_engaged_accounts()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_pep" not in BLOCKLIST:
    @mcp.tool()
    async def get_pep(email: str) -> dict:
        """Get Prospect Engagement Profile for an email."""
        try:
            return await _client().get_pep(email)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "list_client_presenters" not in BLOCKLIST:
    @mcp.tool()
    async def list_client_presenters() -> dict:
        """List all presenters for the client."""
        try:
            return await _client().list_client_presenters()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "list_sub_clients" not in BLOCKLIST:
    @mcp.tool()
    async def list_sub_clients() -> dict:
        """List sub-client accounts."""
        try:
            return await _client().list_sub_clients()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_realtime_user_questions" not in BLOCKLIST:
    @mcp.tool()
    async def get_realtime_user_questions() -> dict:
        """Get questions from last 5 minutes across live events."""
        try:
            return await _client().get_realtime_user_questions()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "list_users" not in BLOCKLIST:
    @mcp.tool()
    async def list_users() -> dict:
        """List platform users for the client."""
        try:
            return await _client().list_users()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event_viewing_sessions" not in BLOCKLIST:
    @mcp.tool()
    async def get_event_viewing_sessions(event_id: int, session_type: str = "all", items_per_page: int = 100, page_offset: int = 0) -> dict:
        """Get attendee viewing sessions for an event."""
        try:
            return await _client().get_event_viewing_sessions(event_id, session_type, items_per_page, page_offset)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event_ctas" not in BLOCKLIST:
    @mcp.tool()
    async def get_event_ctas(event_id: int) -> dict:
        """Get CTA activity for an event."""
        try:
            return await _client().get_event_ctas(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event_group_chat" not in BLOCKLIST:
    @mcp.tool()
    async def get_event_group_chat(event_id: int) -> dict:
        """Get group chat activity for an event."""
        try:
            return await _client().get_event_group_chat(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event_email_stats" not in BLOCKLIST:
    @mcp.tool()
    async def get_event_email_stats(event_id: int) -> dict:
        """Get email statistics for an event."""
        try:
            return await _client().get_event_email_stats(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event_certifications" not in BLOCKLIST:
    @mcp.tool()
    async def get_event_certifications(event_id: int) -> dict:
        """Get certifications for an event."""
        try:
            return await _client().get_event_certifications(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event_content_activity" not in BLOCKLIST:
    @mcp.tool()
    async def get_event_content_activity(event_id: int) -> dict:
        """Get Engagement Hub content activity for an event."""
        try:
            return await _client().get_event_content_activity(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event_presenters" not in BLOCKLIST:
    @mcp.tool()
    async def get_event_presenters(event_id: int) -> dict:
        """Get presenters for an event."""
        try:
            return await _client().get_event_presenters(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event_calendar_reminder" not in BLOCKLIST:
    @mcp.tool()
    async def get_event_calendar_reminder(event_id: int) -> dict:
        """Get calendar reminder for an event."""
        try:
            return await _client().get_event_calendar_reminder(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event_email" not in BLOCKLIST:
    @mcp.tool()
    async def get_event_email(event_id: int) -> dict:
        """Get email notification details for an event."""
        try:
            return await _client().get_event_email(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event_presenter_chat" not in BLOCKLIST:
    @mcp.tool()
    async def get_event_presenter_chat(event_id: int) -> dict:
        """Get presenter chat logs for an event."""
        try:
            return await _client().get_event_presenter_chat(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event_slides" not in BLOCKLIST:
    @mcp.tool()
    async def get_event_slides(event_id: int) -> dict:
        """Get slide listing for an event."""
        try:
            return await _client().get_event_slides(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_ehub_content" not in BLOCKLIST:
    @mcp.tool()
    async def get_ehub_content(gateway_id: int) -> dict:
        """Get Engagement Hub content listing."""
        try:
            return await _client().get_ehub_content(gateway_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "list_media_manager_content" not in BLOCKLIST:
    @mcp.tool()
    async def list_media_manager_content(items_per_page: int = 100, page_offset: int = 0) -> dict:
        """List Media Manager derivative content."""
        try:
            return await _client().list_media_manager_content(items_per_page, page_offset)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_media_manager_content" not in BLOCKLIST:
    @mcp.tool()
    async def get_media_manager_content(media_id: int) -> dict:
        """Get a single Media Manager content item."""
        try:
            return await _client().get_media_manager_content(media_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_custom_account_tags" not in BLOCKLIST:
    @mcp.tool()
    async def get_custom_account_tags() -> dict:
        """Get custom account tags."""
        try:
            return await _client().get_custom_account_tags()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_account_managers" not in BLOCKLIST:
    @mcp.tool()
    async def get_account_managers() -> dict:
        """Get account manager contacts."""
        try:
            return await _client().get_account_managers()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event_managers" not in BLOCKLIST:
    @mcp.tool()
    async def get_event_managers() -> dict:
        """Get event manager contacts."""
        try:
            return await _client().get_event_managers()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_event_profiles" not in BLOCKLIST:
    @mcp.tool()
    async def get_event_profiles() -> dict:
        """Get event profiles."""
        try:
            return await _client().get_event_profiles()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_languages" not in BLOCKLIST:
    @mcp.tool()
    async def get_languages() -> dict:
        """Get available language codes."""
        try:
            return await _client().get_languages()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_registration_fields" not in BLOCKLIST:
    @mcp.tool()
    async def get_registration_fields(event_id: int) -> dict:
        """Get registration fields for an event."""
        try:
            return await _client().get_registration_fields(event_id)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_replacement_tokens" not in BLOCKLIST:
    @mcp.tool()
    async def get_replacement_tokens(context: str = "") -> dict:
        """Get replacement tokens for email templates."""
        try:
            return await _client().get_replacement_tokens(context or None)
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_sales_reps" not in BLOCKLIST:
    @mcp.tool()
    async def get_sales_reps() -> dict:
        """Get sales rep contacts."""
        try:
            return await _client().get_sales_reps()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_signal_contacts" not in BLOCKLIST:
    @mcp.tool()
    async def get_signal_contacts() -> dict:
        """Get signal contacts."""
        try:
            return await _client().get_signal_contacts()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "get_technical_reps" not in BLOCKLIST:
    @mcp.tool()
    async def get_technical_reps() -> dict:
        """Get technical rep contacts."""
        try:
            return await _client().get_technical_reps()
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if __name__ == "__main__":
    logger.info(f"Starting ON24 MCP server. Blocklist: {BLOCKLIST or 'none'}")
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = 8001
    mcp.run(transport="streamable-http")
