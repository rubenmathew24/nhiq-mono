import json
from typing import Any

import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.config import settings

LOOKUP_TTL_SECONDS = 7 * 24 * 60 * 60
REPORT_TTL_SECONDS = 24 * 60 * 60

_redis: redis.Redis | None = None
_memory_store: dict[str, str] = {}


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def _lookup_key(address_id: str) -> str:
    return f"lookup:{address_id}"


def _report_key(address_id: str) -> str:
    return f"report:{settings.SCORE_DATA_VINTAGE}:{address_id}"


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


async def save_report(address_id: str, data: dict[str, Any]) -> None:
    key = _report_key(address_id)
    payload = json.dumps(data)
    try:
        client = await get_redis()
        await client.setex(key, REPORT_TTL_SECONDS, payload)
    except (RedisConnectionError, OSError):
        if settings.ENVIRONMENT != "development":
            raise
        _memory_store[key] = payload


async def get_report(address_id: str) -> dict[str, Any] | None:
    key = _report_key(address_id)
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


async def invalidate_report_cache(*, address_id: str | None = None) -> int:
    """Drop cached live reports so mocks/stale scores cannot override DB."""
    deleted = 0
    pattern = (
        _report_key(address_id)
        if address_id
        else f"report:{settings.SCORE_DATA_VINTAGE}:*"
    )
    try:
        client = await get_redis()
        async for key in client.scan_iter(match=pattern):
            deleted += await client.delete(key)
    except (RedisConnectionError, OSError):
        if settings.ENVIRONMENT not in ("development", "test"):
            raise
        keys = [k for k in list(_memory_store) if k.startswith("report:")]
        if address_id:
            keys = [k for k in keys if k.endswith(f":{address_id}")]
        for key in keys:
            _memory_store.pop(key, None)
            deleted += 1
    return deleted
