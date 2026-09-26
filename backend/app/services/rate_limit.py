"""Fixed-window rate limiting in Redis.

Rate limiting is a best-effort *availability* control: if Redis is unreachable
(down, mis-configured, a transient blip) it must never take down sign-in. So the
Redis-touching helpers **fail open** — on a backend error they log and allow the
request rather than raising a 500. The `RateLimited` signal itself is always
honored when Redis is working.
"""
import logging
from typing import Optional

from app import cache
from app.config import get_settings

log = logging.getLogger(__name__)


class RateLimited(Exception):
    def __init__(self, retry_after: int):
        super().__init__("rate limited")
        self.retry_after = max(1, retry_after)


def _key(bucket: str, subject: str) -> str:
    # Namespaced by database so the test suite never shares counters with the running app.
    return f"{get_settings().mongo_db}:rl:{bucket}:{subject}"


async def hit(bucket: str, subject: str, limit: int, window_seconds: int) -> None:
    """Count one attempt; raise RateLimited once `limit` is exceeded within the window."""
    key = _key(bucket, subject)
    try:
        redis = cache.get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
    except Exception as exc:  # Redis down/unreachable → don't block the request.
        log.warning("rate-limit backend unavailable, allowing request (%s)", exc)
        return
    if count > limit:
        try:
            ttl = await redis.ttl(key)
        except Exception:
            ttl = window_seconds
        raise RateLimited(ttl if ttl and ttl > 0 else window_seconds)


async def remaining_cooldown(bucket: str, subject: str) -> int:
    try:
        ttl = await cache.get_redis().ttl(_key(bucket, subject))
    except Exception:
        return 0
    return ttl if ttl and ttl > 0 else 0


async def start_cooldown(bucket: str, subject: str, seconds: int) -> None:
    try:
        await cache.get_redis().set(_key(bucket, subject), "1", ex=seconds)
    except Exception as exc:
        log.warning("rate-limit cooldown skipped, backend unavailable (%s)", exc)


async def reset(bucket: str, subject: str) -> None:
    try:
        await cache.get_redis().delete(_key(bucket, subject))
    except Exception:
        pass


async def clear_all(prefix: Optional[str] = None) -> None:
    """Delete every rate-limit key for this database (tests)."""
    redis = cache.get_redis()
    pattern = f"{get_settings().mongo_db}:rl:{prefix or ''}*"
    async for key in redis.scan_iter(match=pattern):
        await redis.delete(key)
