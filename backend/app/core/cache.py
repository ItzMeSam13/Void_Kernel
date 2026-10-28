"""
Redis helpers: ARQ job-queue connection factory + SHA-256 7-day result cache.

ARQ uses redis-py under the hood; the same connection pool can service both the
queue and the hand-rolled result cache.
"""
from __future__ import annotations

import json
import hashlib
from typing import Any, Optional

import redis.asyncio as aioredis
from app.core.config import settings


# ── Pool (lazily created once per process) ────────────────────────────────────
_redis_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Return the shared async Redis connection (creates it on first call)."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


# ── ARQ settings dict (pass to arq.create_pool / Worker) ─────────────────────
def arq_redis_settings() -> dict:
    """Return a dict ARQ expects for its RedisSettings."""
    from arq.connections import RedisSettings  # local import — only when ARQ is used
    return RedisSettings.from_dsn(settings.REDIS_URL)


# ── SHA-256 helpers ────────────────────────────────────────────────────────────
def compute_sha256(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


_CACHE_PREFIX = "result:"


async def cache_get(sha256: str) -> Optional[dict]:
    """
    Look up a previously computed result by its media SHA-256.
    Returns the deserialized dict on hit, ``None`` on miss.
    """
    r = await get_redis()
    raw = await r.get(f"{_CACHE_PREFIX}{sha256}")
    if raw is None:
        return None
    return json.loads(raw)


async def cache_set(sha256: str, result: dict) -> None:
    """
    Persist *result* under *sha256* with the configured TTL (default 7 days).
    """
    r = await get_redis()
    await r.set(
        f"{_CACHE_PREFIX}{sha256}",
        json.dumps(result),
        ex=settings.RESULT_CACHE_TTL_SECONDS,
    )


async def cache_delete(sha256: str) -> None:
    """Evict a cached result (useful if a result is reprocessed with updated models)."""
    r = await get_redis()
    await r.delete(f"{_CACHE_PREFIX}{sha256}")
