"""Read-only async connection pool for the ON24 master database.

SECURITY: client_id is loaded from settings and injected into every query.
It is NEVER accepted as a parameter from agents or users.

MULTI-TENANT DESIGN (current: single root client hardcoded in config):
- get_client_id()        → returns the root client_id from config
- get_tenant_client_ids() → returns root + all sub-clients in the hierarchy
- All queries use get_tenant_client_ids() so sub-client data is included

FUTURE multi-client support (when needed):
1. Add a `tenants` table in our own DB mapping session/user → root_client_id
2. Replace get_client_id() with a context-var based lookup (per-request)
3. get_tenant_client_ids() already accepts an optional root override for this
4. No query-level changes needed — just swap the root resolution
"""

import asyncio
import ssl
import tempfile
import os
from functools import lru_cache

import asyncpg

from app.config import settings

_pool: asyncpg.Pool | None = None
_tenant_ids_cache: list[int] | None = None
_tenant_ids_lock = asyncio.Lock()


def _build_ssl_context() -> ssl.SSLContext | None:
    """Build SSL context from cert content env vars, if provided."""
    if not settings.db_pg_ssl_root_cert_content:
        return None

    def unescape(s: str) -> str:
        return s.replace("\\n", "\n").strip('"').strip("'")

    ca = unescape(settings.db_pg_ssl_root_cert_content)
    cert = unescape(settings.db_pg_ssl_cert_content)
    key = unescape(settings.db_pg_ssl_key_content)

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_REQUIRED

    tmp_dir = tempfile.mkdtemp()
    ca_path = os.path.join(tmp_dir, "ca.pem")
    cert_path = os.path.join(tmp_dir, "client.crt")
    key_path = os.path.join(tmp_dir, "client.key")

    with open(ca_path, "w", newline="\n") as f: f.write(ca)
    with open(cert_path, "w", newline="\n") as f: f.write(cert)
    with open(key_path, "w", newline="\n") as f: f.write(key)

    ctx.load_verify_locations(ca_path)
    ctx.load_cert_chain(cert_path, key_path)

    return ctx


async def get_pool() -> asyncpg.Pool:
    """Return (or lazily create) the shared asyncpg connection pool."""
    global _pool
    if _pool is None:
        if not settings.on24_db_url:
            raise RuntimeError("ON24_DB_URL is not configured")

        ssl_ctx = _build_ssl_context()

        # Parse ON24_DB_URL: postgresql+asyncpg://user:pass@host:port/db
        url = settings.on24_db_url.replace("postgresql+asyncpg://", "")
        userpass, hostdb = url.split("@", 1)
        user, password = userpass.split(":", 1)
        hostport, database = hostdb.split("/", 1)
        host, port = hostport.rsplit(":", 1)

        _pool = await asyncpg.create_pool(
            host=host,
            port=int(port),
            database=database,
            user=user,
            password=password,
            ssl=ssl_ctx,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
    return _pool


async def close_pool() -> None:
    """Close and discard the shared connection pool (called on app shutdown)."""
    global _pool, _tenant_ids_cache
    if _pool:
        await _pool.close()
        _pool = None
    _tenant_ids_cache = None


def get_client_id() -> int:
    """Return the root tenant client_id from config.

    NEVER accept this value from agents, users, or any external input.

    FUTURE: replace with a per-request context var lookup when supporting
    multiple root clients.
    """
    return int(settings.on24_client_id)


async def get_tenant_client_ids() -> list[int]:
    """Return the root client_id plus all sub-clients in the hierarchy.

    Result is cached for the lifetime of the process (hierarchy rarely changes).
    Uses a cycle-safe query to handle self-referential rows in client_hierarchy.

    Example for root=10710:
        [10710, 22355, 28516, 42835, 44220, 45077, 46851, 48673, 51429, 52909]

    SECURITY: The root is always sourced from get_client_id() — never from
    external input.

    FUTURE multi-client: accept an optional root_client_id parameter (sourced
    from the per-request tenant context, not from agents/users).
    """
    global _tenant_ids_cache
    if _tenant_ids_cache is not None:
        return _tenant_ids_cache

    async with _tenant_ids_lock:
        # Double-checked locking
        if _tenant_ids_cache is not None:
            return _tenant_ids_cache

        root = get_client_id()
        pool = await get_pool()

        # Cycle-safe recursive CTE: DISTINCT prevents re-visiting nodes
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
                WHERE ch.sub_client_id != ch.client_id  -- skip self-refs in recursion
            )
            SELECT DISTINCT cid FROM hierarchy
            WHERE cid != $1   -- sub-clients only; we add root separately below
            """,
            root,
        )

        sub_ids = [r["cid"] for r in rows]
        # Root always included, sub-clients appended
        _tenant_ids_cache = [root] + sorted(sub_ids)
        return _tenant_ids_cache
