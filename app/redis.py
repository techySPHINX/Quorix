import redis.asyncio as redis  # type: ignore

from .core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
