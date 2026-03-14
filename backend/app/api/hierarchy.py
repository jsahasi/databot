"""Account hierarchy API — breadcrumb path + children for the account switcher."""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.db.on24_hierarchy import (
    get_allowed_client_ids,
    get_client_children,
    get_client_path,
    get_hierarchy_pool,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/hierarchy")
async def get_hierarchy(client_id: int | None = Query(default=None)):
    """Return breadcrumb path from root to client_id plus its direct children.

    Response shape:
    {
        "root_client_id": 10710,
        "path": [{"client_id": int, "company_name": str}, ...],   # root → client
        "children": [{"client_id": int, "company_name": str}, ...],
        "db_mode": "PROD" | "QA"
    }
    """
    root_id = int(settings.on24_client_id)
    try:
        pool, db_mode = await get_hierarchy_pool()
    except Exception as e:
        logger.error(f"Hierarchy pool unavailable: {e}")
        raise HTTPException(status_code=503, detail="ON24 database unavailable")

    effective = client_id if client_id is not None else root_id

    # Validate: the requested client must be within this deployment's hierarchy
    if effective != root_id:
        allowed = await get_allowed_client_ids(pool, root_id)
        if effective not in allowed:
            raise HTTPException(status_code=404, detail="Client not found in hierarchy")

    path = await get_client_path(effective, root_id, pool)
    children = await get_client_children(effective, pool)

    return {
        "root_client_id": root_id,
        "path": path,
        "children": children,
        "db_mode": db_mode,
    }


@router.get("/hierarchy/children/{client_id}")
async def get_children(client_id: int):
    """Return direct children of a client node."""
    try:
        pool, db_mode = await get_hierarchy_pool()
    except Exception as e:
        logger.error(f"Hierarchy pool unavailable: {e}")
        raise HTTPException(status_code=503, detail="ON24 database unavailable")

    children = await get_client_children(client_id, pool)
    return {"children": children, "db_mode": db_mode}


