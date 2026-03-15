"""Tests for response_cache.py — Redis response caching with mocked Redis client."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

MODULE = "app.services.response_cache"


@pytest.fixture
def mock_redis():
    """Create a mock async Redis client."""
    r = AsyncMock()
    r.ping = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.setex = AsyncMock()
    r.aclose = AsyncMock()
    return r


class TestCacheKey:
    def test_same_prompt_same_client_same_key(self):
        from app.services.response_cache import _cache_key
        k1 = _cache_key("show attendance trends", 10710)
        k2 = _cache_key("show attendance trends", 10710)
        assert k1 == k2

    def test_different_prompt_different_key(self):
        from app.services.response_cache import _cache_key
        k1 = _cache_key("show attendance trends", 10710)
        k2 = _cache_key("show top events", 10710)
        assert k1 != k2

    def test_different_client_different_key(self):
        from app.services.response_cache import _cache_key
        k1 = _cache_key("show attendance trends", 10710)
        k2 = _cache_key("show attendance trends", 22355)
        assert k1 != k2

    def test_case_insensitive(self):
        from app.services.response_cache import _cache_key
        k1 = _cache_key("Show Attendance Trends", 10710)
        k2 = _cache_key("show attendance trends", 10710)
        assert k1 == k2

    def test_strips_whitespace(self):
        from app.services.response_cache import _cache_key
        k1 = _cache_key("  show trends  ", 10710)
        k2 = _cache_key("show trends", 10710)
        assert k1 == k2

    def test_key_format(self):
        from app.services.response_cache import _cache_key
        key = _cache_key("test", 10710)
        assert key.startswith("chat:resp:10710:")
        assert len(key) > 20


class TestGetCachedResponse:
    @pytest.mark.asyncio
    async def test_returns_none_when_redis_unavailable(self):
        from app.services.response_cache import get_cached_response
        import app.services.response_cache as mod
        mod._redis = None
        with patch(f"{MODULE}.get_redis", AsyncMock(return_value=None)):
            result = await get_cached_response("test", 10710)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_cached_data(self, mock_redis):
        from app.services.response_cache import get_cached_response
        cached = {"text": "5 events", "agent_used": "data_agent"}
        mock_redis.get.return_value = json.dumps(cached)
        with patch(f"{MODULE}.get_redis", AsyncMock(return_value=mock_redis)):
            result = await get_cached_response("test prompt", 10710)
        assert result == cached
        assert result["text"] == "5 events"

    @pytest.mark.asyncio
    async def test_returns_none_on_cache_miss(self, mock_redis):
        from app.services.response_cache import get_cached_response
        mock_redis.get.return_value = None
        with patch(f"{MODULE}.get_redis", AsyncMock(return_value=mock_redis)):
            result = await get_cached_response("uncached prompt", 10710)
        assert result is None


class TestCacheResponse:
    @pytest.mark.asyncio
    async def test_stores_with_ttl(self, mock_redis):
        from app.services.response_cache import cache_response
        response = {"text": "hello", "agent_used": "data_agent"}
        with patch(f"{MODULE}.get_redis", AsyncMock(return_value=mock_redis)):
            await cache_response("test prompt", 10710, response)
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        assert args[0].startswith("chat:resp:10710:")
        assert args[1] == 300  # TTL from config default (5 min)
        stored = json.loads(args[2])
        assert stored["text"] == "hello"

    @pytest.mark.asyncio
    async def test_no_op_when_redis_unavailable(self):
        from app.services.response_cache import cache_response
        with patch(f"{MODULE}.get_redis", AsyncMock(return_value=None)):
            await cache_response("test", 10710, {"text": "x"})
        # Should not raise


class TestCloseRedis:
    @pytest.mark.asyncio
    async def test_close_sets_none(self, mock_redis):
        import app.services.response_cache as mod
        mod._redis = mock_redis
        await mod.close_redis()
        assert mod._redis is None
        mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_noop_when_none(self):
        import app.services.response_cache as mod
        mod._redis = None
        await mod.close_redis()  # Should not raise
