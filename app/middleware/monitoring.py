"""
Advanced Monitoring & Observability Middleware
Provides comprehensive monitoring, metrics collection, and observability features.
"""

import asyncio
import logging
import time
import traceback
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import structlog
from fastapi import Request, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.cache import cache
from app.core.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        (
            structlog.processors.JSONRenderer()
            if settings.monitoring.LOG_FORMAT == "json"
            else structlog.dev.ConsoleRenderer()
        ),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Get structured logger
struct_logger = structlog.get_logger()


class PrometheusMetrics:
    """Prometheus metrics collection"""

    def __init__(self) -> None:
        # HTTP metrics
        self.http_requests_total = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status_code", "version"],
        )

        self.http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "HTTP request latency",
            ["method", "endpoint", "version"],
            buckets=(
                0.005,
                0.01,
                0.025,
                0.05,
                0.075,
                0.1,
                0.25,
                0.5,
                0.75,
                1.0,
                2.5,
                5.0,
                7.5,
                10.0,
            ),
        )

        self.http_request_size_bytes = Histogram(
            "http_request_size_bytes",
            "HTTP request size in bytes",
            ["method", "endpoint"],
        )

        self.http_response_size_bytes = Histogram(
            "http_response_size_bytes",
            "HTTP response size in bytes",
            ["method", "endpoint", "status_code"],
        )

        # Application metrics
        self.active_connections = Gauge(
            "active_connections", "Number of active connections"
        )

        self.database_connections_active = Gauge(
            "database_connections_active", "Number of active database connections"
        )

        self.cache_operations_total = Counter(
            "cache_operations_total", "Total cache operations", ["operation", "result"]
        )

        self.background_tasks_total = Counter(
            "background_tasks_total", "Total background tasks", ["task_name", "status"]
        )

        self.errors_total = Counter(
            "errors_total", "Total application errors", ["error_type", "endpoint"]
        )

        # Business metrics
        self.user_registrations_total = Counter(
            "user_registrations_total", "Total user registrations"
        )

        self.events_created_total = Counter(
            "events_created_total", "Total events created"
        )

        self.bookings_total = Counter("bookings_total", "Total bookings", ["status"])

    def record_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        version: str = "v1",
    ) -> None:
        """Record HTTP request metrics"""
        self.http_requests_total.labels(
            method=method, endpoint=endpoint, status_code=status_code, version=version
        ).inc()

        self.http_request_duration_seconds.labels(
            method=method, endpoint=endpoint, version=version
        ).observe(duration)

    def record_request_size(self, method: str, endpoint: str, size: int) -> None:
        """Record request size metrics"""
        self.http_request_size_bytes.labels(method=method, endpoint=endpoint).observe(
            size
        )

    def record_response_size(
        self, method: str, endpoint: str, status_code: int, size: int
    ) -> None:
        """Record response size metrics"""
        self.http_response_size_bytes.labels(
            method=method, endpoint=endpoint, status_code=status_code
        ).observe(size)

    def record_error(self, error_type: str, endpoint: str) -> None:
        """Record application error"""
        self.errors_total.labels(error_type=error_type, endpoint=endpoint).inc()


class RequestTracker:
    """Track active requests and their performance"""

    def __init__(self) -> None:
        self.active_requests: Dict[str, Dict[str, Any]] = {}

    def start_request(self, request_id: str, request: Request) -> Dict[str, Any]:
        """Start tracking a request"""
        request_context = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "start_time": time.time(),
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.active_requests[request_id] = request_context
        return request_context

    def finish_request(
        self,
        request_id: str,
        response: Optional[Response],
        error: Optional[Exception] = None,
    ) -> Optional[Dict[str, Any]]:
        """Finish tracking a request"""
        if request_id not in self.active_requests:
            return None

        request_context = self.active_requests[request_id]
        end_time = time.time()
        duration = end_time - request_context["start_time"]

        request_context.update(
            {
                "end_time": end_time,
                "duration": duration,
                "status_code": response.status_code if response else None,
                "response_headers": dict(response.headers) if response else None,
                "error": str(error) if error else None,
                "error_type": error.__class__.__name__ if error else None,
            }
        )

        # Remove from active requests
        del self.active_requests[request_id]

        return request_context

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return str(forwarded.split(",")[0].strip())

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return str(real_ip.strip())

        return str(request.client.host) if request.client else "unknown"

    def get_active_requests(self) -> List[Dict[str, Any]]:
        """Get list of currently active requests"""
        return list(self.active_requests.values())


class PerformanceAnalyzer:
    """Analyze application performance and identify bottlenecks"""

    def __init__(self) -> None:
        self.slow_queries: list[Dict[str, Any]] = []
        self.error_patterns: dict[str, int] = {}
        self.endpoint_stats: dict[str, Dict[str, Any]] = {}

    async def analyze_request(self, request_context: Dict[str, Any]) -> None:
        """Analyze completed request for performance insights"""
        endpoint = request_context.get("path", "unknown")
        duration = request_context.get("duration", 0)
        status_code = request_context.get("status_code", 0)

        # Update endpoint statistics
        if endpoint not in self.endpoint_stats:
            self.endpoint_stats[endpoint] = {
                "count": 0,
                "total_duration": 0,
                "error_count": 0,
                "avg_duration": 0,
                "max_duration": 0,
                "min_duration": float("inf"),
            }

        stats = self.endpoint_stats[endpoint]
        stats["count"] += 1
        stats["total_duration"] += duration
        stats["avg_duration"] = stats["total_duration"] / stats["count"]
        stats["max_duration"] = max(stats["max_duration"], duration)
        stats["min_duration"] = min(stats["min_duration"], duration)

        if status_code >= 400:
            stats["error_count"] += 1

        # Detect slow requests
        slow_threshold = 2.0  # 2 seconds
        if duration > slow_threshold:
            self.slow_queries.append(
                {
                    "timestamp": request_context.get("timestamp"),
                    "endpoint": endpoint,
                    "duration": duration,
                    "method": request_context.get("method"),
                    "query_params": request_context.get("query_params"),
                    "client_ip": request_context.get("client_ip"),
                }
            )

            # Keep only recent slow queries
            if len(self.slow_queries) > 100:
                self.slow_queries = self.slow_queries[-100:]

        # Store analytics in cache for dashboard
        await self._store_analytics()

    async def _store_analytics(self) -> None:
        """Store analytics data in cache"""
        analytics_data = {
            "endpoint_stats": self.endpoint_stats,
            "slow_queries": self.slow_queries[-10:],  # Last 10 slow queries
            "timestamp": time.time(),
        }

        await cache.set("performance_analytics", analytics_data, 300)  # 5 minutes

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        total_requests = sum(stats["count"] for stats in self.endpoint_stats.values())
        total_errors = sum(
            stats["error_count"] for stats in self.endpoint_stats.values()
        )

        # Find slowest endpoints
        slowest_endpoints = sorted(
            self.endpoint_stats.items(),
            key=lambda x: x[1]["avg_duration"],
            reverse=True,
        )[:5]

        return {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": (
                (total_errors / total_requests * 100) if total_requests > 0 else 0
            ),
            "slowest_endpoints": [
                {
                    "endpoint": endpoint,
                    "avg_duration": stats["avg_duration"],
                    "max_duration": stats["max_duration"],
                    "count": stats["count"],
                }
                for endpoint, stats in slowest_endpoints
            ],
            "recent_slow_queries_count": len(self.slow_queries),
        }


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive monitoring middleware providing:
    - Request/response tracking
    - Performance metrics
    - Error monitoring
    - Structured logging
    - Prometheus metrics
    - Performance analysis
    """

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.metrics = PrometheusMetrics()
        self.request_tracker = RequestTracker()
        self.performance_analyzer = PerformanceAnalyzer()
        if settings.monitoring.ENABLE_PROMETHEUS:
            asyncio.create_task(self._start_metrics_collection())

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with comprehensive monitoring"""
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Start request tracking
        request_context = self.request_tracker.start_request(request_id, request)

        # Add request ID to request state
        request.state.request_id = request_id

        # Log request start
        struct_logger.info(
            "request_started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            client_ip=request_context["client_ip"],
            user_agent=request_context["user_agent"],
        )

        start_time = time.time()
        response = None
        error = None

        try:
            # Update active connections
            self.metrics.active_connections.inc()

            # Record request size
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    request_size = int(content_length)
                    self.metrics.record_request_size(
                        request.method, request.url.path, request_size
                    )
                except ValueError:
                    pass

            # Process request
            response = await call_next(request)

            # Calculate response time
            duration = time.time() - start_time

            # Record metrics
            self.metrics.record_request(
                request.method, request.url.path, response.status_code, duration
            )

            # Record response size
            if hasattr(response, "headers") and "content-length" in response.headers:
                try:
                    response_size = int(response.headers["content-length"])
                    self.metrics.record_response_size(
                        request.method,
                        request.url.path,
                        response.status_code,
                        response_size,
                    )
                except ValueError:
                    pass

            # Add monitoring headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.3f}s"

            # Log successful request
            struct_logger.info(
                "request_completed",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                duration=duration,
                client_ip=request_context["client_ip"],
            )

            return response

        except Exception as e:
            error = e
            duration = time.time() - start_time

            # Record error metrics
            self.metrics.record_error(error.__class__.__name__, request.url.path)

            # Log error
            struct_logger.error(
                "request_failed",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                duration=duration,
                error=str(e),
                error_type=error.__class__.__name__,
                traceback=traceback.format_exc(),
                client_ip=request_context["client_ip"],
            )

            raise

        finally:
            # Update active connections
            self.metrics.active_connections.dec()

            # Finish request tracking
            final_context = self.request_tracker.finish_request(
                request_id, response, error
            )

            # Analyze performance (async)
            if final_context:
                asyncio.create_task(
                    self.performance_analyzer.analyze_request(final_context)
                )

    async def _start_metrics_collection(self) -> None:
        while True:
            try:
                # Collect database metrics
                from app.core.database_manager import db_manager

                db_health = await db_manager.health_check()
                if db_health.get("pool_status"):
                    pool_status = db_health["pool_status"]
                    self.metrics.database_connections_active.set(
                        pool_status.get("checked_out", 0)
                    )
                # Collect cache metrics
                from app.core.cache import cache

                cache_health = await cache.health_check()
                if cache_health.get("status") == "healthy":
                    cache_metrics = cache_health.get("metrics", {})
                    # Record cache operations
                    if "hits" in cache_metrics:
                        self.metrics.cache_operations_total.labels(
                            operation="get", result="hit"
                        )._value._value = cache_metrics["hits"]
                    if "misses" in cache_metrics:
                        self.metrics.cache_operations_total.labels(
                            operation="get", result="miss"
                        )._value._value = cache_metrics["misses"]
                await asyncio.sleep(30)  # Collect every 30 seconds
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(30)


# Health check endpoint data
async def get_health_status() -> Dict[str, Any]:
    """Get comprehensive health status"""
    from app.core.cache import cache
    from app.core.database_manager import db_manager

    # Check database health
    db_health = await db_manager.health_check()

    # Check cache health
    cache_health = await cache.health_check()

    # Get system metrics
    system_info = {
        "timestamp": time.time(),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }

    # Overall health status
    overall_status = "healthy"
    if db_health.get("status") != "healthy" or cache_health.get("status") != "healthy":
        overall_status = "degraded"

    return {
        "status": overall_status,
        "system": system_info,
        "database": db_health,
        "cache": cache_health,
        "checks": {
            "database": db_health.get("status") == "healthy",
            "cache": cache_health.get("status") == "healthy",
        },
    }


# Metrics endpoint
async def get_prometheus_metrics() -> str:
    """Get Prometheus metrics"""
    return str(generate_latest().decode("utf-8"))
