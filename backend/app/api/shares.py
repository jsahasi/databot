"""Content sharing and approval endpoints."""

import hashlib
import html as html_mod
import logging
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.config import settings
from app.db.session import async_session_factory
from app.models.content_share import ContentShare, ShareComment, ShareRecipient
from app.services.email_service import _validate_email, send_email

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Remove HTML tags from text for security."""
    return _HTML_TAG_RE.sub("", text)


def _get_share_secret() -> str:
    """Return the share secret, auto-generating if not set."""
    if not settings.share_secret:
        settings.share_secret = secrets.token_hex(32)
    return settings.share_secret


def _generate_token(
    share_id: str, email: str, admin_id: int, created_at: str, secret: str
) -> str:
    """Generate a deterministic token for a share recipient."""
    payload = f"{secret}:{share_id}:{email}:{admin_id}:{created_at}"
    return hashlib.sha256(payload.encode()).hexdigest()


async def _validate_share_access(
    share_id: str, key: str, email: str, session
) -> tuple[ContentShare, ShareRecipient]:
    """Load and validate share + recipient access.

    Raises HTTPException(404) if not found, 410 if expired, 403 if invalid token.
    """
    share = await session.get(ContentShare, share_id)
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    if share.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Share link has expired")

    result = await session.execute(
        select(ShareRecipient).where(
            ShareRecipient.share_id == share_id,
            ShareRecipient.email == email,
        )
    )
    recipient = result.scalar_one_or_none()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    # Recompute expected token and compare
    expected = _generate_token(
        share_id,
        email,
        share.admin_id,
        share.created_at.isoformat(),
        _get_share_secret(),
    )
    if not secrets.compare_digest(expected, key):
        raise HTTPException(status_code=403, detail="Invalid access token")

    return share, recipient


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class CreateShareRequest(BaseModel):
    content_html: str
    title: str
    recipients: list[str]
    admin_id: int
    admin_email: str
    session_id: str = ""


class RespondRequest(BaseModel):
    approved: bool
    rating: int  # 1-5


class CommentRequest(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("")
async def create_share(req: CreateShareRequest):
    """Create a content share and email recipients."""
    # Validate recipients
    valid_emails = [e.strip() for e in req.recipients if _validate_email(e.strip())]
    if not valid_emails:
        raise HTTPException(status_code=400, detail="No valid recipient emails")

    if not req.content_html.strip():
        raise HTTPException(status_code=400, detail="content_html is required")

    if not req.title.strip():
        raise HTTPException(status_code=400, detail="title is required")

    share_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=7)
    secret = _get_share_secret()

    share = ContentShare(
        id=share_id,
        content_html=req.content_html,
        title=req.title,
        admin_id=req.admin_id,
        admin_email=req.admin_email,
        session_id=req.session_id,
        expires_at=expires_at,
    )

    share_urls: dict[str, str] = {}

    async with async_session_factory() as session:
        session.add(share)
        await session.flush()  # ensure created_at is populated

        created_at_str = share.created_at.isoformat()

        for email in valid_emails:
            token = _generate_token(share_id, email, req.admin_id, created_at_str, secret)
            recipient = ShareRecipient(
                share_id=share_id,
                email=email,
                token_hash=token,
            )
            session.add(recipient)

            url = f"{settings.share_base_url}/share/{share_id}?key={token}&email={email}"
            share_urls[email] = url

        await session.commit()

    # Send emails (fire-and-forget per recipient, don't fail the request)
    for email, url in share_urls.items():
        html_body = f"""
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:600px;margin:0 auto;padding:2rem;">
            <div style="background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 100%);border-radius:12px;padding:2rem;color:#fff;margin-bottom:1.5rem;">
                <h1 style="margin:0 0 0.5rem;font-size:1.5rem;">Content Review Request</h1>
                <p style="margin:0;opacity:0.9;">From {html_mod.escape(req.admin_email)}</p>
            </div>
            <h2 style="color:#1f2937;margin:0 0 1rem;">{html_mod.escape(req.title)}</h2>
            <p style="color:#4b5563;line-height:1.6;">
                You've been invited to review and approve content.
                Click the button below to view the content and provide your feedback.
            </p>
            <div style="text-align:center;margin:2rem 0;">
                <a href="{url}"
                   style="display:inline-block;background:#4f46e5;color:#fff;padding:0.75rem 2rem;
                          border-radius:8px;text-decoration:none;font-weight:600;font-size:1rem;">
                    Review Content
                </a>
            </div>
            <p style="color:#9ca3af;font-size:0.85rem;text-align:center;">
                This link expires in 7 days. Do not forward this email &mdash; the link is unique to you.
            </p>
        </div>
        """
        try:
            await send_email(
                to=email,
                subject=f"Content Review: {req.title}",
                html_body=html_body,
            )
        except Exception:
            logger.exception(f"Failed to send share email to {email}")

    return {
        "share_id": share_id,
        "share_urls": share_urls,
        "recipients_count": len(valid_emails),
    }


@router.get("/{share_id}")
async def get_share(share_id: str, key: str, email: str):
    """Get share details, recipients, and comments. Validates access token."""
    async with async_session_factory() as session:
        share, recipient = await _validate_share_access(share_id, key, email, session)

        # Mark first view
        if not recipient.viewed_at:
            recipient.viewed_at = datetime.now(timezone.utc)
            await session.commit()

        # Load all recipients
        result = await session.execute(
            select(ShareRecipient).where(ShareRecipient.share_id == share_id)
        )
        recipients = result.scalars().all()

        # Load all comments
        result = await session.execute(
            select(ShareComment)
            .where(ShareComment.share_id == share_id)
            .order_by(ShareComment.created_at.asc())
        )
        comments = result.scalars().all()

        all_responded = all(r.approved is not None for r in recipients)
        all_approved = all_responded and all(r.approved is True for r in recipients)

        return {
            "share": share.to_dict(),
            "recipients": [r.to_dict() for r in recipients],
            "comments": [c.to_dict() for c in comments],
            "all_approved": all_approved,
            "all_responded": all_responded,
        }


@router.post("/{share_id}/respond")
async def respond_to_share(share_id: str, key: str, email: str, req: RespondRequest):
    """Submit approval decision and rating for a share."""
    if req.rating < 1 or req.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    async with async_session_factory() as session:
        share, recipient = await _validate_share_access(share_id, key, email, session)

        recipient.approved = req.approved
        recipient.rating = req.rating
        recipient.responded_at = datetime.now(timezone.utc)
        await session.commit()

    return {"status": "ok", "approved": req.approved, "rating": req.rating}


@router.post("/{share_id}/comments")
async def add_comment(share_id: str, key: str, email: str, req: CommentRequest):
    """Add a comment to a share."""
    content = _strip_html(req.content).strip()
    if not content:
        raise HTTPException(status_code=400, detail="Comment content is required")

    async with async_session_factory() as session:
        share, recipient = await _validate_share_access(share_id, key, email, session)

        comment = ShareComment(
            share_id=share_id,
            author_email=email,
            content=content,
        )
        session.add(comment)
        await session.commit()

        return comment.to_dict()
