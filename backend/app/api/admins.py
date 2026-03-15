"""Admin users endpoint — returns active admins for the current client."""

import logging

from fastapi import APIRouter, HTTPException

from app.db.on24_db import get_pool, get_tenant_client_ids
from app.services.on24_client import ON24Client

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/admins")
async def list_admins():
    """Return active admin users for the current client hierarchy."""
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    sql = """
        SELECT DISTINCT a.admin_id, a.email, a.firstname, a.lastname,
               axp.admin_profile_name AS profile
        FROM on24master.admin a
        JOIN on24master.admin_x_client axc ON a.admin_id = axc.admin_id
        LEFT JOIN on24master.admin_x_profile axp
          ON axp.admin_id = a.admin_id AND axp.is_active = 'Y'
        WHERE axc.client_id = ANY($1::bigint[])
          AND a.is_active = 'Y'
          AND (axp.admin_profile_name IS NULL OR axp.admin_profile_name != 'Event Admin')
        ORDER BY a.lastname, a.firstname
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, client_ids, timeout=8.0)

    return {"admins": [
            {
                "admin_id": r["admin_id"],
                "email": r["email"],
                "name": f"{r['firstname'] or ''} {r['lastname'] or ''}".strip(),
                "profile": r["profile"] or "User",
            }
            for r in rows
        ]
    }


@router.get("/admins/{admin_id}/permissions")
async def get_admin_permissions(admin_id: int):
    """Return active permission prop_codes for an admin (value='Yes')."""
    client_ids = await get_tenant_client_ids()
    pool = await get_pool()

    # Verify admin belongs to this client hierarchy
    check_sql = """
        SELECT 1 FROM on24master.admin_x_client
        WHERE admin_id = $1 AND client_id = ANY($2::bigint[])
        LIMIT 1
    """
    async with pool.acquire() as conn:
        exists = await conn.fetchrow(check_sql, admin_id, client_ids, timeout=5.0)
        if not exists:
            raise HTTPException(status_code=404, detail="Admin not found")

        sql = """
            SELECT prop_code
            FROM on24master.admin_property_info
            WHERE admin_id = $1 AND value = 'Yes'
            ORDER BY prop_code
        """
        rows = await conn.fetch(sql, admin_id, timeout=5.0)

    return {
        "admin_id": admin_id,
        "permissions": [r["prop_code"] for r in rows],
    }


@router.get("/technicalrep")
async def get_technical_contacts():
    """Return technical rep contacts for the current client via ON24 REST API."""
    try:
        client = ON24Client()
        result = await client._request("GET", "technicalrep")
        await client.close()
        contacts = result.get("technicalcontacts", [])
        return {
            "contacts": [
                {"id": c.get("contactid"), "name": c.get("contactname", "")}
                for c in contacts
            ]
        }
    except Exception as e:
        logger.warning(f"Technical rep lookup failed: {e}")
        return {"contacts": []}
