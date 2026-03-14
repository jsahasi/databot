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


if __name__ == "__main__":
    logger.info(f"Starting ON24 MCP server. Blocklist: {BLOCKLIST or 'none'}")
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = 8001
    mcp.run(transport="streamable-http")
