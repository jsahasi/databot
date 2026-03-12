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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ingest knowledge base in background (non-blocking)
    asyncio.get_event_loop().run_in_executor(None, _ingest_knowledge_base)
    yield
    # Shutdown
    await close_pool()


def _ingest_knowledge_base():
    """Ingest Zendesk articles into ChromaDB (runs in thread pool)."""
    try:
        from app.db.knowledge_base import ingest_zendesk_articles
        count = ingest_zendesk_articles()
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
