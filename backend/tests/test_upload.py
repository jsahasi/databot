"""Tests for the upload API endpoints and cleanup logic.

Covers file size validation, MIME type validation, cleanup_old_uploads,
and path traversal protection on the serve endpoint.
"""

import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.upload import cleanup_old_uploads, UPLOAD_DIR


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------- MIME type validation ----------

@pytest.mark.asyncio
async def test_upload_rejects_disallowed_mime_type(client):
    """Uploading a .txt file should be rejected with 400."""
    resp = await client.post(
        "/api/upload",
        files={"file": ("test.txt", b"hello world", "text/plain")},
    )
    assert resp.status_code == 400
    assert "not allowed" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_rejects_html_mime_type(client):
    resp = await client.post(
        "/api/upload",
        files={"file": ("page.html", b"<html></html>", "text/html")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_accepts_pdf(client, tmp_path):
    """PDF content type should be accepted (size under limit)."""
    # Minimal valid-looking PDF bytes (not a real PDF, but content_type check comes first)
    pdf_bytes = b"%PDF-1.4 fake content"
    with patch("app.api.upload.UPLOAD_DIR", tmp_path):
        resp = await client.post(
            "/api/upload",
            files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["content_type"] == "application/pdf"
    assert data["original_name"] == "doc.pdf"
    assert data["size"] == len(pdf_bytes)


@pytest.mark.asyncio
async def test_upload_accepts_png(client, tmp_path):
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    with patch("app.api.upload.UPLOAD_DIR", tmp_path):
        resp = await client.post(
            "/api/upload",
            files={"file": ("image.png", png_bytes, "image/png")},
        )
    assert resp.status_code == 200
    assert resp.json()["content_type"] == "image/png"


@pytest.mark.asyncio
async def test_upload_accepts_jpeg(client, tmp_path):
    jpeg_bytes = b"\xff\xd8\xff" + b"\x00" * 50
    with patch("app.api.upload.UPLOAD_DIR", tmp_path):
        resp = await client.post(
            "/api/upload",
            files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_upload_accepts_gif(client, tmp_path):
    gif_bytes = b"GIF89a" + b"\x00" * 50
    with patch("app.api.upload.UPLOAD_DIR", tmp_path):
        resp = await client.post(
            "/api/upload",
            files={"file": ("anim.gif", gif_bytes, "image/gif")},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_upload_accepts_webp(client, tmp_path):
    webp_bytes = b"RIFF" + b"\x00" * 50
    with patch("app.api.upload.UPLOAD_DIR", tmp_path):
        resp = await client.post(
            "/api/upload",
            files={"file": ("pic.webp", webp_bytes, "image/webp")},
        )
    assert resp.status_code == 200


# ---------- File size validation ----------

@pytest.mark.asyncio
async def test_upload_rejects_oversized_file(client, tmp_path):
    """Files larger than 10 MB should be rejected."""
    big_content = b"x" * (10 * 1024 * 1024 + 1)  # just over 10 MB
    with patch("app.api.upload.UPLOAD_DIR", tmp_path):
        resp = await client.post(
            "/api/upload",
            files={"file": ("big.pdf", big_content, "application/pdf")},
        )
    assert resp.status_code == 400
    assert "too large" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_accepts_exactly_max_size(client, tmp_path):
    """A file of exactly MAX_FILE_SIZE bytes should be accepted."""
    content = b"x" * (10 * 1024 * 1024)  # exactly 10 MB
    with patch("app.api.upload.UPLOAD_DIR", tmp_path):
        resp = await client.post(
            "/api/upload",
            files={"file": ("exact.pdf", content, "application/pdf")},
        )
    assert resp.status_code == 200


# ---------- Path traversal protection ----------

@pytest.mark.asyncio
async def test_serve_rejects_path_traversal_dotdot(client):
    resp = await client.get("/api/uploads/../../etc/passwd")
    assert resp.status_code in (400, 404, 422)


@pytest.mark.asyncio
async def test_serve_rejects_forward_slash(client):
    resp = await client.get("/api/uploads/sub/file.pdf")
    # FastAPI may split this differently, but the handler should reject or 404
    assert resp.status_code in (400, 404, 422)


@pytest.mark.asyncio
async def test_serve_rejects_backslash(client):
    resp = await client.get("/api/uploads/sub%5Cfile.pdf")
    # %5C is backslash — should be rejected
    assert resp.status_code in (400, 404, 422)


@pytest.mark.asyncio
async def test_serve_returns_404_for_nonexistent_file(client):
    resp = await client.get("/api/uploads/nonexistent_abc123.pdf")
    assert resp.status_code == 404


# ---------- cleanup_old_uploads ----------

def test_cleanup_deletes_old_files(tmp_path):
    """Files older than max_age_hours should be deleted."""
    old_file = tmp_path / "old_file.pdf"
    old_file.write_bytes(b"old content")
    # Set mtime to 25 hours ago
    old_mtime = time.time() - (25 * 3600)
    os.utime(old_file, (old_mtime, old_mtime))

    new_file = tmp_path / "new_file.pdf"
    new_file.write_bytes(b"new content")

    with patch("app.api.upload.UPLOAD_DIR", tmp_path):
        deleted = cleanup_old_uploads(max_age_hours=24)

    assert deleted == 1
    assert not old_file.exists()
    assert new_file.exists()


def test_cleanup_keeps_recent_files(tmp_path):
    """Files newer than max_age_hours should be kept."""
    recent = tmp_path / "recent.pdf"
    recent.write_bytes(b"content")

    with patch("app.api.upload.UPLOAD_DIR", tmp_path):
        deleted = cleanup_old_uploads(max_age_hours=24)

    assert deleted == 0
    assert recent.exists()


def test_cleanup_returns_zero_on_empty_dir(tmp_path):
    with patch("app.api.upload.UPLOAD_DIR", tmp_path):
        deleted = cleanup_old_uploads(max_age_hours=24)
    assert deleted == 0


# ---------- Filename extension handling ----------

@pytest.mark.asyncio
async def test_upload_preserves_pdf_extension(client, tmp_path):
    with patch("app.api.upload.UPLOAD_DIR", tmp_path):
        resp = await client.post(
            "/api/upload",
            files={"file": ("report.pdf", b"%PDF-1.4 data", "application/pdf")},
        )
    assert resp.status_code == 200
    assert resp.json()["filename"].endswith(".pdf")


@pytest.mark.asyncio
async def test_upload_unknown_extension_becomes_bin(client, tmp_path):
    """If the file has an unrecognized extension, it should be saved as .bin."""
    with patch("app.api.upload.UPLOAD_DIR", tmp_path):
        resp = await client.post(
            "/api/upload",
            files={"file": ("data.xyz", b"\x00" * 10, "image/png")},
        )
    assert resp.status_code == 200
    assert resp.json()["filename"].endswith(".bin")
