"""Brand template management — per-client JSON file storage.

Each client_id gets its own file: data/brand_templates_{client_id}.json
No client shares templates with any other client.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from pydantic import BaseModel

from app.db.on24_db import get_client_id

router = APIRouter()

DATA_DIR = Path("/app/data")

GOOGLE_FONTS = [
    "Inter", "Roboto", "Open Sans", "Lato", "Montserrat", "Poppins",
    "Raleway", "Nunito", "Playfair Display", "Merriweather",
    "Source Sans 3", "PT Sans", "Oswald", "Rubik", "Work Sans",
    "Fira Sans", "Barlow", "DM Sans", "Outfit", "Space Grotesk",
    "Plus Jakarta Sans", "Sora", "Manrope", "Lexend", "Geist",
]

DEFAULT_TEMPLATE: dict = {
    "id": "default",
    "name": "ON24 Nexus",
    "primaryColor": "#4f46e5",
    "backgroundColor": "#ffffff",
    "accentColor": "#6366f1",
    "fontColor": "#1a1d2e",
    "fontFamily": "Inter",
    "logoUrl": "",
    "bannerImageUrl": "",
    "isDefault": True,
    "createdAt": "2026-01-01T00:00:00Z",
}


class BrandTemplateCreate(BaseModel):
    name: str
    primaryColor: str = "#4f46e5"
    backgroundColor: str = "#ffffff"
    accentColor: str = "#6366f1"
    fontColor: str = "#1a1d2e"
    fontFamily: str = "Inter"
    logoUrl: str = ""
    bannerImageUrl: str = ""
    isDefault: bool = False


class BrandTemplateUpdate(BaseModel):
    name: str | None = None
    primaryColor: str | None = None
    backgroundColor: str | None = None
    accentColor: str | None = None
    fontColor: str | None = None
    fontFamily: str | None = None
    logoUrl: str | None = None
    bannerImageUrl: str | None = None
    isDefault: bool | None = None


def _templates_file(client_id: int | None = None) -> Path:
    """Return the per-client templates JSON file path."""
    cid = client_id or get_client_id()
    return DATA_DIR / f"brand_templates_{cid}.json"


def _load_templates(client_id: int | None = None) -> list[dict]:
    f = _templates_file(client_id)
    if f.exists():
        try:
            return json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save_templates(templates: list[dict], client_id: int | None = None) -> None:
    f = _templates_file(client_id)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(templates, indent=2))


@router.get("/fonts")
def list_fonts():
    """Return the curated Google Fonts list."""
    return {"fonts": GOOGLE_FONTS}


@router.get("/default")
def get_default_template():
    """Return the default brand template for the current client."""
    templates = _load_templates()
    for t in templates:
        if t.get("isDefault"):
            return t
    if templates:
        return templates[0]
    return DEFAULT_TEMPLATE


@router.get("")
def list_templates():
    """List all brand templates for the current client."""
    templates = _load_templates()
    return {"templates": templates}


@router.post("")
def create_template(body: BrandTemplateCreate):
    """Create a new brand template for the current client."""
    templates = _load_templates()
    if body.isDefault:
        for t in templates:
            t["isDefault"] = False
    template = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "primaryColor": body.primaryColor,
        "backgroundColor": body.backgroundColor,
        "accentColor": body.accentColor,
        "fontColor": body.fontColor,
        "fontFamily": body.fontFamily,
        "logoUrl": body.logoUrl,
        "bannerImageUrl": body.bannerImageUrl,
        "isDefault": body.isDefault,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    templates.append(template)
    _save_templates(templates)
    return template


@router.put("/{template_id}")
def update_template(template_id: str, body: BrandTemplateUpdate):
    """Update an existing brand template for the current client."""
    templates = _load_templates()
    target = None
    for t in templates:
        if t["id"] == template_id:
            target = t
            break
    if not target:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = body.model_dump(exclude_none=True)
    if update_data.get("isDefault"):
        for t in templates:
            t["isDefault"] = False
    target.update(update_data)
    _save_templates(templates)
    return target


@router.delete("/{template_id}")
def delete_template(template_id: str):
    """Delete a brand template. Cannot delete the last default template."""
    templates = _load_templates()
    target = None
    for t in templates:
        if t["id"] == template_id:
            target = t
            break
    if not target:
        raise HTTPException(status_code=404, detail="Template not found")
    if target.get("isDefault") and len(templates) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last default template")

    templates = [t for t in templates if t["id"] != template_id]
    if target.get("isDefault") and templates:
        templates[0]["isDefault"] = True
    _save_templates(templates)
    return {"ok": True}
