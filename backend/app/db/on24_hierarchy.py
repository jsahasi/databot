"""ON24 client hierarchy queries with PROD → QA fallback.

Used exclusively by the hierarchy API endpoint — not by agent query tools.
"""

import asyncio
import logging
import os
import shutil
import ssl
import tempfile

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

_qa_pool: asyncpg.Pool | None = None
_qa_pool_lock = asyncio.Lock()
_cached_db_mode: str | None = None


def _unescape(s: str) -> str:
    return s.replace("\\n", "\n").strip('"').strip("'")


def _build_ssl_ctx(root_cert: str, cert: str, key: str) -> ssl.SSLContext | None:
    if not root_cert:
        return None
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_REQUIRED
    tmp = tempfile.mkdtemp()
    try:
        paths = {
            "ca.pem": _unescape(root_cert),
            "client.crt": _unescape(cert),
            "client.key": _unescape(key),
        }
        for name, content in paths.items():
            with open(os.path.join(tmp, name), "w", newline="\n") as f:
                f.write(content)
        ctx.load_verify_locations(os.path.join(tmp, "ca.pem"))
        ctx.load_cert_chain(os.path.join(tmp, "client.crt"), os.path.join(tmp, "client.key"))
    finally:
        # Certs are loaded into the SSLContext in memory; remove temp files immediately
        shutil.rmtree(tmp, ignore_errors=True)
    return ctx


def _parse_url(url: str) -> tuple[str, str, str, int, str]:
    url = url.replace("postgresql+asyncpg://", "")
    userpass, hostdb = url.split("@", 1)
    user, password = userpass.split(":", 1)
    hostport, database = hostdb.split("/", 1)
    host, port = hostport.rsplit(":", 1)
    return user, password, host, int(port), database


async def _make_pool(db_url: str, ssl_ctx: ssl.SSLContext | None) -> asyncpg.Pool:
    user, password, host, port, database = _parse_url(db_url)
    return await asyncpg.create_pool(
        host=host, port=port, database=database,
        user=user, password=password, ssl=ssl_ctx,
        min_size=1, max_size=5, command_timeout=30,
    )


async def get_hierarchy_pool() -> tuple[asyncpg.Pool, str]:
    """Return (pool, 'PROD'|'QA').  Tries PROD first, falls back to QA."""
    global _qa_pool, _cached_db_mode

    # Try PROD
    try:
        from app.db.on24_db import get_pool  # shared PROD pool
        pool = await asyncio.wait_for(get_pool(), timeout=5.0)
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1", timeout=3)
        _cached_db_mode = "PROD"
        return pool, "PROD"
    except Exception as e:
        logger.warning(f"PROD ON24 DB unavailable for hierarchy, trying QA: {e}")

    if not settings.on24_db_url_qa:
        raise RuntimeError("PROD ON24 DB unavailable and ON24_DB_URL_QA is not configured")

    if _qa_pool is None:
        async with _qa_pool_lock:
            if _qa_pool is None:
                # QA certs: use QA-specific if provided, else reuse PROD root cert
                ssl_ctx = _build_ssl_ctx(
                    settings.db_pg_ssl_root_cert_content,
                    settings.db_pg_ssl_cert_content_qa or settings.db_pg_ssl_cert_content,
                    settings.db_pg_ssl_key_content_qa or settings.db_pg_ssl_key_content,
                )
                _qa_pool = await _make_pool(settings.on24_db_url_qa, ssl_ctx)

    _cached_db_mode = "QA"
    return _qa_pool, "QA"


async def get_client_info(client_id: int, pool: asyncpg.Pool) -> dict | None:
    try:
        row = await pool.fetchrow(
            "SELECT client_id, company_name FROM on24master.client WHERE client_id = $1",
            client_id, timeout=5,
        )
        return {"client_id": row["client_id"], "company_name": row["company_name"]} if row else None
    except Exception as e:
        logger.warning(f"get_client_info({client_id}): {e}")
        return None


async def get_client_children(client_id: int, pool: asyncpg.Pool) -> list[dict]:
    try:
        rows = await pool.fetch(
            """
            SELECT ch.sub_client_id AS client_id, c.company_name
            FROM on24master.client_hierarchy ch
            JOIN on24master.client c ON c.client_id = ch.sub_client_id
            WHERE ch.client_id = $1
              AND ch.sub_client_id != ch.client_id
            ORDER BY c.company_name
            """,
            client_id, timeout=8,
        )
        return [{"client_id": r["client_id"], "company_name": r["company_name"]} for r in rows]
    except Exception as e:
        logger.warning(f"get_client_children({client_id}): {e}")
        return []


async def get_client_path(client_id: int, root_id: int, pool: asyncpg.Pool) -> list[dict]:
    """Return [{client_id, company_name}] from root down to client_id, inclusive."""
    # Walk upward from client_id to root_id iteratively (hierarchy is shallow)
    path_ids: list[int] = [client_id]
    current = client_id

    for _ in range(10):
        if current == root_id:
            break
        try:
            # A sub_client can have multiple parent entries in client_hierarchy.
            # Prefer the root (shortest path) or the one closest to root.
            # ORDER BY: root_id first, then smallest client_id as tiebreaker.
            row = await pool.fetchrow(
                """
                SELECT client_id FROM on24master.client_hierarchy
                WHERE sub_client_id = $1
                  AND client_id != sub_client_id
                ORDER BY (client_id = $2) DESC, client_id ASC
                LIMIT 1
                """,
                current, root_id, timeout=5,
            )
        except Exception as e:
            logger.warning(f"Path walk at {current}: {e}")
            break
        if not row:
            break
        parent = row["client_id"]
        if parent == current or parent in path_ids:
            break
        path_ids.append(parent)
        current = parent

    path_ids.reverse()  # root → leaf

    # Ensure root is always the first node.
    # If root appears somewhere in the middle (e.g. walk went past root due to
    # ambiguous parent entries), truncate everything before it.
    if root_id in path_ids:
        root_idx = path_ids.index(root_id)
        if root_idx > 0:
            path_ids = path_ids[root_idx:]
    else:
        path_ids.insert(0, root_id)

    # Fetch names in one round-trip
    try:
        rows = await pool.fetch(
            "SELECT client_id, company_name FROM on24master.client WHERE client_id = ANY($1::bigint[])",
            path_ids, timeout=8,
        )
        name_map = {r["client_id"]: r["company_name"] for r in rows}
    except Exception:
        name_map = {}

    return [
        {"client_id": cid, "company_name": name_map.get(cid, f"Client {cid}")}
        for cid in path_ids
    ]


async def get_allowed_client_ids(pool: asyncpg.Pool, root_id: int) -> set[int]:
    """Return all client_ids reachable from root — used to validate user selection."""
    try:
        rows = await pool.fetch(
            """
            WITH RECURSIVE h(cid) AS (
                SELECT DISTINCT sub_client_id FROM on24master.client_hierarchy WHERE client_id = $1
                UNION
                SELECT DISTINCT ch.sub_client_id FROM on24master.client_hierarchy ch
                INNER JOIN h ON ch.client_id = h.cid
                WHERE ch.sub_client_id != ch.client_id
            )
            SELECT DISTINCT cid FROM h
            """,
            root_id, timeout=8,
        )
        return {root_id} | {r["cid"] for r in rows}
    except Exception:
        return {root_id}
