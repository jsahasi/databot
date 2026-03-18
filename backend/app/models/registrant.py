from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SyncedMixin, TimestampMixin


class Registrant(Base, TimestampMixin, SyncedMixin):
    __tablename__ = "registrants"
    __table_args__ = (UniqueConstraint("on24_registrant_id", "on24_event_id", name="uq_registrant_event"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    on24_registrant_id: Mapped[int] = mapped_column(BigInteger, index=True)
    on24_event_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("events.on24_event_id"), index=True)

    # Contact info
    email: Mapped[str] = mapped_column(String(255), index=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_function: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Location
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Contact details
    work_phone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_size: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Tracking
    partner_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    registration_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    registration_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # UTM fields
    utm_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Custom fields (std1-std10 from ON24)
    custom_fields: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Full API response
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "on24_registrant_id": self.on24_registrant_id,
            "on24_event_id": self.on24_event_id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "company": self.company,
            "job_title": self.job_title,
            "city": self.city,
            "country": self.country,
            "registration_status": self.registration_status,
            "registration_date": (self.registration_date.isoformat() if self.registration_date else None),
            "utm_source": self.utm_source,
            "utm_medium": self.utm_medium,
            "utm_campaign": self.utm_campaign,
        }
