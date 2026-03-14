import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import websocket_chat
from app.api.router import api_router
from app.config import settings
from app.db.on24_db import close_pool
from app.services.response_cache import close_redis

logger = logging.getLogger(__name__)


_background_tasks: set = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ingest knowledge base in background (non-blocking)
    task = asyncio.create_task(_ingest_knowledge_base())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    # Startup: refresh brand voice if stale (non-blocking)
    bv_task = asyncio.create_task(_refresh_brand_voice())
    _background_tasks.add(bv_task)
    bv_task.add_done_callback(_background_tasks.discard)
    # Startup: clean up expired uploads (>24h)
    from app.api.upload import cleanup_old_uploads
    cleanup_old_uploads()
    yield
    # Shutdown
    await close_pool()
    await close_redis()


async def _refresh_brand_voice():
    """Refresh brand voice document if stale (runs as background task)."""
    try:
        from app.services.brand_voice import refresh_if_stale
        await refresh_if_stale()
    except Exception as e:
        logger.warning(f"Brand voice refresh failed (non-fatal): {e}")


async def _ingest_knowledge_base():
    """Ingest Zendesk articles and API reference into Postgres (runs as background task)."""
    try:
        from app.db.knowledge_base import ingest_zendesk_articles, ingest_api_reference
        count = await ingest_zendesk_articles()
        logger.info(f"Knowledge base: {count} Zendesk articles ingested")
        api_count = await ingest_api_reference()
        logger.info(f"Knowledge base: {api_count} API endpoints ingested")
    except Exception as e:
        logger.warning(f"Knowledge base ingestion failed (non-fatal): {e}")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next) -> Response:
    """Add OWASP-recommended security headers to every HTTP response (A05)."""
    response = await call_next(request)
    # Prevent MIME-type sniffing (A05)
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Deny framing (clickjacking protection, A05)
    response.headers["X-Frame-Options"] = "DENY"
    # Restrict referrer info on cross-origin requests
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Permissions policy — disable unused browser features
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # Content-Security-Policy — defence-in-depth against XSS even with DOMPurify
    # 'unsafe-inline' is required for inline Recharts SVG styles; tighten if deps allow
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self' wss: ws:; "
        "frame-ancestors 'none';"
    )
    return response


app.include_router(api_router, prefix="/api")
app.add_api_websocket_route("/ws/chat", websocket_chat)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/status")
async def app_status():
    """Return app status including which ON24 DB environment is active."""
    from app.db.on24_db import get_active_env, get_pool
    env = get_active_env()
    # If no pool exists yet, try to create one so we can report the actual state
    if not env:
        try:
            await get_pool()
            env = get_active_env()
        except Exception:
            env = "disconnected"
    return {
        "on24_db": env or "disconnected",
        "qa_available": bool(settings.on24_db_url_qa),
    }


@app.post("/api/status/switch-db")
async def switch_db(target: str = "PROD"):
    """Switch the ON24 DB connection to PROD or QA."""
    from app.db.on24_db import switch_environment
    target = target.upper()
    if target not in ("PROD", "QA"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="target must be PROD or QA")
    env = await switch_environment(target)
    return {"on24_db": env}
