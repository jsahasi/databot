from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SyncedMixin, TimestampMixin


class PollResponse(Base, TimestampMixin, SyncedMixin):
    __tablename__ = "poll_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    on24_event_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("events.on24_event_id"), index=True)
    poll_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    attendee_email: Mapped[str] = mapped_column(String(255), index=True)
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "on24_event_id": self.on24_event_id,
            "poll_id": self.poll_id,
            "attendee_email": self.attendee_email,
            "question": self.question,
            "answer": self.answer,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
        }
