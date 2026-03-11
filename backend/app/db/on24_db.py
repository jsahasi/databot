"""Read-only async connection pool for the ON24 master database.

SECURITY: client_id is loaded from settings and injected into every query.
It is NEVER accepted as a parameter from agents or users.
"""

import ssl
import tempfile
import os

import asyncpg

from app.config import settings

_pool: asyncpg.Pool | None = None


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

    open(ca_path, "w").write(ca)
    open(cert_path, "w").write(cert)
    open(key_path, "w").write(key)

    ctx.load_verify_locations(ca_path)
    ctx.load_cert_chain(cert_path, key_path)

    return ctx


async def get_pool() -> asyncpg.Pool:
    """Return (or lazily create) the shared asyncpg connection pool."""
    global _pool
    if _pool is None:
        ssl_ctx = _build_ssl_context()

        # Parse DATABASE_URL: postgresql+asyncpg://user:pass@host:port/db
        url = settings.database_url.replace("postgresql+asyncpg://", "")
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
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_client_id() -> int:
    """Return the current tenant client_id from config.

    NEVER accept this value from agents, users, or any external input.
    """
    return int(settings.on24_client_id)
