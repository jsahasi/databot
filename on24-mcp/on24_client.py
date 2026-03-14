import logging
from typing import Any
import httpx

logger = logging.getLogger(__name__)


class ON24APIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"ON24 API error {status_code}: {message}")


class ON24Client:
    def __init__(self, client_id: str, token_key: str, token_secret: str, base_url: str):
        self.client_id = client_id
        self.base_url = base_url.rstrip("/")
        self._headers = {
            "accessTokenKey": token_key,
            "accessTokenSecret": token_secret,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _path(self, endpoint: str) -> str:
        return f"/v2/client/{self.client_id}/{endpoint.lstrip('/')}"

    async def _request(self, method: str, endpoint: str, json_body: dict | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=30.0) as client:
            resp = await client.request(method, self._path(endpoint), json=json_body)
        if resp.status_code == 401:
            raise ON24APIError(401, "Invalid credentials")
        if resp.status_code == 403:
            raise ON24APIError(403, "Permission denied")
        if resp.status_code == 404:
            raise ON24APIError(404, f"Not found: {endpoint}")
        if resp.status_code >= 400:
            raise ON24APIError(resp.status_code, resp.text)
        return resp.json()

    async def create_event(self, title: str, event_type: str, start_time: str, end_time: str, description: str | None = None) -> dict:
        body: dict = {"eventType": event_type, "title": title, "startTime": start_time, "endTime": end_time}
        if description:
            body["description"] = description
        return await self._request("POST", "event", body)

    async def update_event(self, event_id: int, title: str | None = None, description: str | None = None, start_time: str | None = None, end_time: str | None = None) -> dict:
        body = {k: v for k, v in {"title": title, "description": description, "startTime": start_time, "endTime": end_time}.items() if v is not None}
        return await self._request("PATCH", f"event/{event_id}", body)

    async def register_attendee(self, event_id: int, email: str, first_name: str, last_name: str, company: str | None = None, job_title: str | None = None) -> dict:
        body: dict = {"email": email, "firstName": first_name, "lastName": last_name}
        if company:
            body["company"] = company
        if job_title:
            body["jobTitle"] = job_title
        return await self._request("POST", f"event/{event_id}/registrant", body)

    async def remove_registration(self, event_id: int, email: str) -> dict:
        return await self._request("DELETE", f"event/{event_id}/registrant/{email}")

    # ── Read Operations ──

    async def _get(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=30.0) as client:
            resp = await client.get(self._path(endpoint), params=params)
        if resp.status_code >= 400:
            raise ON24APIError(resp.status_code, resp.text)
        return resp.json()

    async def list_events(self, start_date: str | None = None, end_date: str | None = None,
                          items_per_page: int = 100, page_offset: int = 0) -> dict:
        params: dict = {"itemsPerPage": items_per_page, "pageOffset": page_offset}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self._get("event", params)

    async def get_event(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}")

    async def list_event_attendees(self, event_id: int, items_per_page: int = 100, page_offset: int = 0) -> dict:
        return await self._get(f"event/{event_id}/attendee", {"itemsPerPage": items_per_page, "pageOffset": page_offset})

    async def list_event_registrants(self, event_id: int, items_per_page: int = 100, page_offset: int = 0) -> dict:
        return await self._get(f"event/{event_id}/registrant", {"itemsPerPage": items_per_page, "pageOffset": page_offset})

    async def list_client_attendees(self, start_date: str | None = None, end_date: str | None = None,
                                    items_per_page: int = 100, page_offset: int = 0) -> dict:
        params: dict = {"itemsPerPage": items_per_page, "pageOffset": page_offset}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self._get("attendee", params)

    async def list_client_registrants(self, start_date: str | None = None, end_date: str | None = None,
                                      items_per_page: int = 100, page_offset: int = 0) -> dict:
        params: dict = {"itemsPerPage": items_per_page, "pageOffset": page_offset}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self._get("registrant", params)

    async def list_client_leads(self, start_date: str | None = None, end_date: str | None = None,
                                items_per_page: int = 50, page_offset: int = 0) -> dict:
        params: dict = {"itemsPerPage": items_per_page, "pageOffset": page_offset}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self._get("lead", params)

    async def get_event_polls(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}/poll")

    async def get_event_surveys(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}/survey")

    async def get_event_resources(self, event_id: int) -> dict:
        return await self._get(f"event/{event_id}/resource")

    async def get_event_types(self) -> dict:
        return await self._get("eventtypes")

    async def get_timezones(self) -> dict:
        return await self._get("timezones")
