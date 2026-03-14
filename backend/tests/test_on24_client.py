"""Tests for the ON24 API client."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.on24_client import ON24APIError, ON24Client

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client():
    return ON24Client(
        client_id="12345",
        access_token_key="test-key",
        access_token_secret="test-secret",
        base_url="https://api.on24.com",
    )


@pytest.fixture
def events_payload():
    return json.loads((FIXTURES / "events_response.json").read_text())


@pytest.fixture
def attendees_payload():
    return json.loads((FIXTURES / "attendees_response.json").read_text())


# ---------------------------------------------------------------------------
# _build_path
# ---------------------------------------------------------------------------


class TestBuildPath:
    def test_simple_endpoint(self, client):
        assert client._build_path("event") == "/v2/client/12345/event"

    def test_nested_endpoint(self, client):
        assert (
            client._build_path("event/10001/attendee")
            == "/v2/client/12345/event/10001/attendee"
        )

    def test_strips_leading_slash(self, client):
        assert client._build_path("/event") == "/v2/client/12345/event"


# ---------------------------------------------------------------------------
# Auth headers
# ---------------------------------------------------------------------------


class TestAuthHeaders:
    def test_headers_contain_credentials(self, client):
        assert client._headers["accessTokenKey"] == "test-key"
        assert client._headers["accessTokenSecret"] == "test-secret"
        assert client._headers["Accept"] == "application/json"


# ---------------------------------------------------------------------------
# Rate limiter category detection
# ---------------------------------------------------------------------------


class TestCategoryDetection:
    def test_event_detail(self, client):
        cat = client._rate_limiter.get_category_for_endpoint(
            "/v2/client/12345/event/10001"
        )
        assert cat == "event_detail"

    def test_event_attendee_is_analytics_high(self, client):
        cat = client._rate_limiter.get_category_for_endpoint(
            "/v2/client/12345/event/10001/attendee"
        )
        assert cat == "analytics_high"

    def test_event_registrant_write(self, client):
        # Path ending in "registrant" matches registrant_write rule
        cat = client._rate_limiter.get_category_for_endpoint(
            "/v2/client/12345/event/10001/registrant"
        )
        assert cat == "registrant_write"

    def test_event_poll_is_analytics_medium(self, client):
        cat = client._rate_limiter.get_category_for_endpoint(
            "/v2/client/12345/event/10001/poll"
        )
        assert cat == "analytics_medium"

    def test_events_list_is_analytics_low(self, client):
        cat = client._rate_limiter.get_category_for_endpoint(
            "/v2/client/12345/event"
        )
        assert cat == "analytics_low"

    def test_unknown_endpoint_returns_default(self, client):
        cat = client._rate_limiter.get_category_for_endpoint(
            "/v2/client/12345/something/unknown"
        )
        assert cat == "default"


# ---------------------------------------------------------------------------
# Mocked HTTP requests – list_events, get_event, list_event_attendees
# ---------------------------------------------------------------------------


def _mock_transport(status_code: int, json_body: dict | None = None, text: str = ""):
    """Build an httpx MockTransport that returns a canned response."""

    async def handler(request: httpx.Request) -> httpx.Response:
        if json_body is not None:
            return httpx.Response(
                status_code,
                json=json_body,
                request=request,
            )
        return httpx.Response(status_code, text=text, request=request)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
class TestListEvents:
    async def test_returns_events(self, client, events_payload):
        transport = _mock_transport(200, events_payload)
        client._http_client = httpx.AsyncClient(
            transport=transport, base_url=client.base_url, headers=client._headers
        )

        result = await client.list_events()

        assert result["totalevents"] == 2
        assert len(result["events"]) == 2
        assert result["events"][0]["eventid"] == 10001
        await client.close()

    async def test_passes_date_params(self, client, events_payload):
        received_params = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            received_params.update(dict(request.url.params))
            return httpx.Response(200, json=events_payload, request=request)

        client._http_client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url=client.base_url,
            headers=client._headers,
        )

        await client.list_events(start_date="2025-01-01", end_date="2025-12-31")

        assert received_params["startDate"] == "2025-01-01"
        assert received_params["endDate"] == "2025-12-31"
        await client.close()


@pytest.mark.asyncio
class TestGetEvent:
    async def test_returns_single_event(self, client):
        event_data = {"eventid": 10001, "eventname": "Test"}
        transport = _mock_transport(200, event_data)
        client._http_client = httpx.AsyncClient(
            transport=transport, base_url=client.base_url, headers=client._headers
        )

        result = await client.get_event(10001)

        assert result["eventid"] == 10001
        await client.close()


@pytest.mark.asyncio
class TestListEventAttendees:
    async def test_returns_attendees(self, client, attendees_payload):
        transport = _mock_transport(200, attendees_payload)
        client._http_client = httpx.AsyncClient(
            transport=transport, base_url=client.base_url, headers=client._headers
        )

        result = await client.list_event_attendees(10001)

        assert result["totalattendees"] == 3
        assert len(result["attendees"]) == 3
        assert result["attendees"][0]["email"] == "alice.johnson@example.com"
        await client.close()


# ---------------------------------------------------------------------------
# Pagination helper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPaginate:
    async def test_collects_items_across_pages(self, client):
        """Paginate should keep fetching until a page returns fewer items than
        items_per_page."""
        call_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            page_offset = int(request.url.params.get("pageOffset", 0))
            call_count += 1
            if page_offset == 0:
                items = [{"id": i} for i in range(3)]
            else:
                items = [{"id": 10}]  # last page – fewer than items_per_page
            return httpx.Response(200, json={"items": items}, request=request)

        client._http_client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url=client.base_url,
            headers=client._headers,
        )

        result = await client.paginate("some/endpoint", items_key="items", items_per_page=3)

        assert len(result) == 4  # 3 from page 0 + 1 from page 1
        assert call_count == 2
        await client.close()

    async def test_respects_max_pages(self, client):
        """When max_pages is set, pagination should stop even if the page is full."""

        async def handler(request: httpx.Request) -> httpx.Response:
            items = [{"id": i} for i in range(5)]
            return httpx.Response(200, json={"items": items}, request=request)

        client._http_client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url=client.base_url,
            headers=client._headers,
        )

        result = await client.paginate(
            "some/endpoint", items_key="items", items_per_page=5, max_pages=1
        )

        assert len(result) == 5
        await client.close()

    async def test_falls_back_to_alternative_keys(self, client):
        """When items_key is missing, paginate should try common keys like
        'events'."""

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"events": [{"id": 1}, {"id": 2}]}, request=request
            )

        client._http_client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url=client.base_url,
            headers=client._headers,
        )

        result = await client.paginate(
            "event", items_key="nonexistent", items_per_page=100
        )

        assert len(result) == 2
        await client.close()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestErrorHandling:
    async def test_401_raises_on24_api_error(self, client):
        transport = _mock_transport(401, text="Unauthorized")
        client._http_client = httpx.AsyncClient(
            transport=transport, base_url=client.base_url, headers=client._headers
        )

        with pytest.raises(ON24APIError) as exc_info:
            await client.get("event")

        assert exc_info.value.status_code == 401
        assert "credentials" in exc_info.value.message.lower()
        await client.close()

    async def test_403_raises_on24_api_error(self, client):
        transport = _mock_transport(403, text="Forbidden")
        client._http_client = httpx.AsyncClient(
            transport=transport, base_url=client.base_url, headers=client._headers
        )

        with pytest.raises(ON24APIError) as exc_info:
            await client.get("event")

        assert exc_info.value.status_code == 403
        assert "permission" in exc_info.value.message.lower()
        await client.close()

    async def test_404_raises_on24_api_error(self, client):
        transport = _mock_transport(404, text="Not Found")
        client._http_client = httpx.AsyncClient(
            transport=transport, base_url=client.base_url, headers=client._headers
        )

        with pytest.raises(ON24APIError) as exc_info:
            await client.get("event/99999")

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.message.lower()
        await client.close()

    async def test_500_raises_on24_api_error(self, client):
        transport = _mock_transport(500, text="Internal Server Error")
        client._http_client = httpx.AsyncClient(
            transport=transport, base_url=client.base_url, headers=client._headers
        )

        with pytest.raises(ON24APIError) as exc_info:
            await client.get("event")

        assert exc_info.value.status_code == 500
        await client.close()
