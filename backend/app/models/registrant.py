from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SyncedMixin, TimestampMixin


class Registrant(Base, TimestampMixin, SyncedMixin):
    __tablename__ = "registrants"
    __table_args__ = (
        UniqueConstraint("on24_registrant_id", "on24_event_id", name="uq_registrant_event"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    on24_registrant_id: Mapped[int] = mapped_column(BigInteger, index=True)
    on24_event_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("events.on24_event_id"), index=True
    )

    # Contact info
    email: Mapped[str] = mapped_column(String(255), index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_function: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Location
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Contact details
    work_phone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    company_industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    company_size: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Tracking
    partner_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    registration_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    registration_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_activity: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # UTM fields
    utm_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Custom fields (std1-std10 from ON24)
    custom_fields: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Full API response
    raw_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

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
            "registration_date": (
                self.registration_date.isoformat() if self.registration_date else None
            ),
            "utm_source": self.utm_source,
            "utm_medium": self.utm_medium,
            "utm_campaign": self.utm_campaign,
        }
