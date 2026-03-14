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

import logging

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None
_active_env: str = ""  # "PROD" or "QA" — tracks which DB we're connected to
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


def _build_ssl_context_qa() -> ssl.SSLContext | None:
    """Build SSL context for QA DB (uses QA-specific certs if available, else shared)."""
    cert_content = settings.db_pg_ssl_cert_content_qa or settings.db_pg_ssl_cert_content
    key_content = settings.db_pg_ssl_key_content_qa or settings.db_pg_ssl_key_content
    ca_content = settings.db_pg_ssl_root_cert_content
    if not ca_content:
        return None

    def unescape(s: str) -> str:
        return s.replace("\\n", "\n").strip('"').strip("'")

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_REQUIRED

    tmp_dir = tempfile.mkdtemp()
    try:
        ca_path = os.path.join(tmp_dir, "ca.pem")
        cert_path = os.path.join(tmp_dir, "client.crt")
        key_path = os.path.join(tmp_dir, "client.key")
        with open(ca_path, "w", newline="\n") as f: f.write(unescape(ca_content))
        with open(cert_path, "w", newline="\n") as f: f.write(unescape(cert_content))
        with open(key_path, "w", newline="\n") as f: f.write(unescape(key_content))
        ctx.load_verify_locations(ca_path)
        ctx.load_cert_chain(cert_path, key_path)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return ctx


async def _create_pool(url: str, ssl_ctx: ssl.SSLContext | None) -> asyncpg.Pool:
    """Parse a DB URL and create an asyncpg pool."""
    parsed = url.replace("postgresql+asyncpg://", "")
    userpass, hostdb = parsed.split("@", 1)
    user, password = userpass.split(":", 1)
    hostport, database = hostdb.split("/", 1)
    host, port = hostport.rsplit(":", 1)

    return await asyncpg.create_pool(
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


def get_active_env() -> str:
    """Return which ON24 DB environment is active: 'PROD', 'QA', or '' if not connected."""
    return _active_env


async def get_pool() -> asyncpg.Pool:
    """Return (or lazily create) the shared asyncpg connection pool.

    Tries PROD first. If PROD fails (connection refused, timeout), falls back to QA.
    """
    global _pool, _active_env
    if _pool is not None:
        # Verify the pool is still alive with a quick check
        try:
            async with _pool.acquire(timeout=5) as conn:
                await conn.fetchval("SELECT 1")
            return _pool
        except Exception:
            logger.warning(f"ON24 {_active_env} pool health check failed — reconnecting")
            try:
                await _pool.close()
            except Exception:
                pass
            _pool = None
            _active_env = ""

    if not settings.on24_db_url:
        raise RuntimeError("ON24_DB_URL is not configured")

    # Try PROD first
    try:
        ssl_ctx = _build_ssl_context()
        _pool = await asyncio.wait_for(
            _create_pool(settings.on24_db_url, ssl_ctx),
            timeout=10,
        )
        # Quick connectivity test
        async with _pool.acquire(timeout=5) as conn:
            await conn.fetchval("SELECT 1")
        _active_env = "PROD"
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
            ssl_ctx_qa = _build_ssl_context_qa()
            _pool = await asyncio.wait_for(
                _create_pool(settings.on24_db_url_qa, ssl_ctx_qa),
                timeout=10,
            )
            async with _pool.acquire(timeout=5) as conn:
                await conn.fetchval("SELECT 1")
            _active_env = "QA"
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


async def switch_environment(target: str) -> str:
    """Force-switch to PROD or QA. Closes existing pool and connects to target.

    Returns the environment name actually connected to.
    """
    global _pool, _active_env, _tenant_ids_cache

    # Close existing pool
    if _pool:
        try:
            await _pool.close()
        except Exception:
            pass
        _pool = None
    _active_env = ""
    _tenant_ids_cache = {}

    if target == "PROD":
        url = settings.on24_db_url
        ssl_ctx = _build_ssl_context()
    elif target == "QA":
        url = settings.on24_db_url_qa
        ssl_ctx = _build_ssl_context_qa()
    else:
        raise ValueError(f"Unknown target: {target}")

    if not url:
        raise RuntimeError(f"ON24_DB_URL{'_QA' if target == 'QA' else ''} is not configured")

    _pool = await asyncio.wait_for(_create_pool(url, ssl_ctx), timeout=10)
    async with _pool.acquire(timeout=5) as conn:
        await conn.fetchval("SELECT 1")
    _active_env = target
    logger.info(f"Switched to ON24 {target} database")
    return _active_env


async def close_pool() -> None:
    """Close and discard the shared connection pool (called on app shutdown)."""
    global _pool, _active_env, _tenant_ids_cache
    if _pool:
        await _pool.close()
        _pool = None
    _active_env = ""
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
