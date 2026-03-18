import asyncio
import time

# ON24 rate limits per endpoint category (requests per minute)
RATE_LIMITS = {
    "event_detail": 1000,  # GET /event/{eventId}
    "registrant_write": 1000,  # POST registrant
    "analytics_high": 100,  # attendee/registrant queries
    "analytics_medium": 60,  # polls, surveys, resources, group chat
    "analytics_low": 30,  # events list, presenters, survey library
    "management": 10,  # event creation/modification
    "default": 30,  # fallback
}


class RateLimiter:
    """Async token bucket rate limiter for ON24 API."""

    def __init__(self):
        self._buckets: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    def _get_bucket(self, category: str) -> dict:
        if category not in self._buckets:
            max_tokens = RATE_LIMITS.get(category, RATE_LIMITS["default"])
            self._buckets[category] = {
                "tokens": max_tokens,
                "max_tokens": max_tokens,
                "last_refill": time.monotonic(),
            }
        return self._buckets[category]

    async def acquire(self, category: str = "default") -> None:
        """Wait until a token is available for the given category."""
        while True:
            async with self._lock:
                bucket = self._get_bucket(category)
                now = time.monotonic()
                elapsed = now - bucket["last_refill"]
                # Refill tokens based on elapsed time (tokens per second = max/60)
                refill = elapsed * (bucket["max_tokens"] / 60.0)
                bucket["tokens"] = min(bucket["max_tokens"], bucket["tokens"] + refill)
                bucket["last_refill"] = now

                if bucket["tokens"] >= 1.0:
                    bucket["tokens"] -= 1.0
                    return

            # No tokens available, wait briefly
            await asyncio.sleep(0.1)

    def get_category_for_endpoint(self, path: str) -> str:
        """Determine rate limit category from URL path."""
        # Event detail by ID (highest limit)
        if "/event/" in path and path.rstrip("/").split("/")[-1].isdigit():
            segments_after_event = path.split("/event/")[1].split("/")
            if len(segments_after_event) == 1:
                return "event_detail"

        # Registration writes
        if "registrant" in path and path.endswith("registrant"):
            return "registrant_write"

        # High-rate analytics (attendee/registrant reads)
        if any(kw in path for kw in ["attendee", "registrant"]):
            return "analytics_high"

        # Medium-rate analytics
        if any(kw in path for kw in ["poll", "survey", "resource", "groupchat", "cta", "contentactivity"]):
            return "analytics_medium"

        # Low-rate analytics
        if any(kw in path for kw in ["event", "presenter", "surveylibrary", "lead", "engagedaccount"]):
            return "analytics_low"

        # Management operations
        if any(kw in path for kw in ["forget", "speakerbio", "slide", "email"]):
            return "management"

        return "default"
