"""Content sharing and approval models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ContentShare(Base, TimestampMixin):
    __tablename__ = "content_shares"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID string
    content_html: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    admin_id: Mapped[int] = mapped_column(Integer, nullable=False)
    admin_email: Mapped[str] = mapped_column(String(255), nullable=False)
    session_id: Mapped[str] = mapped_column(String(100), default="")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content_html": self.content_html,
            "title": self.title,
            "admin_id": self.admin_id,
            "admin_email": self.admin_email,
            "session_id": self.session_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ShareRecipient(Base, TimestampMixin):
    __tablename__ = "share_recipients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    share_id: Mapped[str] = mapped_column(String(36), ForeignKey("content_shares.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # None=pending
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "share_id": self.share_id,
            "email": self.email,
            "approved": self.approved,
            "rating": self.rating,
            "viewed_at": self.viewed_at.isoformat() if self.viewed_at else None,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ShareComment(Base, TimestampMixin):
    __tablename__ = "share_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    share_id: Mapped[str] = mapped_column(String(36), ForeignKey("content_shares.id"), nullable=False, index=True)
    author_email: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "share_id": self.share_id,
            "author_email": self.author_email,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
