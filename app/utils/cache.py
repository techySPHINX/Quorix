from typing import Any, Callable, Coroutine, Optional
import json
import redis.asyncio as redis

_redis_client: Optional[redis.Redis] = None


async def init_redis(url: str) -> None:
    """
    Initialize global redis client. Call on FastAPI startup.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(url, decode_responses=True)


async def close_redis() -> None:
    """
    Close global redis connection. Call on FastAPI shutdown.
    """
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


def get_redis() -> redis.Redis:
    """
    Return initialized redis client or raise.
    """
    if _redis_client is None:
        raise RuntimeError("Redis is not initialized. Call init_redis on startup.")
    return _redis_client


async def cache_get(
        key: str,
        ttl: int,
        db_loader: Callable[[], Coroutine[Any, Any, Any]],
        serializer: Callable[[Any], str],
        deserializer: Callable[[str], Any] = lambda s: json.loads(s),
) -> Any:
    """
    Caching-aside helper:
    - Try to read `key` from Redis.
    - If present, return deserialized value.
    - If missing, call async db_loader(), serialize with `serializer`, set with TTL and return DB object.
    Notes:
    - serializer -> returns JSON string (use pydantic_model.model_dump_json()).
    - deserializer -> convert JSON string back to desired type (use Pydantic.model_validate_json()).
    """
    r = get_redis()
    cached = await r.get(key)
    if cached is not None:
        return deserializer(cached)

    obj = await db_loader()
    if obj is None:
        # avoid caching None by default; caller can cache negative results if needed
        return None

    # serialize and set with TTL (seconds)
    payload = serializer(obj)
    await r.set(key, payload, ex=ttl)
    return obj


async def set_cache(key: str, payload_json: str, ttl: int) -> None:
    """
    Directly set a JSON payload into cache with TTL.
    """
    r = get_redis()
    await r.set(key, payload_json, ex=ttl)


async def invalidate_cache(key: str) -> None:
    """
    Delete key from cache (explicit invalidation).
    """
    r = get_redis()
    await r.delete(key)
    r = get_redis()
    await r.delete(key)
