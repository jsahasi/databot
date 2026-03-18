from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Pagination wrapper
# ---------------------------------------------------------------------------


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    per_page: int

    @property
    def total_pages(self) -> int:
        return (self.total + self.per_page - 1) // self.per_page if self.per_page else 0


# ---------------------------------------------------------------------------
# Event schemas
# ---------------------------------------------------------------------------


class EventSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    on24_event_id: int
    title: str
    event_type: str | None = None
    is_active: bool
    live_start: datetime | None = None
    live_end: datetime | None = None
    total_registrants: int = 0
    total_attendees: int = 0
    engagement_score: float | None = None


class EventDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    on24_event_id: int
    title: str
    description: str | None = None
    event_type: str | None = None
    content_type: str | None = None
    language: str | None = None
    timezone: str | None = None
    is_active: bool
    registration_required: bool = True
    live_start: datetime | None = None
    live_end: datetime | None = None
    archive_start: datetime | None = None
    archive_end: datetime | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    on24_created: datetime | None = None
    on24_last_modified: datetime | None = None
    total_registrants: int = 0
    total_attendees: int = 0
    live_attendees: int = 0
    on_demand_attendees: int = 0
    no_show_count: int = 0
    engagement_score: float | None = None
    audience_url: str | None = None
    report_url: str | None = None
    tags: dict[str, Any] | None = None
    synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Attendee / Registrant schemas
# ---------------------------------------------------------------------------


class AttendeeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    on24_attendee_id: int
    on24_event_id: int
    email: str
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    live_minutes: int | None = None
    archive_minutes: int | None = None
    engagement_score: float | None = None
    asked_questions: int = 0
    resources_downloaded: int = 0
    answered_polls: int = 0
    answered_surveys: int = 0
    launch_mode: str | None = None


class RegistrantSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    on24_registrant_id: int
    on24_event_id: int
    email: str
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    job_title: str | None = None
    city: str | None = None
    country: str | None = None
    registration_status: str | None = None
    registration_date: datetime | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None


# ---------------------------------------------------------------------------
# Engagement sub-entity schemas
# ---------------------------------------------------------------------------


class PollResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    on24_event_id: int
    poll_id: int | None = None
    attendee_email: str
    question: str | None = None
    answer: str | None = None
    responded_at: datetime | None = None


class SurveyResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    on24_event_id: int
    survey_id: int | None = None
    attendee_email: str
    question: str | None = None
    answer: str | None = None
    responded_at: datetime | None = None


class ResourceViewedSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    on24_event_id: int
    attendee_email: str
    resource_name: str | None = None
    resource_type: str | None = None
    viewed_at: datetime | None = None


class CTAClickSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    on24_event_id: int
    attendee_email: str
    cta_name: str | None = None
    cta_url: str | None = None
    clicked_at: datetime | None = None


# ---------------------------------------------------------------------------
# Analytics schemas
# ---------------------------------------------------------------------------


class DashboardKPI(BaseModel):
    total_events: int
    total_attendees: int
    total_registrants: int
    avg_engagement_score: float | None = None
    conversion_rate: float | None = Field(None, description="Percentage of registrants who attended")


class TrendPoint(BaseModel):
    period: str  # e.g. "2025-03"
    events: int = 0
    attendees: int = 0
    avg_engagement: float | None = None


class TopEvent(BaseModel):
    on24_event_id: int
    title: str
    total_attendees: int = 0
    engagement_score: float | None = None
    live_start: datetime | None = None


# ---------------------------------------------------------------------------
# Audience analytics schemas
# ---------------------------------------------------------------------------


class CompanyAudience(BaseModel):
    company: str
    events_attended: int
    total_attendances: int
    avg_engagement: float | None = None


class AudienceAnalytics(BaseModel):
    top_companies: list[CompanyAudience]
    registration_sources: list[dict]
    country_distribution: list[dict]


# ---------------------------------------------------------------------------
# Content performance schemas
# ---------------------------------------------------------------------------


class ContentTypePerformance(BaseModel):
    event_type: str
    event_count: int
    avg_attendees: float
    avg_engagement: float | None = None
    avg_conversion_rate: float | None = None


class ContentPerformance(BaseModel):
    by_type: list[ContentTypePerformance]
    top_events: list[TopEvent]


# ---------------------------------------------------------------------------
# Heatmap schema
# ---------------------------------------------------------------------------


class HeatmapPoint(BaseModel):
    day: int  # 0 = Monday … 6 = Sunday (ISO dow - 1)
    hour: int  # 0-23
    avg_engagement: float
    event_count: int


# ---------------------------------------------------------------------------
# Sync schemas
# ---------------------------------------------------------------------------


class SyncTriggerResponse(BaseModel):
    message: str
    status: str


class SyncLogSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    on24_event_id: int | None = None
    status: str
    records_synced: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
