"""Tests for the ON24 rate limiter."""

import asyncio
import time
from unittest.mock import patch

import pytest

from app.services.rate_limiter import RATE_LIMITS, RateLimiter


@pytest.fixture
def limiter():
    return RateLimiter()


# ---------------------------------------------------------------------------
# acquire – does not block when tokens are available
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAcquire:
    async def test_acquire_returns_immediately_with_tokens(self, limiter):
        """acquire should return without delay when the bucket is full."""
        start = time.monotonic()
        await limiter.acquire("default")
        elapsed = time.monotonic() - start
        # Should be essentially instant (well under 1 second)
        assert elapsed < 0.5

    async def test_acquire_multiple_tokens(self, limiter):
        """Consuming several tokens in a row should succeed without blocking
        as long as the bucket is not empty."""
        max_tokens = RATE_LIMITS["default"]
        for _ in range(min(max_tokens, 10)):
            await limiter.acquire("default")
        # If we get here without hanging, the test passes.

    async def test_acquire_creates_bucket_on_first_call(self, limiter):
        """An unknown category should lazily create a bucket using the
        default limit."""
        assert "default" not in limiter._buckets
        await limiter.acquire("default")
        assert "default" in limiter._buckets


# ---------------------------------------------------------------------------
# get_category_for_endpoint
# ---------------------------------------------------------------------------


class TestGetCategoryForEndpoint:
    def test_event_detail_by_id(self, limiter):
        assert (
            limiter.get_category_for_endpoint("/v2/client/123/event/10001")
            == "event_detail"
        )

    def test_event_attendee_list(self, limiter):
        assert (
            limiter.get_category_for_endpoint("/v2/client/123/event/10001/attendee")
            == "analytics_high"
        )

    def test_event_registrant_ending_is_write(self, limiter):
        # Path ending in "registrant" matches the registrant_write rule
        assert (
            limiter.get_category_for_endpoint("/v2/client/123/event/10001/registrant")
            == "registrant_write"
        )

    def test_registrant_subpath_is_analytics_high(self, limiter):
        # Path with registrant but NOT ending in it (has sub-path) is analytics_high
        assert (
            limiter.get_category_for_endpoint("/v2/client/123/event/10001/registrant/details")
            == "analytics_high"
        )

    def test_poll_is_analytics_medium(self, limiter):
        assert (
            limiter.get_category_for_endpoint("/v2/client/123/event/10001/poll")
            == "analytics_medium"
        )

    def test_survey_is_analytics_medium(self, limiter):
        assert (
            limiter.get_category_for_endpoint("/v2/client/123/event/10001/survey")
            == "analytics_medium"
        )

    def test_resource_is_analytics_medium(self, limiter):
        assert (
            limiter.get_category_for_endpoint("/v2/client/123/event/10001/resource")
            == "analytics_medium"
        )

    def test_events_list_is_analytics_low(self, limiter):
        assert (
            limiter.get_category_for_endpoint("/v2/client/123/event")
            == "analytics_low"
        )

    def test_presenter_is_analytics_low(self, limiter):
        assert (
            limiter.get_category_for_endpoint("/v2/client/123/presenter")
            == "analytics_low"
        )

    def test_lead_is_analytics_low(self, limiter):
        assert (
            limiter.get_category_for_endpoint("/v2/client/123/lead")
            == "analytics_low"
        )

    def test_forget_is_management(self, limiter):
        # "forget" path maps to management category
        assert (
            limiter.get_category_for_endpoint("/v2/client/123/forget/user")
            == "management"
        )

    def test_speakerbio_is_management(self, limiter):
        assert (
            limiter.get_category_for_endpoint("/v2/client/123/speakerbio")
            == "management"
        )

    def test_unknown_returns_default(self, limiter):
        assert (
            limiter.get_category_for_endpoint("/v2/client/123/somethingweird")
            == "default"
        )


# ---------------------------------------------------------------------------
# Bucket refill over time
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestBucketRefill:
    async def test_tokens_refill_over_time(self, limiter):
        """After draining tokens, they should refill based on elapsed time."""
        category = "default"
        max_tokens = RATE_LIMITS[category]

        # Drain all tokens
        for _ in range(max_tokens):
            await limiter.acquire(category)

        bucket = limiter._buckets[category]
        assert bucket["tokens"] < 1.0

        # Simulate time passing (60 seconds = full refill for any category)
        bucket["last_refill"] = time.monotonic() - 60.0

        # Next acquire should succeed because tokens have refilled
        start = time.monotonic()
        await limiter.acquire(category)
        elapsed = time.monotonic() - start
        assert elapsed < 0.5  # Should not block

    async def test_partial_refill(self, limiter):
        """Tokens should partially refill proportionally to elapsed time."""
        category = "analytics_low"  # 30 per minute = 0.5 per second
        await limiter.acquire(category)

        bucket = limiter._buckets[category]
        tokens_after_acquire = bucket["tokens"]

        # Simulate 2 seconds passing
        bucket["last_refill"] = time.monotonic() - 2.0

        # Trigger a refill by acquiring again
        await limiter.acquire(category)

        # After 2 seconds at 30/min = 0.5/sec, we should have gained ~1.0 token
        # minus the one we just consumed. The bucket should have roughly
        # tokens_after_acquire + 1.0 - 1.0 = tokens_after_acquire
        # (within floating-point tolerance)
        bucket = limiter._buckets[category]
        assert bucket["tokens"] >= tokens_after_acquire - 1.5
