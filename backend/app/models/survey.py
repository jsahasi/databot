from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SyncedMixin, TimestampMixin


class SurveyResponse(Base, TimestampMixin, SyncedMixin):
    __tablename__ = "survey_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    on24_event_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("events.on24_event_id"), index=True
    )
    survey_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    attendee_email: Mapped[str] = mapped_column(String(255), index=True)
    question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    raw_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "on24_event_id": self.on24_event_id,
            "survey_id": self.survey_id,
            "attendee_email": self.attendee_email,
            "question": self.question,
            "answer": self.answer,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
        }
