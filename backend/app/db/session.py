import ssl
import tempfile
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


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

    # Write certs to temp files (asyncpg requires file paths)
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


def _make_engine():
    ssl_ctx = _build_ssl_context()
    connect_args = {"ssl": ssl_ctx} if ssl_ctx else {}
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        connect_args=connect_args,
    )


engine = _make_engine()
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
