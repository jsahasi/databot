"""Tests for the brand templates API (JSON file-backed CRUD)."""

import pytest
from unittest.mock import patch

_mock_store: list[dict] = []


def _mock_load() -> list[dict]:
    return list(_mock_store)


def _mock_save(templates: list[dict]) -> None:
    _mock_store.clear()
    _mock_store.extend(templates)


@pytest.fixture(autouse=True)
def _patch_file_io():
    """Replace file I/O with in-memory list for every test."""
    _mock_store.clear()
    with patch(
        "app.api.brand_templates._load_templates", side_effect=_mock_load
    ), patch(
        "app.api.brand_templates._save_templates", side_effect=_mock_save
    ):
        yield


@pytest.mark.asyncio
class TestBrandTemplates:
    async def test_list_templates_empty(self, client):
        """GET /api/brand-templates returns empty list when no file exists."""
        resp = await client.get("/api/brand-templates")
        assert resp.status_code == 200
        assert resp.json() == {"templates": []}

    async def test_create_template(self, client):
        """POST /api/brand-templates creates a template with id and createdAt."""
        payload = {"name": "My Brand", "primaryColor": "#ff0000"}
        resp = await client.post("/api/brand-templates", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "My Brand"
        assert data["primaryColor"] == "#ff0000"
        assert "id" in data
        assert "createdAt" in data
        assert data["isDefault"] is False

    async def test_create_template_sets_default(self, client):
        """Creating with isDefault=true works."""
        payload = {"name": "Default Brand", "isDefault": True}
        resp = await client.post("/api/brand-templates", json=payload)
        assert resp.status_code == 200
        assert resp.json()["isDefault"] is True

    async def test_get_default_template_fallback(self, client):
        """GET /api/brand-templates/default returns hardcoded fallback when empty."""
        resp = await client.get("/api/brand-templates/default")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "default"
        assert data["name"] == "ON24 Nexus"
        assert data["isDefault"] is True

    async def test_get_fonts(self, client):
        """GET /api/brand-templates/fonts returns non-empty list including Inter."""
        resp = await client.get("/api/brand-templates/fonts")
        assert resp.status_code == 200
        fonts = resp.json()["fonts"]
        assert len(fonts) > 0
        assert "Inter" in fonts

    async def test_update_template(self, client):
        """PUT /api/brand-templates/{id} updates name and colors."""
        # Create first
        create_resp = await client.post(
            "/api/brand-templates", json={"name": "Original"}
        )
        template_id = create_resp.json()["id"]

        # Update
        resp = await client.put(
            f"/api/brand-templates/{template_id}",
            json={"name": "Updated", "primaryColor": "#00ff00"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated"
        assert data["primaryColor"] == "#00ff00"

    async def test_delete_template(self, client):
        """DELETE /api/brand-templates/{id} removes the template."""
        # Create two so delete doesn't hit last-default guard
        await client.post(
            "/api/brand-templates", json={"name": "First", "isDefault": True}
        )
        resp2 = await client.post(
            "/api/brand-templates", json={"name": "Second"}
        )
        second_id = resp2.json()["id"]

        # Delete the second
        del_resp = await client.delete(f"/api/brand-templates/{second_id}")
        assert del_resp.status_code == 200
        assert del_resp.json() == {"ok": True}

        # Verify it's gone
        list_resp = await client.get("/api/brand-templates")
        ids = [t["id"] for t in list_resp.json()["templates"]]
        assert second_id not in ids

    async def test_create_default_clears_others(self, client):
        """Creating a second template with isDefault=true clears the first."""
        # Create first default
        resp1 = await client.post(
            "/api/brand-templates", json={"name": "First", "isDefault": True}
        )
        first_id = resp1.json()["id"]

        # Create second default
        await client.post(
            "/api/brand-templates", json={"name": "Second", "isDefault": True}
        )

        # Verify first is no longer default
        list_resp = await client.get("/api/brand-templates")
        templates = list_resp.json()["templates"]
        first = next(t for t in templates if t["id"] == first_id)
        assert first["isDefault"] is False

        # Exactly one default
        defaults = [t for t in templates if t["isDefault"]]
        assert len(defaults) == 1
        assert defaults[0]["name"] == "Second"
