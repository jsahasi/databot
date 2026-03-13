import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import websocket_chat
from app.api.router import api_router
from app.config import settings
from app.db.on24_db import close_pool

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
    yield
    # Shutdown
    await close_pool()


async def _refresh_brand_voice():
    """Refresh brand voice document if stale (runs as background task)."""
    try:
        from app.services.brand_voice import refresh_if_stale
        await refresh_if_stale()
    except Exception as e:
        logger.warning(f"Brand voice refresh failed (non-fatal): {e}")


async def _ingest_knowledge_base():
    """Ingest Zendesk articles into Postgres (runs as background task)."""
    try:
        from app.db.knowledge_base import ingest_zendesk_articles
        count = await ingest_zendesk_articles()
        logger.info(f"Knowledge base: {count} articles ingested")
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

app.include_router(api_router, prefix="/api")
app.add_api_websocket_route("/ws/chat", websocket_chat)


@app.get("/health")
async def health():
    return {"status": "ok"}
