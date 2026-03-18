from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SyncedMixin, TimestampMixin


class Attendee(Base, TimestampMixin, SyncedMixin):
    __tablename__ = "attendees"
    __table_args__ = (UniqueConstraint("on24_attendee_id", "on24_event_id", name="uq_attendee_event"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    on24_attendee_id: Mapped[int] = mapped_column(BigInteger, index=True)
    on24_event_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("events.on24_event_id"), index=True)

    # Contact info
    email: Mapped[str] = mapped_column(String(255), index=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Attendance metrics
    join_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    leave_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    live_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    archive_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cumulative_live_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cumulative_archive_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Engagement
    engagement_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    asked_questions: Mapped[int] = mapped_column(Integer, default=0)
    resources_downloaded: Mapped[int] = mapped_column(Integer, default=0)
    answered_polls: Mapped[int] = mapped_column(Integer, default=0)
    answered_surveys: Mapped[int] = mapped_column(Integer, default=0)
    launch_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Nested engagement data
    questions: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    polls: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    resources: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    surveys: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    call_to_actions: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Full API response
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "on24_attendee_id": self.on24_attendee_id,
            "on24_event_id": self.on24_event_id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "company": self.company,
            "live_minutes": self.live_minutes,
            "archive_minutes": self.archive_minutes,
            "engagement_score": (float(self.engagement_score) if self.engagement_score else None),
            "asked_questions": self.asked_questions,
            "resources_downloaded": self.resources_downloaded,
            "answered_polls": self.answered_polls,
            "answered_surveys": self.answered_surveys,
            "launch_mode": self.launch_mode,
        }
