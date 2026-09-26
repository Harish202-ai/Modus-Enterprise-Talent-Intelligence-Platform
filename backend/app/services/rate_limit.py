"""Fixed-window rate limiting in Redis."""
from typing import Optional

from app import cache
from app.config import get_settings


class RateLimited(Exception):
    def __init__(self, retry_after: int):
        super().__init__("rate limited")
        self.retry_after = max(1, retry_after)


def _key(bucket: str, subject: str) -> str:
    # Namespaced by database so the test suite never shares counters with the running app.
    return f"{get_settings().mongo_db}:rl:{bucket}:{subject}"


async def hit(bucket: str, subject: str, limit: int, window_seconds: int) -> None:
    """Count one attempt; raise RateLimited once `limit` is exceeded within the window."""
    redis = cache.get_redis()
    key = _key(bucket, subject)
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window_seconds)
    if count > limit:
        ttl = await redis.ttl(key)
        raise RateLimited(ttl if ttl and ttl > 0 else window_seconds)


async def remaining_cooldown(bucket: str, subject: str) -> int:
    ttl = await cache.get_redis().ttl(_key(bucket, subject))
    return ttl if ttl and ttl > 0 else 0


async def start_cooldown(bucket: str, subject: str, seconds: int) -> None:
    await cache.get_redis().set(_key(bucket, subject), "1", ex=seconds)


async def reset(bucket: str, subject: str) -> None:
    await cache.get_redis().delete(_key(bucket, subject))


async def clear_all(prefix: Optional[str] = None) -> None:
    """Delete every rate-limit key for this database (tests)."""
    redis = cache.get_redis()
    pattern = f"{get_settings().mongo_db}:rl:{prefix or ''}*"
    async for key in redis.scan_iter(match=pattern):
        await redis.delete(key)
