"""Sync management endpoints – trigger syncs and view status."""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models import SyncLog
from app.schemas.event import SyncLogSchema, SyncTriggerResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Background sync runner
# ---------------------------------------------------------------------------

async def _run_sync(entity_type: Optional[str] = None) -> None:
    """Run a sync in the background.

    Imports SyncService lazily to avoid circular imports and to allow the
    endpoint to return immediately while the sync runs.
    """
    try:
        from app.services.sync_service import SyncService  # noqa: WPS433

        service = SyncService()
        if entity_type:
            await service.sync_entity(entity_type)
        else:
            await service.sync_all()
    except ImportError:
        logger.error("SyncService not yet implemented – skipping sync execution")
    except Exception:
        logger.exception("Background sync failed")


# ---------------------------------------------------------------------------
# POST /sync/trigger – trigger a full sync
# ---------------------------------------------------------------------------

@router.post("/trigger", response_model=SyncTriggerResponse)
async def trigger_sync():
    """Trigger a full sync of all entities from ON24.

    The sync runs as a background task; this endpoint returns immediately.
    """
    asyncio.create_task(_run_sync())
    return SyncTriggerResponse(
        message="Full sync triggered",
        status="running",
    )


# ---------------------------------------------------------------------------
# POST /sync/trigger/{entity_type} – trigger sync for specific entity
# ---------------------------------------------------------------------------

@router.post("/trigger/{entity_type}", response_model=SyncTriggerResponse)
async def trigger_entity_sync(entity_type: str):
    """Trigger a sync for a specific entity type (e.g. events, attendees, registrants)."""
    valid_types = {"events", "attendees", "registrants", "polls", "surveys", "resources", "ctas"}
    if entity_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity_type '{entity_type}'. Must be one of: {', '.join(sorted(valid_types))}",
        )

    asyncio.create_task(_run_sync(entity_type))
    return SyncTriggerResponse(
        message=f"Sync triggered for {entity_type}",
        status="running",
    )


# ---------------------------------------------------------------------------
# GET /sync/status – latest sync logs
# ---------------------------------------------------------------------------

@router.get("/status", response_model=list[SyncLogSchema])
async def sync_status(
    limit: int = Query(20, ge=1, le=100, description="Number of recent sync logs to return"),
    db: AsyncSession = Depends(get_db),
):
    """Return the most recent sync logs showing current sync state."""
    result = await db.execute(
        select(SyncLog)
        .order_by(SyncLog.started_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return [SyncLogSchema.model_validate(log) for log in logs]
