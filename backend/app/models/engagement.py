from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SyncedMixin, TimestampMixin


class ViewingSession(Base, TimestampMixin, SyncedMixin):
    __tablename__ = "viewing_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    attendee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("attendees.id"), nullable=True, index=True
    )
    on24_event_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("events.on24_event_id"), index=True
    )
    email: Mapped[str] = mapped_column(String(255), index=True)
    session_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    session_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    session_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    raw_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "on24_event_id": self.on24_event_id,
            "email": self.email,
            "session_type": self.session_type,
            "session_start": self.session_start.isoformat() if self.session_start else None,
            "session_end": self.session_end.isoformat() if self.session_end else None,
            "duration_seconds": self.duration_seconds,
        }


class ResourceViewed(Base, TimestampMixin, SyncedMixin):
    __tablename__ = "resources_viewed"

    id: Mapped[int] = mapped_column(primary_key=True)
    on24_event_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("events.on24_event_id"), index=True
    )
    attendee_email: Mapped[str] = mapped_column(String(255), index=True)
    resource_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    viewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    raw_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "on24_event_id": self.on24_event_id,
            "attendee_email": self.attendee_email,
            "resource_name": self.resource_name,
            "resource_type": self.resource_type,
            "viewed_at": self.viewed_at.isoformat() if self.viewed_at else None,
        }


class CTAClick(Base, TimestampMixin, SyncedMixin):
    __tablename__ = "cta_clicks"

    id: Mapped[int] = mapped_column(primary_key=True)
    on24_event_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("events.on24_event_id"), index=True
    )
    attendee_email: Mapped[str] = mapped_column(String(255), index=True)
    cta_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cta_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    clicked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    raw_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "on24_event_id": self.on24_event_id,
            "attendee_email": self.attendee_email,
            "cta_name": self.cta_name,
            "cta_url": self.cta_url,
            "clicked_at": self.clicked_at.isoformat() if self.clicked_at else None,
        }


class EngagementProfile(Base, TimestampMixin, SyncedMixin):
    """Cross-event engagement profile (PEP data from ON24)."""

    __tablename__ = "engagement_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    total_events_attended: Mapped[int] = mapped_column(Integer, default=0)
    total_engagement_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    last_event_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pep_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "company": self.company,
            "total_events_attended": self.total_events_attended,
            "total_engagement_score": (
                float(self.total_engagement_score) if self.total_engagement_score else None
            ),
            "last_event_date": (
                self.last_event_date.isoformat() if self.last_event_date else None
            ),
        }
