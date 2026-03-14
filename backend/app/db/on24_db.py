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
import contextvars
import shutil
import ssl
import tempfile
import os

import asyncpg

from app.config import settings

_pool: asyncpg.Pool | None = None
_tenant_ids_cache: dict[int, list[int]] = {}
_tenant_ids_lock = asyncio.Lock()

# Per-request client override (set in WebSocket handler, never from agents/tools)
_request_client_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "_request_client_id", default=None
)


def set_request_client_id(client_id: int | None) -> None:
    """Set the root client_id for the current request context."""
    _request_client_id.set(client_id)


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
    try:
        ca_path = os.path.join(tmp_dir, "ca.pem")
        cert_path = os.path.join(tmp_dir, "client.crt")
        key_path = os.path.join(tmp_dir, "client.key")

        with open(ca_path, "w", newline="\n") as f: f.write(ca)
        with open(cert_path, "w", newline="\n") as f: f.write(cert)
        with open(key_path, "w", newline="\n") as f: f.write(key)

        ctx.load_verify_locations(ca_path)
        ctx.load_cert_chain(cert_path, key_path)
    finally:
        # Certs are loaded into the SSLContext in memory; remove temp files immediately
        shutil.rmtree(tmp_dir, ignore_errors=True)

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
            command_timeout=60,
        )
    return _pool


async def close_pool() -> None:
    """Close and discard the shared connection pool (called on app shutdown)."""
    global _pool, _tenant_ids_cache
    if _pool:
        await _pool.close()
        _pool = None
    _tenant_ids_cache = {}


def get_client_id() -> int:
    """Return the root tenant client_id for this request.

    Checks the per-request contextvar first (set by WebSocket handler when the
    user selects a different account in the breadcrumb).  Falls back to the
    global config value.  The contextvar is NEVER set from agent/tool code.
    """
    override = _request_client_id.get()
    if override is not None:
        return override
    return int(settings.on24_client_id)


async def get_tenant_client_ids() -> list[int]:
    """Return the root client_id plus all sub-clients in the hierarchy.

    Result is cached per root (hierarchy rarely changes).
    The root is sourced from get_client_id(), which reads the per-request
    contextvar (set by WebSocket handler) or falls back to config.
    """
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
