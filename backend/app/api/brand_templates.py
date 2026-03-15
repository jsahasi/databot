"""Brand template management — simple JSON file storage."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

TEMPLATES_FILE = Path("/app/data/brand_templates.json")

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
    isDefault: bool = False


class BrandTemplateUpdate(BaseModel):
    name: str | None = None
    primaryColor: str | None = None
    backgroundColor: str | None = None
    accentColor: str | None = None
    fontColor: str | None = None
    fontFamily: str | None = None
    logoUrl: str | None = None
    isDefault: bool | None = None


def _load_templates() -> list[dict]:
    if TEMPLATES_FILE.exists():
        try:
            return json.loads(TEMPLATES_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save_templates(templates: list[dict]) -> None:
    TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATES_FILE.write_text(json.dumps(templates, indent=2))


@router.get("/fonts")
def list_fonts():
    """Return the curated Google Fonts list."""
    return {"fonts": GOOGLE_FONTS}


@router.get("/default")
def get_default_template():
    """Return the default brand template."""
    templates = _load_templates()
    for t in templates:
        if t.get("isDefault"):
            return t
    if templates:
        return templates[0]
    return DEFAULT_TEMPLATE


@router.get("")
def list_templates():
    """List all brand templates."""
    templates = _load_templates()
    return {"templates": templates}


@router.post("")
def create_template(body: BrandTemplateCreate):
    """Create a new brand template."""
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
        "isDefault": body.isDefault,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    templates.append(template)
    _save_templates(templates)
    return template


@router.put("/{template_id}")
def update_template(template_id: str, body: BrandTemplateUpdate):
    """Update an existing brand template."""
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
    # If we deleted the default, make the first one default
    if target.get("isDefault") and templates:
        templates[0]["isDefault"] = True
    _save_templates(templates)
    return {"ok": True}
