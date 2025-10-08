"""
Advanced Caching Layer with Redis Backend
Provides sophisticated caching capabilities with compression, serialization, and monitoring.
"""

import asyncio
import hashlib
import json
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from app.core.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheSerializer:
    """Handle different serialization methods for cache values"""

    @staticmethod
    def serialize_json(value: Any) -> str:
        """Serialize value using JSON"""
        return json.dumps(value, default=str, ensure_ascii=False)

    @staticmethod
    def deserialize_json(value: str) -> Any:
        """Deserialize JSON value"""
        return json.loads(value)


class CacheMetrics:
    """Track cache performance metrics"""

    def __init__(self) -> None:
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.total_requests = 0
        self.total_response_time = 0.0

    def record_hit(self, response_time: float) -> None:
        """Record cache hit"""
        self.hits += 1
        self.total_requests += 1
        self.total_response_time += response_time

    def record_miss(self, response_time: float) -> None:
        """Record cache miss"""
        self.misses += 1
        self.total_requests += 1
        self.total_response_time += response_time

    def record_error(self) -> None:
        """Record cache error"""
        self.errors += 1
        self.total_requests += 1

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests

    @property
    def average_response_time(self) -> float:
        """Calculate average response time"""
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time / self.total_requests

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "errors": self.errors,
            "total_requests": self.total_requests,
            "hit_rate": round(self.hit_rate * 100, 2),
            "average_response_time_ms": round(self.average_response_time * 1000, 2),
        }

    def reset(self) -> None:
        """Reset all metrics"""
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.total_requests = 0
        self.total_response_time = 0.0


class AdvancedCacheManager:
    """
    Advanced Redis-based cache manager with sophisticated features:
    - Multiple serialization methods
    - Compression support
    - Performance monitoring
    - Circuit breaker pattern
    - Batch operations
    """

    def __init__(self) -> None:
        self.redis_client: Optional[Redis] = None
        self.metrics = CacheMetrics()
        self.serializer = CacheSerializer()
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure: Optional[float] = None
        self._circuit_breaker_threshold = 5
        self._circuit_breaker_timeout = 60  # seconds
        self._setup_redis_client()

    def _setup_redis_client(self) -> None:
        """Setup Redis client with advanced configuration"""
        try:
            self.redis_client = redis.Redis.from_url(
                settings.redis.redis_url,
                max_connections=settings.redis.REDIS_MAX_CONNECTIONS,
                retry_on_timeout=settings.redis.REDIS_RETRY_ON_TIMEOUT,
                socket_timeout=settings.redis.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.redis.REDIS_SOCKET_CONNECT_TIMEOUT,
                health_check_interval=settings.redis.REDIS_HEALTH_CHECK_INTERVAL,
                decode_responses=True,
                encoding="utf-8",
            )
            logger.info("Redis cache client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            self.redis_client = None

    def _make_key(self, key: str, prefix: Optional[str] = None) -> str:
        """Generate cache key with prefix"""
        prefix = prefix or settings.scalability.CACHE_KEY_PREFIX
        return f"{prefix}{key}"

    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open (failing)"""
        if self._circuit_breaker_failures < self._circuit_breaker_threshold:
            return False

        if self._circuit_breaker_last_failure is None:
            return False

        time_since_failure = time.time() - self._circuit_breaker_last_failure
        if time_since_failure > self._circuit_breaker_timeout:
            # Reset circuit breaker
            self._circuit_breaker_failures = 0
            self._circuit_breaker_last_failure = None
            return False
        else:
            return True

    def _record_failure(self) -> None:
        """Record a cache operation failure"""
        self._circuit_breaker_failures += 1
        self._circuit_breaker_last_failure = float(time.time())
        self.metrics.record_error()

    def _record_success(self) -> None:
        """Record a successful cache operation"""
        if self._circuit_breaker_failures > 0:
            self._circuit_breaker_failures = max(0, self._circuit_breaker_failures - 1)

    async def get(
        self, key: str, default: Any = None, prefix: Optional[str] = None
    ) -> Any:
        """Get value from cache with error handling and metrics"""
        if not settings.scalability.CACHE_ENABLED or not self.redis_client:
            return default

        if self._is_circuit_breaker_open():
            logger.warning("Cache circuit breaker is open, returning default")
            return default

        start_time = time.time()
        cache_key = self._make_key(key, prefix)

        try:
            cached_value = await self.redis_client.get(cache_key)
            response_time = time.time() - start_time

            if cached_value is None:
                self.metrics.record_miss(response_time)
                return default

            # Only allow JSON deserialization
            result = self.serializer.deserialize_json(cached_value)

            self.metrics.record_hit(response_time)
            self._record_success()
            return result

        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self._record_failure()
            return default
        except Exception as e:
            logger.error(f"Unexpected cache error for key {key}: {e}")
            self.metrics.record_error()
            return default

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        prefix: Optional[str] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        Set value in cache with advanced options

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            prefix: Key prefix
            nx: Only set if key doesn't exist
            xx: Only set if key exists
        """
        if not settings.scalability.CACHE_ENABLED or not self.redis_client:
            return False

        if self._is_circuit_breaker_open():
            logger.warning("Cache circuit breaker is open, skipping set operation")
            return False

        cache_key = self._make_key(key, prefix)
        ttl = ttl or settings.scalability.CACHE_TTL

        try:
            # Only allow JSON serialization
            serialized_value = self.serializer.serialize_json(value)

            # Set with options
            result = await self.redis_client.set(
                cache_key, serialized_value, ex=ttl, nx=nx, xx=xx
            )

            self._record_success()
            return bool(result)

        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.error(f"Cache set error for key {key}: {e}")
            self._record_failure()
            return False
        except Exception as e:
            logger.error(f"Unexpected cache error for key {key}: {e}")
            self.metrics.record_error()
            return False

    async def delete(self, key: str, prefix: Optional[str] = None) -> bool:
        """Delete key from cache"""
        if not settings.scalability.CACHE_ENABLED or not self.redis_client:
            return False

        if self._is_circuit_breaker_open():
            return False

        cache_key = self._make_key(key, prefix)

        try:
            result = await self.redis_client.delete(cache_key)
            self._record_success()
            return bool(result)
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            self._record_failure()
            return False

    async def exists(self, key: str, prefix: Optional[str] = None) -> bool:
        """Check if key exists in cache"""
        if not settings.scalability.CACHE_ENABLED or not self.redis_client:
            return False

        if self._is_circuit_breaker_open():
            return False

        cache_key = self._make_key(key, prefix)

        try:
            result = await self.redis_client.exists(cache_key)
            self._record_success()
            return bool(result)
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            self._record_failure()
            return False

    async def increment(
        self, key: str, amount: int = 1, prefix: Optional[str] = None
    ) -> Optional[int]:
        """Increment a numeric value in cache"""
        if not settings.scalability.CACHE_ENABLED or not self.redis_client:
            return None

        cache_key = self._make_key(key, prefix)

        try:
            result = await self.redis_client.incr(cache_key, amount)
            self._record_success()
            return int(result) if result is not None else None
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            self._record_failure()
            return None

    async def expire(self, key: str, ttl: int, prefix: Optional[str] = None) -> bool:
        """Set expiration time for a key"""
        if not settings.scalability.CACHE_ENABLED or not self.redis_client:
            return False

        cache_key = self._make_key(key, prefix)

        try:
            result = await self.redis_client.expire(cache_key, ttl)
            self._record_success()
            return bool(result)
        except Exception as e:
            logger.error(f"Cache expire error for key {key}: {e}")
            self._record_failure()
            return False

    async def get_many(
        self, keys: List[str], prefix: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get multiple values from cache"""
        if not settings.scalability.CACHE_ENABLED or not self.redis_client:
            return {}

        if self._is_circuit_breaker_open():
            return {}

        cache_keys = [self._make_key(key, prefix) for key in keys]

        try:
            values = await self.redis_client.mget(cache_keys)
            result = {}

            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = self.serializer.deserialize_json(value)
                    except Exception as e:
                        logger.error(f"Deserialization error for key {key}: {e}")

            self._record_success()
            return result

        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            self._record_failure()
            return {}

    async def set_many(
        self,
        mapping: Dict[str, Any],
        ttl: Optional[int] = None,
        prefix: Optional[str] = None,
    ) -> bool:
        """Set multiple values in cache"""
        if not settings.scalability.CACHE_ENABLED or not self.redis_client:
            return False

        if self._is_circuit_breaker_open():
            return False

        try:
            pipeline = self.redis_client.pipeline()
            ttl = ttl or settings.scalability.CACHE_TTL

            for key, value in mapping.items():
                cache_key = self._make_key(key, prefix)

                serialized_value = self.serializer.serialize_json(value)

                pipeline.setex(cache_key, ttl, serialized_value)

            await pipeline.execute()
            self._record_success()
            return True

        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            self._record_failure()
            return False

    async def clear_pattern(self, pattern: str, prefix: Optional[str] = None) -> int:
        """Clear all keys matching a pattern"""
        if not settings.scalability.CACHE_ENABLED or not self.redis_client:
            return 0

        cache_pattern = self._make_key(pattern, prefix)

        try:
            keys = []
            cursor = 0  # Start with integer 0
            while True:
                cursor, partial_keys = await self.redis_client.scan(
                    cursor=cursor, match=cache_pattern, count=100
                )
                keys.extend(partial_keys)
                if cursor == 0:
                    break

            if keys:
                deleted_count = await self.redis_client.delete(*keys)
                self._record_success()
                return int(deleted_count)

            return 0

        except Exception as e:
            logger.error(f"Cache clear_pattern error: {e}")
            self._record_failure()
            return 0

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive cache health check"""
        if not self.redis_client:
            return {"status": "error", "message": "Redis client not initialized"}

        try:
            start_time = time.time()

            # Test basic connectivity
            await self.redis_client.ping()

            # Test set/get operations
            test_key = "health_check_test"
            test_value = {"timestamp": time.time(), "test": True}

            await self.set(test_key, test_value, ttl=60)
            retrieved_value = await self.get(test_key)

            if retrieved_value != test_value:
                return {"status": "error", "message": "Set/Get operation failed"}

            await self.delete(test_key)

            response_time = (time.time() - start_time) * 1000

            # Get Redis info
            info = await self.redis_client.info()

            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "metrics": self.metrics.get_stats(),
                "circuit_breaker": {
                    "failures": self._circuit_breaker_failures,
                    "is_open": self._is_circuit_breaker_open(),
                },
                "redis_info": {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "version": info.get("redis_version", "unknown"),
                },
            }

        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        return self.metrics.get_stats()

    def reset_metrics(self) -> None:
        """Reset performance metrics"""
        self.metrics.reset()


# Decorator for caching function results
def cache_result(
    ttl: int = 3600,
    key_prefix: str = "func:",
    use_args: bool = True,
    use_kwargs: bool = True,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to cache function results

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys
        use_args: Include function arguments in cache key
        use_kwargs: Include function keyword arguments in cache key
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            key_parts = [func.__name__]

            if use_args and args:
                key_parts.append(str(args))

            if use_kwargs and kwargs:
                key_parts.append(str(sorted(kwargs.items())))

            key_data = ":".join(key_parts)
            cache_key = key_prefix + hashlib.sha256(key_data.encode()).hexdigest()

            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            await cache.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator


# Global cache manager instance
cache = AdvancedCacheManager()
