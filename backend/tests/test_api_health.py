"""Tests for the FastAPI health endpoint and API router mounting."""

import pytest


@pytest.mark.asyncio
class TestHealth:
    async def test_health_returns_200(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "ok"}


@pytest.mark.asyncio
class TestAPIRouter:
    async def test_api_prefix_is_mounted(self, client):
        """The API router should be mounted at /api. We verify by checking the
        OpenAPI schema which lists all routes without requiring a DB."""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        paths = response.json().get("paths", {})
        # The events endpoint should be registered under /api/events
        assert "/api/events" in paths

    async def test_unknown_route_returns_404(self, client):
        response = await client.get("/nonexistent")
        assert response.status_code == 404
