"""
Advanced Rate Limiting Middleware
Provides sophisticated rate limiting with multiple strategies and storage backends.
"""
import time
import hashlib
import logging
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.cache import cache
from app.core.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"  # Not a password, just a constant name for strategy type  # nosec


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests: int  # Number of requests allowed
    window: int    # Time window in seconds
    strategy: RateLimitStrategy = RateLimitStrategy.FIXED_WINDOW
    burst: Optional[int] = None  # Burst capacity for token bucket


class RateLimiter:
    """Advanced rate limiter with multiple strategies"""

    def __init__(self, config: RateLimitConfig):
        self.config = config

    async def is_allowed(self, identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limit

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        if self.config.strategy == RateLimitStrategy.FIXED_WINDOW:
            return await self._fixed_window_check(identifier)
        elif self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._sliding_window_check(identifier)
        elif self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._token_bucket_check(identifier)
        else:
            raise ValueError(f"Unknown rate limit strategy: {self.config.strategy}")

    async def _fixed_window_check(self, identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Fixed window rate limiting"""
        current_time = int(time.time())
        window_start = current_time - (current_time % self.config.window)

        # Create rate limit key
        rate_limit_key = f"rate_limit:fixed:{identifier}:{window_start}"

        # Get current request count
        current_requests = await cache.get(rate_limit_key, 0)

        if current_requests >= self.config.requests:
            return False, {
                "limit": self.config.requests,
                "remaining": 0,
                "reset": window_start + self.config.window,
                "retry_after": window_start + self.config.window - current_time
            }

        # Increment request count
        await cache.set(rate_limit_key, current_requests + 1, self.config.window)

        return True, {
            "limit": self.config.requests,
            "remaining": max(0, self.config.requests - current_requests - 1),
            "reset": window_start + self.config.window,
            "retry_after": 0
        }

    async def _sliding_window_check(self, identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Sliding window rate limiting using sorted sets"""
        current_time = time.time()
        window_start = current_time - self.config.window

        rate_limit_key = f"rate_limit:sliding:{identifier}"

        # This is a simplified implementation
        # In production, you might want to use Redis sorted sets for more accuracy

        # Get request timestamps from cache
        requests_data = await cache.get(rate_limit_key, [])

        # Filter requests within the current window
        valid_requests = [req_time for req_time in requests_data if req_time > window_start]

        if len(valid_requests) >= self.config.requests:
            oldest_request = min(valid_requests)
            retry_after = int(oldest_request + self.config.window - current_time)

            return False, {
                "limit": self.config.requests,
                "remaining": 0,
                "reset": int(oldest_request + self.config.window),
                "retry_after": max(0, retry_after)
            }

        # Add current request
        valid_requests.append(current_time)

        # Store updated requests (keep only recent ones)
        await cache.set(rate_limit_key, valid_requests, self.config.window)

        return True, {
            "limit": self.config.requests,
            "remaining": max(0, self.config.requests - len(valid_requests)),
            "reset": int(current_time + self.config.window),
            "retry_after": 0
        }

    async def _token_bucket_check(self, identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Token bucket rate limiting"""
        current_time = time.time()
        rate_limit_key = f"rate_limit:bucket:{identifier}"

        # Get bucket state
        bucket_data = await cache.get(rate_limit_key, {
            "tokens": self.config.requests,
            "last_refill": current_time
        })

        # Calculate tokens to add based on elapsed time
        elapsed = current_time - bucket_data["last_refill"]
        tokens_to_add = elapsed * (self.config.requests / self.config.window)

        # Refill bucket
        bucket_data["tokens"] = min(
            self.config.requests,
            bucket_data["tokens"] + tokens_to_add
        )
        bucket_data["last_refill"] = current_time

        if bucket_data["tokens"] < 1:
            # Calculate retry after
            tokens_needed = 1 - bucket_data["tokens"]
            retry_after = int(tokens_needed * (self.config.window / self.config.requests))

            return False, {
                "limit": self.config.requests,
                "remaining": 0,
                "reset": int(current_time + retry_after),
                "retry_after": retry_after
            }

        # Consume one token
        bucket_data["tokens"] -= 1

        # Store updated bucket state
        await cache.set(rate_limit_key, bucket_data, self.config.window * 2)

        return True, {
            "limit": self.config.requests,
            "remaining": int(bucket_data["tokens"]),
            "reset": int(current_time + self.config.window),
            "retry_after": 0
        }


class IPWhitelist:
    """IP address whitelist management"""

    def __init__(self):
        self.whitelist = set()
        self._load_whitelist()

    def _load_whitelist(self):
        """Load IP whitelist from configuration"""
        # This could be loaded from database, config file, etc.
        whitelist_ips = getattr(settings, 'RATE_LIMIT_WHITELIST', [])
        self.whitelist.update(whitelist_ips)

        # Add localhost and common development IPs
        self.whitelist.update(['127.0.0.1', '::1', 'localhost'])

    def is_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted"""
        return ip in self.whitelist

    def add_ip(self, ip: str):
        """Add IP to whitelist"""
        self.whitelist.add(ip)

    def remove_ip(self, ip: str):
        """Remove IP from whitelist"""
        self.whitelist.discard(ip)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Advanced rate limiting middleware with multiple strategies and features:
    - Multiple rate limiting strategies
    - IP whitelisting
    - Different limits for different endpoints
    - User-based rate limiting
    - Detailed rate limit headers
    """

    def __init__(
        self,
        app,
        default_config: Optional[RateLimitConfig] = None,
        endpoint_configs: Optional[Dict[str, RateLimitConfig]] = None
    ):
        super().__init__(app)

        # Default configuration
        self.default_config = default_config or RateLimitConfig(
            requests=settings.scalability.RATE_LIMIT_REQUESTS,
            window=settings.scalability.RATE_LIMIT_WINDOW,
            strategy=RateLimitStrategy.FIXED_WINDOW
        )

        # Endpoint-specific configurations
        self.endpoint_configs = endpoint_configs or {}

        # IP whitelist
        self.ip_whitelist = IPWhitelist()

        # Rate limiters cache
        self._rate_limiters: Dict[str, RateLimiter] = {}

    def _get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Try to get user ID from request state (set by auth middleware)
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        return f"ip:{self._get_client_ip(request)}"

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded headers (load balancer/proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Get the first IP in the chain
            return forwarded.split(",")[0].strip()

        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct connection
        return request.client.host if request.client else "unknown"

    def _get_rate_limit_config(self, request: Request) -> RateLimitConfig:
        """Get rate limit configuration for the request"""
        # Check for endpoint-specific configuration
        path = request.url.path

        # Try exact match first
        if path in self.endpoint_configs:
            return self.endpoint_configs[path]

        # Try pattern matching
        for pattern, config in self.endpoint_configs.items():
            if path.startswith(pattern):
                return config

        return self.default_config

    def _get_rate_limiter(self, config: RateLimitConfig) -> RateLimiter:
        """Get or create rate limiter for configuration"""
        config_key = f"{config.requests}:{config.window}:{config.strategy.value}"

        if config_key not in self._rate_limiters:
            self._rate_limiters[config_key] = RateLimiter(config)

        return self._rate_limiters[config_key]

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting"""
        # Skip rate limiting if disabled
        if not settings.scalability.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Get client identifier
        client_identifier = self._get_client_identifier(request)
        client_ip = self._get_client_ip(request)

        # Check IP whitelist
        if self.ip_whitelist.is_whitelisted(client_ip):
            response = await call_next(request)
            response.headers["X-RateLimit-Whitelisted"] = "true"
            return response

        # Get rate limit configuration
        config = self._get_rate_limit_config(request)
        rate_limiter = self._get_rate_limiter(config)

        # Check rate limit
        try:
            is_allowed, rate_info = await rate_limiter.is_allowed(client_identifier)

            if not is_allowed:
                # Log rate limit violation
                logger.warning(
                    f"Rate limit exceeded for {client_identifier} "
                    f"on {request.method} {request.url.path}"
                )

                # Create rate limit exceeded response
                response = Response(
                    content='{"detail": "Rate limit exceeded. Please try again later."}',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    media_type="application/json"
                )

                # Add rate limit headers
                response.headers.update(self._get_rate_limit_headers(rate_info))
                return response

            # Process request
            response = await call_next(request)

            # Add rate limit headers to successful response
            response.headers.update(self._get_rate_limit_headers(rate_info))

            return response

        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Continue with request if rate limiting fails
            return await call_next(request)

    def _get_rate_limit_headers(self, rate_info: Dict[str, Any]) -> Dict[str, str]:
        """Generate rate limit headers"""
        return {
            "X-RateLimit-Limit": str(rate_info["limit"]),
            "X-RateLimit-Remaining": str(rate_info["remaining"]),
            "X-RateLimit-Reset": str(rate_info["reset"]),
            "Retry-After": str(rate_info["retry_after"]) if rate_info["retry_after"] > 0 else ""
        }


# Predefined rate limit configurations for different endpoint types
RATE_LIMIT_CONFIGS = {
    "/api/v1/auth/login": RateLimitConfig(
        requests=5,
        window=300,  # 5 requests per 5 minutes
        strategy=RateLimitStrategy.SLIDING_WINDOW
    ),
    "/api/v1/auth/register": RateLimitConfig(
        requests=3,
        window=300,  # 3 requests per 5 minutes
        strategy=RateLimitStrategy.SLIDING_WINDOW
    ),
    "/api/v1/events": RateLimitConfig(
        requests=100,
        window=3600,  # 100 requests per hour
        strategy=RateLimitStrategy.TOKEN_BUCKET
    ),
    "/api/v1/users": RateLimitConfig(
        requests=200,
        window=3600,  # 200 requests per hour
        strategy=RateLimitStrategy.FIXED_WINDOW
    ),
}
