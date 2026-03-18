"""File upload endpoint: accepts PDF and image files, stores in temp folder with daily cleanup."""

import logging
import os
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Temp upload directory — Docker volume or local
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "data/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Allowed MIME types
ALLOWED_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def cleanup_old_uploads(max_age_hours: int = 24) -> int:
    """Delete files older than max_age_hours. Returns count of deleted files."""
    cutoff = time.time() - (max_age_hours * 3600)
    deleted = 0
    for f in UPLOAD_DIR.iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink()
            deleted += 1
    if deleted:
        logger.info(f"Cleaned up {deleted} expired upload(s)")
    return deleted


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a PDF or image file. Returns filename and access URL."""
    # Validate content type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="File type not allowed. Accepted: PDF, PNG, JPEG, GIF, WEBP",
        )

    # Read and validate size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    # Generate unique filename preserving extension
    ext = Path(file.filename or "file").suffix.lower()
    if ext not in {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        ext = ".bin"
    unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
    dest = UPLOAD_DIR / unique_name

    dest.write_bytes(contents)
    logger.info(f"Uploaded: {file.filename} -> {unique_name} ({len(contents)} bytes)")

    # Extract text for PDFs so the LLM can read the content
    extracted_text = None
    if file.content_type == "application/pdf":
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=contents, filetype="pdf")
            pages = []
            for page in doc:
                pages.append(page.get_text())
            doc.close()
            extracted_text = "\n\n".join(pages).strip()
            if len(extracted_text) > 8000:
                extracted_text = extracted_text[:8000] + "\n...(truncated)"
        except ImportError:
            logger.warning("PyMuPDF not installed — PDF text extraction unavailable")
        except Exception as e:
            logger.warning(f"PDF text extraction failed: {e}")

    return {
        "filename": unique_name,
        "original_name": file.filename,
        "url": f"/api/uploads/{unique_name}",
        "size": len(contents),
        "content_type": file.content_type,
        "extracted_text": extracted_text,
    }


@router.get("/uploads/{filename}")
async def serve_upload(filename: str):
    """Serve an uploaded file."""
    # Sanitize: only allow simple filenames (no path traversal)
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = UPLOAD_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)
