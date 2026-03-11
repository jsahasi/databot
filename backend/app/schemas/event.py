from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

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
    event_type: Optional[str] = None
    is_active: bool
    live_start: Optional[datetime] = None
    live_end: Optional[datetime] = None
    total_registrants: int = 0
    total_attendees: int = 0
    engagement_score: Optional[float] = None


class EventDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    on24_event_id: int
    title: str
    description: Optional[str] = None
    event_type: Optional[str] = None
    content_type: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    is_active: bool
    registration_required: bool = True
    live_start: Optional[datetime] = None
    live_end: Optional[datetime] = None
    archive_start: Optional[datetime] = None
    archive_end: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    on24_created: Optional[datetime] = None
    on24_last_modified: Optional[datetime] = None
    total_registrants: int = 0
    total_attendees: int = 0
    live_attendees: int = 0
    on_demand_attendees: int = 0
    no_show_count: int = 0
    engagement_score: Optional[float] = None
    audience_url: Optional[str] = None
    report_url: Optional[str] = None
    tags: Optional[dict[str, Any]] = None
    synced_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Attendee / Registrant schemas
# ---------------------------------------------------------------------------

class AttendeeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    on24_attendee_id: int
    on24_event_id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    live_minutes: Optional[int] = None
    archive_minutes: Optional[int] = None
    engagement_score: Optional[float] = None
    asked_questions: int = 0
    resources_downloaded: int = 0
    answered_polls: int = 0
    answered_surveys: int = 0
    launch_mode: Optional[str] = None


class RegistrantSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    on24_registrant_id: int
    on24_event_id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    registration_status: Optional[str] = None
    registration_date: Optional[datetime] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


# ---------------------------------------------------------------------------
# Engagement sub-entity schemas
# ---------------------------------------------------------------------------

class PollResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    on24_event_id: int
    poll_id: Optional[int] = None
    attendee_email: str
    question: Optional[str] = None
    answer: Optional[str] = None
    responded_at: Optional[datetime] = None


class SurveyResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    on24_event_id: int
    survey_id: Optional[int] = None
    attendee_email: str
    question: Optional[str] = None
    answer: Optional[str] = None
    responded_at: Optional[datetime] = None


class ResourceViewedSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    on24_event_id: int
    attendee_email: str
    resource_name: Optional[str] = None
    resource_type: Optional[str] = None
    viewed_at: Optional[datetime] = None


class CTAClickSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    on24_event_id: int
    attendee_email: str
    cta_name: Optional[str] = None
    cta_url: Optional[str] = None
    clicked_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Analytics schemas
# ---------------------------------------------------------------------------

class DashboardKPI(BaseModel):
    total_events: int
    total_attendees: int
    total_registrants: int
    avg_engagement_score: Optional[float] = None
    conversion_rate: Optional[float] = Field(
        None, description="Percentage of registrants who attended"
    )


class TrendPoint(BaseModel):
    period: str  # e.g. "2025-03"
    events: int = 0
    attendees: int = 0
    avg_engagement: Optional[float] = None


class TopEvent(BaseModel):
    on24_event_id: int
    title: str
    total_attendees: int = 0
    engagement_score: Optional[float] = None
    live_start: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Audience analytics schemas
# ---------------------------------------------------------------------------

class CompanyAudience(BaseModel):
    company: str
    events_attended: int
    total_attendances: int
    avg_engagement: Optional[float] = None


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
    avg_engagement: Optional[float] = None
    avg_conversion_rate: Optional[float] = None


class ContentPerformance(BaseModel):
    by_type: list[ContentTypePerformance]
    top_events: list[TopEvent]


# ---------------------------------------------------------------------------
# Heatmap schema
# ---------------------------------------------------------------------------

class HeatmapPoint(BaseModel):
    day: int   # 0 = Monday … 6 = Sunday (ISO dow - 1)
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
    on24_event_id: Optional[int] = None
    status: str
    records_synced: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
