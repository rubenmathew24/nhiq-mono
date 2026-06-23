import json
from typing import Any

import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.config import settings

LOOKUP_TTL_SECONDS = 7 * 24 * 60 * 60

_redis: redis.Redis | None = None
_memory_store: dict[str, str] = {}


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def _lookup_key(address_id: str) -> str:
    return f"lookup:{address_id}"


async def save_lookup(address_id: str, data: dict[str, Any]) -> None:
    key = _lookup_key(address_id)
    payload = json.dumps(data)
    try:
        client = await get_redis()
        await client.setex(key, LOOKUP_TTL_SECONDS, payload)
    except (RedisConnectionError, OSError):
        if settings.ENVIRONMENT != "development":
            raise
        _memory_store[key] = payload


async def get_lookup(address_id: str) -> dict[str, Any] | None:
    key = _lookup_key(address_id)
    try:
        client = await get_redis()
        raw = await client.get(key)
        if raw is not None:
            return json.loads(raw)
    except (RedisConnectionError, OSError):
        if settings.ENVIRONMENT != "development":
            raise

    raw = _memory_store.get(key)
    if raw is None:
        return None
    return json.loads(raw)
