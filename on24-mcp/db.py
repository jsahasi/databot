"""Read-only asyncpg connection pool for the ON24 master database.

Self-contained — no dependency on the backend package.
Mirrors the logic in backend/app/db/on24_db.py.

SECURITY:
- client_id is sourced from config (ON24_CLIENT_ID env var) only — never from callers.
- All queries must use WHERE client_id = ANY($N::bigint[]).

TENANT HIERARCHY:
- get_client_id()         → root client_id from config
- get_tenant_client_ids() → root + all sub-clients via recursive CTE (cached)
"""

import asyncio
import os
import shutil
import ssl
import tempfile
from typing import Optional

import asyncpg

from config import settings

import logging

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None
_tenant_ids_cache: dict[int, list[int]] = {}
_tenant_ids_lock = asyncio.Lock()


def _unescape(s: str) -> str:
    return s.replace("\\n", "\n").strip('"').strip("'")


def _build_ssl_context() -> Optional[ssl.SSLContext]:
    """Build SSL context from cert content env vars."""
    ca = settings.db_pg_ssl_root_cert_content
    cert = settings.db_pg_ssl_cert_content
    key = settings.db_pg_ssl_key_content

    if not ca:
        return None

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_REQUIRED

    tmp_dir = tempfile.mkdtemp()
    try:
        ca_path = os.path.join(tmp_dir, "ca.pem")
        cert_path = os.path.join(tmp_dir, "client.crt")
        key_path = os.path.join(tmp_dir, "client.key")

        with open(ca_path, "w", newline="\n") as f:
            f.write(_unescape(ca))
        with open(cert_path, "w", newline="\n") as f:
            f.write(_unescape(cert))
        with open(key_path, "w", newline="\n") as f:
            f.write(_unescape(key))

        ctx.load_verify_locations(ca_path)
        ctx.load_cert_chain(cert_path, key_path)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return ctx


def _parse_db_url(url: str) -> dict:
    """Parse postgresql+asyncpg:// URL into connection kwargs."""
    url = url.replace("postgresql+asyncpg://", "").replace("postgresql://", "")
    userpass, hostdb = url.split("@", 1)
    user, password = userpass.split(":", 1)
    hostport, database = hostdb.split("/", 1)
    host, port = hostport.rsplit(":", 1)
    return {"host": host, "port": int(port), "database": database, "user": user, "password": password}


async def _create_pool(url: str, ssl_ctx: Optional[ssl.SSLContext]) -> asyncpg.Pool:
    params = _parse_db_url(url)
    return await asyncpg.create_pool(
        **params,
        ssl=ssl_ctx,
        min_size=1,
        max_size=3,
        command_timeout=60,
    )


async def get_pool() -> asyncpg.Pool:
    """Return (or lazily create) the shared asyncpg pool. Tries PROD, falls back to QA."""
    global _pool

    if _pool is not None:
        try:
            async with _pool.acquire(timeout=5) as conn:
                await conn.fetchval("SELECT 1")
            return _pool
        except Exception:
            logger.warning("ON24 pool health check failed — reconnecting")
            try:
                await _pool.close()
            except Exception:
                pass
            _pool = None

    if not settings.on24_db_url:
        raise RuntimeError("ON24_DB_URL is not configured")

    # Try PROD first
    try:
        ssl_ctx = _build_ssl_context()
        _pool = await asyncio.wait_for(_create_pool(settings.on24_db_url, ssl_ctx), timeout=10)
        async with _pool.acquire(timeout=5) as conn:
            await conn.fetchval("SELECT 1")
        logger.info("Connected to ON24 PROD database")
        return _pool
    except Exception as exc:
        logger.warning(f"ON24 PROD connection failed: {exc}")
        if _pool:
            try:
                await _pool.close()
            except Exception:
                pass
            _pool = None

    # Fallback to QA
    if settings.on24_db_url_qa:
        try:
            ssl_ctx = _build_ssl_context()
            _pool = await asyncio.wait_for(_create_pool(settings.on24_db_url_qa, ssl_ctx), timeout=10)
            async with _pool.acquire(timeout=5) as conn:
                await conn.fetchval("SELECT 1")
            logger.info("Connected to ON24 QA database (PROD unavailable)")
            return _pool
        except Exception as exc:
            logger.warning(f"ON24 QA connection also failed: {exc}")
            if _pool:
                try:
                    await _pool.close()
                except Exception:
                    pass
                _pool = None

    raise RuntimeError("Both ON24 PROD and QA databases are unreachable")


async def close_pool() -> None:
    global _pool, _tenant_ids_cache
    if _pool:
        await _pool.close()
        _pool = None
    _tenant_ids_cache = {}


def get_client_id() -> int:
    """Return root client_id from config — never from callers."""
    return int(settings.on24_client_id)


async def get_tenant_client_ids() -> list[int]:
    """Return root + all sub-clients in the hierarchy (cached)."""
    root = get_client_id()

    if root in _tenant_ids_cache:
        return _tenant_ids_cache[root]

    async with _tenant_ids_lock:
        if root in _tenant_ids_cache:
            return _tenant_ids_cache[root]

        pool = await get_pool()
        rows = await pool.fetch(
            """
            WITH RECURSIVE hierarchy(cid) AS (
                SELECT DISTINCT sub_client_id
                FROM on24master.client_hierarchy
                WHERE client_id = $1

                UNION

                SELECT DISTINCT ch.sub_client_id
                FROM on24master.client_hierarchy ch
                INNER JOIN hierarchy h ON ch.client_id = h.cid
                WHERE ch.sub_client_id != ch.client_id
            )
            SELECT DISTINCT cid FROM hierarchy
            WHERE cid != $1
            """,
            root,
        )
        sub_ids = [r["cid"] for r in rows]
        result = [root] + sorted(sub_ids)
        _tenant_ids_cache[root] = result
        return result
