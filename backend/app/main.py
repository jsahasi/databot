import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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
    # Startup: prefetch common data into Redis cache (non-blocking)
    prefetch_task = asyncio.create_task(_prefetch_data())
    _background_tasks.add(prefetch_task)
    prefetch_task.add_done_callback(_background_tasks.discard)
    # Startup: schedule daily improvement email if configured
    if settings.send_improvement_email_to:
        email_task = asyncio.create_task(_daily_improvement_email_loop())
        _background_tasks.add(email_task)
        email_task.add_done_callback(_background_tasks.discard)
    yield
    # Shutdown
    await close_pool()
    await close_redis()


async def _prefetch_data():
    """Warm Redis cache with commonly requested data (runs as background task)."""
    try:
        # Wait a few seconds for DB pool to initialize
        await asyncio.sleep(3)
        from app.services.data_prefetch import prefetch_common_data
        await prefetch_common_data()
    except Exception:
        logger.exception("Data prefetch failed")


async def _daily_improvement_email_loop():
    """Send daily improvement-inbox email at 11:59 PM server time."""
    from datetime import datetime, time, timedelta
    from pathlib import Path
    from app.services.email_service import send_email

    logger.info(f"Daily improvement email scheduled → {settings.send_improvement_email_to}")
    data_dir = Path("/app/data")

    while True:
        try:
            now = datetime.now()
            # Calculate seconds until next 11:59 PM
            target = datetime.combine(now.date(), time(23, 59))
            if now >= target:
                target += timedelta(days=1)
            wait_seconds = (target - now).total_seconds()
            logger.info(f"Improvement email: next send in {wait_seconds:.0f}s at {target}")
            await asyncio.sleep(wait_seconds)

            # Find today's improvement file(s)
            today_str = datetime.now().strftime("%m-%d-%Y")
            files = sorted(data_dir.glob("improvement-inbox-*.txt"))
            if not files:
                logger.info("No improvement files to send")
                continue

            # Send the most recent file (today's or latest available)
            today_file = data_dir / f"improvement-inbox-{today_str}.txt"
            files_to_send = [today_file] if today_file.exists() else [files[-1]]

            file_names = ", ".join(f.name for f in files_to_send)
            html_body = f"""
            <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:600px;margin:0 auto;padding:2rem;">
                <h2 style="color:#4f46e5;">Daily Improvement Digest</h2>
                <p>Attached: <strong>{file_names}</strong></p>
                <p>These are user-flagged bot responses that need review.
                Each entry contains the user's question, the bot's response,
                the user's complaint, and a structured investigation prompt.</p>
                <p style="color:#6b7280;font-size:0.85rem;">
                    Sent automatically by ON24 Nexus at {datetime.now().strftime('%Y-%m-%d %I:%M %p')}
                </p>
            </div>
            """

            success = await send_email(
                to=settings.send_improvement_email_to,
                subject=f"ON24 Nexus — Improvement Digest ({today_str})",
                html_body=html_body,
                attachments=files_to_send,
            )
            if success:
                logger.info(f"Improvement email sent to {settings.send_improvement_email_to}")
            else:
                logger.warning("Improvement email send failed (no email service configured?)")
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Error in daily improvement email loop")
            await asyncio.sleep(3600)  # retry in 1 hour on error


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

# --- SEC-02: Rate limiting (per IP) ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please slow down."},
    )


# --- SEC-01: API Key authentication middleware ---
@app.middleware("http")
async def api_key_auth(request: Request, call_next):
    """Validate API key on all routes except /health.
    Auth is disabled when API_KEY is not set (dev mode).
    """
    if settings.api_key:
        # Skip auth for health check and static docs
        path = request.url.path
        if path not in ("/health",) and not path.startswith("/docs/"):
            auth_header = request.headers.get("Authorization", "")
            api_key_param = request.query_params.get("api_key", "")
            if auth_header == f"Bearer {settings.api_key}" or api_key_param == settings.api_key:
                pass  # Authenticated
            else:
                return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
    return await call_next(request)


# --- SEC-03: CORS — restricted to configured origins only ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
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


# SEC-02: Apply rate limiting to all /api/* routes
from slowapi.middleware import SlowAPIMiddleware
app.add_middleware(SlowAPIMiddleware)

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
