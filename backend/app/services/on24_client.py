import logging
from typing import Any

import httpx

from app.config import settings
from app.services.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class ON24APIError(Exception):
    """Raised when ON24 API returns an error."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"ON24 API error {status_code}: {message}")


class ON24Client:
    """Async client for ON24 REST API v2."""

    def __init__(
        self,
        client_id: str | None = None,
        access_token_key: str | None = None,
        access_token_secret: str | None = None,
        base_url: str | None = None,
    ):
        self.client_id = client_id or settings.on24_client_id
        self.base_url = (base_url or settings.on24_base_url).rstrip("/")
        self._headers = {
            "accessTokenKey": access_token_key or settings.on24_access_token_key,
            "accessTokenSecret": access_token_secret or settings.on24_access_token_secret,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self._rate_limiter = RateLimiter()
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers,
                timeout=30.0,
            )
        return self._http_client

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    def _build_path(self, endpoint: str) -> str:
        """Build full API path with client ID."""
        return f"/v2/client/{self.client_id}/{endpoint.lstrip('/')}"

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a rate-limited request to ON24 API."""
        path = self._build_path(endpoint)
        category = self._rate_limiter.get_category_for_endpoint(path)
        await self._rate_limiter.acquire(category)

        client = await self._get_client()
        logger.debug(f"ON24 {method} {path} params={params}")

        response = await client.request(method, path, params=params, json=json_body)

        if response.status_code == 401:
            raise ON24APIError(401, "Invalid or deactivated API credentials")
        if response.status_code == 403:
            raise ON24APIError(403, "Permission denied or rate limit exceeded")
        if response.status_code == 404:
            raise ON24APIError(404, f"Resource not found: {path}")
        if response.status_code >= 400:
            raise ON24APIError(response.status_code, response.text)

        return response.json()

    async def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return await self._request("GET", endpoint, params=params)

    async def post(
        self,
        endpoint: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request("POST", endpoint, params=params, json_body=json_body)

    async def put(
        self,
        endpoint: str,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request("PUT", endpoint, json_body=json_body)

    async def patch(
        self,
        endpoint: str,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request("PATCH", endpoint, json_body=json_body)

    async def delete(self, endpoint: str) -> dict[str, Any]:
        return await self._request("DELETE", endpoint)

    # ── Client-Level Analytics ──

    async def list_events(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        include_inactive: bool = False,
        content_type: str = "all",
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict[str, Any]:
        """List events for the client."""
        params: dict[str, Any] = {
            "itemsPerPage": items_per_page,
            "pageOffset": page_offset,
            "contentType": content_type,
        }
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        if include_inactive:
            params["includeInactive"] = "Y"
        return await self.get("event", params=params)

    async def get_event(self, event_id: int) -> dict[str, Any]:
        """Get event metadata and usage summary."""
        return await self.get(f"event/{event_id}")

    async def list_client_attendees(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict[str, Any]:
        """List attendees across all events."""
        params: dict[str, Any] = {
            "itemsPerPage": items_per_page,
            "pageOffset": page_offset,
        }
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self.get("attendee", params=params)

    async def list_client_registrants(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict[str, Any]:
        """List registrants across all events."""
        params: dict[str, Any] = {
            "itemsPerPage": items_per_page,
            "pageOffset": page_offset,
        }
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self.get("registrant", params=params)

    async def get_attendee_by_email(self, email: str) -> dict[str, Any]:
        """Get most recent attendance for an email."""
        return await self.get(f"attendee/{email}")

    async def get_attendee_all_events(
        self, email: str, page_offset: int = 0, items_per_page: int = 100
    ) -> dict[str, Any]:
        """Get all attendance across events for an email."""
        return await self.get(
            f"attendee/{email}/allevents",
            params={"pageOffset": page_offset, "itemsPerPage": items_per_page},
        )

    async def list_client_leads(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        page_offset: int = 0,
        items_per_page: int = 50,
    ) -> dict[str, Any]:
        """List leads for the client."""
        params: dict[str, Any] = {
            "itemsPerPage": items_per_page,
            "pageOffset": page_offset,
        }
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self.get("lead", params=params)

    async def get_pep(self, email: str) -> dict[str, Any]:
        """Get Prospect Engagement Profile for an email."""
        return await self.get(f"lead/{email}")

    async def get_engaged_accounts(self) -> dict[str, Any]:
        """Get top engaged accounts (last 90 days, max 100)."""
        return await self.get("engagedaccount")

    async def list_client_presenters(self) -> dict[str, Any]:
        """List presenters for the client."""
        return await self.get("presenter")

    async def get_survey_library(self) -> dict[str, Any]:
        """Get client survey library."""
        return await self.get("surveylibrary")

    async def list_users(self) -> dict[str, Any]:
        """List users for the client."""
        return await self.get("users")

    # ── Event-Level Analytics ──

    async def list_event_attendees(
        self,
        event_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict[str, Any]:
        """List attendees for a specific event."""
        params: dict[str, Any] = {
            "itemsPerPage": items_per_page,
            "pageOffset": page_offset,
        }
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self.get(f"event/{event_id}/attendee", params=params)

    async def list_event_registrants(
        self,
        event_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        page_offset: int = 0,
        items_per_page: int = 100,
        noshow: bool = False,
    ) -> dict[str, Any]:
        """List registrants for a specific event."""
        params: dict[str, Any] = {
            "itemsPerPage": items_per_page,
            "pageOffset": page_offset,
        }
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        if noshow:
            params["noshow"] = "Y"
        return await self.get(f"event/{event_id}/registrant", params=params)

    async def get_event_viewing_sessions(
        self,
        event_id: int,
        session_type: str = "all",
        page_offset: int = 0,
        items_per_page: int = 100,
    ) -> dict[str, Any]:
        """Get attendee viewing sessions for an event."""
        return await self.get(
            f"event/{event_id}/attendeesession",
            params={
                "sessionType": session_type,
                "pageoffset": page_offset,
                "itemsPerPage": items_per_page,
            },
        )

    async def get_event_polls(self, event_id: int) -> dict[str, Any]:
        """Get polls for an event."""
        return await self.get(f"event/{event_id}/poll")

    async def get_event_surveys(self, event_id: int) -> dict[str, Any]:
        """Get surveys for an event."""
        return await self.get(f"event/{event_id}/survey")

    async def get_event_resources(self, event_id: int) -> dict[str, Any]:
        """Get resources viewed for an event."""
        return await self.get(f"event/{event_id}/resource")

    async def get_event_ctas(self, event_id: int) -> dict[str, Any]:
        """Get CTA activity for an event."""
        return await self.get(f"event/{event_id}/cta")

    async def get_event_group_chat(self, event_id: int) -> dict[str, Any]:
        """Get group chat activity for an event."""
        return await self.get(f"event/{event_id}/groupchat")

    async def get_event_email_stats(self, event_id: int) -> dict[str, Any]:
        """Get email statistics for an event."""
        return await self.get(f"event/{event_id}/emailstatistics")

    async def get_event_certifications(self, event_id: int) -> dict[str, Any]:
        """Get certifications for an event."""
        return await self.get(f"event/{event_id}/certifications")

    async def get_event_content_activity(self, event_id: int) -> dict[str, Any]:
        """Get Engagement Hub content activity for an event."""
        return await self.get(f"event/{event_id}/contentactivity")

    async def get_event_presenters(self, event_id: int) -> dict[str, Any]:
        """Get presenters for an event."""
        return await self.get(f"event/{event_id}/presenter")

    # ── Pagination Helper ──

    async def paginate(
        self,
        endpoint: str,
        items_key: str = "items",
        items_per_page: int = 100,
        max_pages: int | None = None,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Auto-paginate through all pages of a paginated endpoint.

        Args:
            endpoint: API endpoint path
            items_key: Key in response containing the items list
            items_per_page: Number of items per page
            max_pages: Maximum number of pages to fetch (None = all)
            params: Additional query parameters

        Returns:
            Combined list of all items across pages
        """
        all_items: list[dict[str, Any]] = []
        page_offset = 0
        page_count = 0

        while True:
            request_params = dict(params or {})
            request_params["itemsPerPage"] = items_per_page
            request_params["pageOffset"] = page_offset

            data = await self.get(endpoint, params=request_params)

            # ON24 uses various keys for the items list
            items = data.get(items_key, [])
            if not items:
                # Try common alternative keys
                for key in ["events", "attendees", "registrants", "leads"]:
                    items = data.get(key, [])
                    if items:
                        break

            all_items.extend(items)
            page_count += 1

            logger.debug(
                f"Paginate {endpoint}: page {page_offset}, got {len(items)} items, "
                f"total so far: {len(all_items)}"
            )

            # Stop conditions
            if len(items) < items_per_page:
                break
            if max_pages and page_count >= max_pages:
                break

            page_offset += 1

        return all_items
