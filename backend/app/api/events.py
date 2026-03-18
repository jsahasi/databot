"""Event endpoints with filtering, pagination, sorting, and sub-entity access."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models import (
    Attendee,
    CTAClick,
    Event,
    PollResponse,
    Registrant,
    ResourceViewed,
    SurveyResponse,
)
from app.schemas.event import (
    AttendeeSummary,
    CTAClickSchema,
    EventDetail,
    EventSummary,
    PaginatedResponse,
    PollResponseSchema,
    RegistrantSummary,
    ResourceViewedSchema,
    SurveyResponseSchema,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper – validate event exists and return on24_event_id
# ---------------------------------------------------------------------------


async def _get_event_or_404(event_id: int, db: AsyncSession) -> Event:
    result = await db.execute(select(Event).where(Event.on24_event_id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


# ---------------------------------------------------------------------------
# GET /events – list with filtering, pagination, sorting
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse[EventSummary])
async def list_events(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page"),
    status: str | None = Query(None, description="Filter by status: active, inactive, all"),
    date_from: datetime | None = Query(None, description="Events starting after this date"),
    date_to: datetime | None = Query(None, description="Events starting before this date"),
    search: str | None = Query(None, description="Search by event title"),
    sort_by: str = Query("live_start", description="Sort field: live_start, title, total_attendees, engagement_score"),
    sort_order: str = Query("desc", description="Sort direction: asc or desc"),
    db: AsyncSession = Depends(get_db),
):
    """List events with optional filtering, pagination, and sorting."""
    query = select(Event)

    # -- Filters --
    if status == "active":
        query = query.where(Event.is_active.is_(True))
    elif status == "inactive":
        query = query.where(Event.is_active.is_(False))

    if date_from is not None:
        query = query.where(Event.live_start >= date_from)
    if date_to is not None:
        query = query.where(Event.live_start <= date_to)

    if search:
        query = query.where(Event.title.ilike(f"%{search}%"))

    # -- Count (before pagination) --
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # -- Sorting --
    sort_column_map = {
        "live_start": Event.live_start,
        "title": Event.title,
        "total_attendees": Event.total_attendees,
        "engagement_score": Event.engagement_score,
        "created_at": Event.created_at,
    }
    sort_col = sort_column_map.get(sort_by, Event.live_start)
    if sort_order.lower() == "asc":
        query = query.order_by(sort_col.asc().nullslast())
    else:
        query = query.order_by(sort_col.desc().nullslast())

    # -- Pagination --
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    events = result.scalars().all()

    return PaginatedResponse[EventSummary](
        items=[EventSummary.model_validate(e) for e in events],
        total=total,
        page=page,
        per_page=per_page,
    )


# ---------------------------------------------------------------------------
# GET /events/{event_id} – event detail with summary stats
# ---------------------------------------------------------------------------


@router.get("/{event_id}", response_model=EventDetail)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """Return full event detail including summary statistics."""
    event = await _get_event_or_404(event_id, db)
    return EventDetail.model_validate(event)


# ---------------------------------------------------------------------------
# GET /events/{event_id}/attendees
# ---------------------------------------------------------------------------


@router.get("/{event_id}/attendees", response_model=PaginatedResponse[AttendeeSummary])
async def list_event_attendees(
    event_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: str | None = Query(None, description="Search by email or company"),
    db: AsyncSession = Depends(get_db),
):
    """List attendees for a specific event with pagination."""
    await _get_event_or_404(event_id, db)

    query = select(Attendee).where(Attendee.on24_event_id == event_id)

    if search:
        query = query.where(Attendee.email.ilike(f"%{search}%") | Attendee.company.ilike(f"%{search}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Attendee.engagement_score.desc().nullslast())
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    attendees = result.scalars().all()

    return PaginatedResponse[AttendeeSummary](
        items=[AttendeeSummary.model_validate(a) for a in attendees],
        total=total,
        page=page,
        per_page=per_page,
    )


# ---------------------------------------------------------------------------
# GET /events/{event_id}/registrants
# ---------------------------------------------------------------------------


@router.get("/{event_id}/registrants", response_model=PaginatedResponse[RegistrantSummary])
async def list_event_registrants(
    event_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: str | None = Query(None, description="Search by email or company"),
    db: AsyncSession = Depends(get_db),
):
    """List registrants for a specific event with pagination."""
    await _get_event_or_404(event_id, db)

    query = select(Registrant).where(Registrant.on24_event_id == event_id)

    if search:
        query = query.where(Registrant.email.ilike(f"%{search}%") | Registrant.company.ilike(f"%{search}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Registrant.registration_date.desc().nullslast())
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    registrants = result.scalars().all()

    return PaginatedResponse[RegistrantSummary](
        items=[RegistrantSummary.model_validate(r) for r in registrants],
        total=total,
        page=page,
        per_page=per_page,
    )


# ---------------------------------------------------------------------------
# GET /events/{event_id}/polls
# ---------------------------------------------------------------------------


@router.get("/{event_id}/polls", response_model=PaginatedResponse[PollResponseSchema])
async def list_event_polls(
    event_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """Return all poll responses for an event with pagination."""
    await _get_event_or_404(event_id, db)

    query = select(PollResponse).where(PollResponse.on24_event_id == event_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(PollResponse.responded_at.desc().nullslast()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)

    return PaginatedResponse[PollResponseSchema](
        items=[PollResponseSchema.model_validate(p) for p in result.scalars().all()],
        total=total,
        page=page,
        per_page=per_page,
    )


# ---------------------------------------------------------------------------
# GET /events/{event_id}/surveys
# ---------------------------------------------------------------------------


@router.get("/{event_id}/surveys", response_model=PaginatedResponse[SurveyResponseSchema])
async def list_event_surveys(
    event_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """Return all survey responses for an event with pagination."""
    await _get_event_or_404(event_id, db)

    query = select(SurveyResponse).where(SurveyResponse.on24_event_id == event_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(SurveyResponse.responded_at.desc().nullslast()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)

    return PaginatedResponse[SurveyResponseSchema](
        items=[SurveyResponseSchema.model_validate(s) for s in result.scalars().all()],
        total=total,
        page=page,
        per_page=per_page,
    )


# ---------------------------------------------------------------------------
# GET /events/{event_id}/resources
# ---------------------------------------------------------------------------


@router.get("/{event_id}/resources", response_model=PaginatedResponse[ResourceViewedSchema])
async def list_event_resources(
    event_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """Return all resources viewed for an event with pagination."""
    await _get_event_or_404(event_id, db)

    query = select(ResourceViewed).where(ResourceViewed.on24_event_id == event_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(ResourceViewed.viewed_at.desc().nullslast()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)

    return PaginatedResponse[ResourceViewedSchema](
        items=[ResourceViewedSchema.model_validate(r) for r in result.scalars().all()],
        total=total,
        page=page,
        per_page=per_page,
    )


# ---------------------------------------------------------------------------
# GET /events/{event_id}/ctas
# ---------------------------------------------------------------------------


@router.get("/{event_id}/ctas", response_model=PaginatedResponse[CTAClickSchema])
async def list_event_ctas(
    event_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """Return all CTA clicks for an event with pagination."""
    await _get_event_or_404(event_id, db)

    query = select(CTAClick).where(CTAClick.on24_event_id == event_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(CTAClick.clicked_at.desc().nullslast()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)

    return PaginatedResponse[CTAClickSchema](
        items=[CTAClickSchema.model_validate(c) for c in result.scalars().all()],
        total=total,
        page=page,
        per_page=per_page,
    )
