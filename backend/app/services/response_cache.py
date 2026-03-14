"""Redis-backed response cache for chat queries.

Caches identical chat prompts (by SHA256 hash) for a configurable TTL.
Eliminates redundant Anthropic API calls when multiple users ask the
same question within the cache window.

Cache keys include the client_id to prevent cross-tenant cache hits.
"""

import hashlib
import json
import logging
from typing import Any

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

_redis: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    """Return (or lazily create) the shared async Redis client."""
    global _redis
    if _redis is not None:
        try:
            await _redis.ping()
            return _redis
        except Exception:
            _redis = None

    if not settings.redis_url:
        return None

    try:
        _redis = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        await _redis.ping()
        logger.info("Redis response cache connected")
        return _redis
    except Exception as exc:
        logger.warning(f"Redis unavailable — response cache disabled: {exc}")
        _redis = None
        return None


async def close_redis() -> None:
    """Close the Redis connection (called on app shutdown)."""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


def _cache_key(prompt: str, client_id: int) -> str:
    """Generate a cache key from the prompt hash + client_id."""
    h = hashlib.sha256(prompt.strip().lower().encode()).hexdigest()[:16]
    return f"chat:resp:{client_id}:{h}"


async def get_cached_response(prompt: str, client_id: int) -> dict[str, Any] | None:
    """Look up a cached response for this prompt + client."""
    r = await get_redis()
    if r is None:
        return None

    try:
        cached = await r.get(_cache_key(prompt, client_id))
        if cached:
            logger.debug(f"Cache HIT for prompt hash")
            return json.loads(cached)
    except Exception as exc:
        logger.warning(f"Redis get failed: {exc}")
    return None


async def cache_response(
    prompt: str,
    client_id: int,
    response: dict[str, Any],
) -> None:
    """Store a response in cache with TTL."""
    r = await get_redis()
    if r is None:
        return

    try:
        key = _cache_key(prompt, client_id)
        await r.setex(key, settings.response_cache_ttl, json.dumps(response, default=str))
        logger.debug(f"Cache SET for prompt hash (TTL={settings.response_cache_ttl}s)")
    except Exception as exc:
        logger.warning(f"Redis set failed: {exc}")
