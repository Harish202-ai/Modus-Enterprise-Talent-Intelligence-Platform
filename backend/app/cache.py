"""Redis client (session state, rate limits, queues). Never the source of truth."""
import logging
from typing import Optional

from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from app.config import get_settings

log = logging.getLogger(__name__)

_redis: Optional[Redis] = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        # Fail FAST when Redis is unreachable (2s, no retries) so callers that fail
        # open — like rate limiting — don't hang the request. Redis is best-effort
        # (rate limits, cooldowns); the source of truth is Mongo.
        _redis = Redis.from_url(
            get_settings().redis_uri,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry=Retry(NoBackoff(), 0),
            retry_on_timeout=False,
        )
    return _redis


async def ping() -> bool:
    try:
        return bool(await get_redis().ping())
    except Exception:  # noqa: BLE001 - health check must never raise
        log.exception("redis ping failed")
        return False


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
