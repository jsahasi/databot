from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SyncedMixin, TimestampMixin


class Event(Base, TimestampMixin, SyncedMixin):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    on24_event_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    client_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Core metadata
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    registration_required: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps from ON24
    live_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    live_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archive_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archive_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    on24_created: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    on24_last_modified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Analytics summary (from event metadata endpoint)
    total_registrants: Mapped[int] = mapped_column(Integer, default=0)
    total_attendees: Mapped[int] = mapped_column(Integer, default=0)
    live_attendees: Mapped[int] = mapped_column(Integer, default=0)
    on_demand_attendees: Mapped[int] = mapped_column(Integer, default=0)
    no_show_count: Mapped[int] = mapped_column(Integer, default=0)
    engagement_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)

    # URLs
    audience_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tags and custom fields
    tags: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Full ON24 API response for future-proofing
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "on24_event_id": self.on24_event_id,
            "title": self.title,
            "description": self.description,
            "event_type": self.event_type,
            "content_type": self.content_type,
            "is_active": self.is_active,
            "live_start": self.live_start.isoformat() if self.live_start else None,
            "live_end": self.live_end.isoformat() if self.live_end else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_registrants": self.total_registrants,
            "total_attendees": self.total_attendees,
            "live_attendees": self.live_attendees,
            "on_demand_attendees": self.on_demand_attendees,
            "no_show_count": self.no_show_count,
            "engagement_score": float(self.engagement_score) if self.engagement_score else None,
            "tags": self.tags,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }
