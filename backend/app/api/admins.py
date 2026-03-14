"""Admin users endpoint — returns active admins for the current client."""

import logging

from fastapi import APIRouter

from app.db.on24_db import get_pool, get_tenant_client_ids

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/admins")
async def list_admins():
    """Return active admin users for the current client hierarchy."""
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    sql = """
        SELECT DISTINCT a.admin_id, a.email, a.firstname, a.lastname
        FROM on24master.admin a
        JOIN on24master.admin_x_client axc ON a.admin_id = axc.admin_id
        WHERE axc.client_id = ANY($1::bigint[])
          AND a.is_active = 'Y'
        ORDER BY a.lastname, a.firstname
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, client_ids, timeout=8.0)

    return {
        "admins": [
            {
                "admin_id": r["admin_id"],
                "email": r["email"],
                "name": f"{r['firstname'] or ''} {r['lastname'] or ''}".strip(),
            }
            for r in rows
        ]
    }
