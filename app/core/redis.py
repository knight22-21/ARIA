"""Shared async Redis client accessor.

Used for: idempotency keys, bank-failure-rate time series, distributed locks,
and (later) agent message streams.
"""

from __future__ import annotations

import redis.asyncio as aioredis

from app.core.config import settings

_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return a lazily-created, process-wide async Redis client."""
    global _client
    if _client is None:
        _client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _client
