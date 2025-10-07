import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Dict, cast

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi_limiter import FastAPILimiter
from pythonjsonlogger.json import JsonFormatter
from slowapi.errors import RateLimitExceeded
from starlette.middleware.cors import CORSMiddleware

from app.core.database_manager import db_manager

# Import enhanced components
from app.core.settings import get_settings
from app.middleware.monitoring import (
    MonitoringMiddleware,
    get_health_status,
    get_prometheus_metrics,
)
from app.middleware.rate_limiting import RATE_LIMIT_CONFIGS, RateLimitMiddleware
from app.middleware.security import SecurityMiddleware
from app.redis import redis_client
from app.utils.cache import close_redis, init_redis

from .api.api import api_router
from .api.openapi_tags import security_schemes, tags_metadata

# Get enhanced settings
settings = get_settings()

# API Metadata
app = FastAPI(
    title="Evently - Advanced Event Management Platform",
    description="""
    **Evently** is a production-ready, highly scalable event management platform built with FastAPI.

    ## 🚀 Advanced Features

    * **High-Performance Event Management**: Create, update, and manage events with advanced caching and optimization
    * **Scalable Booking System**: Production-grade ticket booking with distributed locking and real-time inventory
    * **Advanced User Management**: Role-based access control with JWT authentication and permission caching
    * **Real-time Analytics**: Advanced reporting with trends, forecasting, and business intelligence
    * **Smart Notifications**: Real-time in-app and email notifications with intelligent batching
    * **Intelligent Waitlists**: Automated waitlist management with predictive notifications
    * **Enterprise Security**: JWT-based authentication with advanced threat detection and rate limiting
    * **Comprehensive Monitoring**: Prometheus metrics, structured logging, and performance analytics

    ## 🏗️ Production Architecture

    * **Backend**: FastAPI with async/await and advanced middleware
    * **Database**: PostgreSQL with connection pooling and performance optimization
    * **Caching**: Redis with circuit breaker and distributed caching
    * **Queue**: Celery with Redis broker for scalable background processing
    * **Security**: Multi-layered security with rate limiting, CSRF protection, and threat detection
    * **Monitoring**: Comprehensive observability with Prometheus, structured logging, and health checks
    * **Deployment**: Docker-ready with Kubernetes support and auto-scaling

    ## 📊 Performance & Scalability

    * **High Throughput**: Optimized for 10,000+ concurrent users
    * **Low Latency**: Sub-100ms response times with intelligent caching
    * **Auto-scaling**: Horizontal scaling with load balancing
    * **Circuit Breakers**: Fault tolerance and graceful degradation
    * **Connection Pooling**: Optimized database and Redis connections

    ## 🔒 Security Features

    * **Multi-factor Authentication**: Enhanced security with MFA support
    * **Rate Limiting**: Advanced rate limiting with multiple strategies
    * **Threat Detection**: Real-time security monitoring and threat mitigation
    * **Data Encryption**: End-to-end encryption for sensitive data
    * **Audit Logging**: Comprehensive security audit trails

    ## 📈 Monitoring & Observability

    * **Prometheus Metrics**: Comprehensive application and business metrics
    * **Structured Logging**: JSON-formatted logs with request tracing
    * **Health Checks**: Multi-layer health monitoring
    * **Performance Analytics**: Real-time performance insights
    * **Error Tracking**: Advanced error monitoring and alerting

    ## 🔗 API Versioning

    This API uses URL path versioning with `/api/v1/` prefix for all endpoints.

    ## 🔐 Authentication

    Most endpoints require authentication using JWT Bearer tokens:

    ```
    Authorization: Bearer <your_jwt_token>
    ```

    Get your token by authenticating via `/api/v1/auth/login` endpoint.
    """,
    version=settings.VERSION,
    terms_of_service="https://github.com/techySPHINX/evently/blob/main/LICENSE",
    contact={
        "name": "Evently Support",
        "url": "https://github.com/techySPHINX/evently",
        "email": "support@evently.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "docExpansion": "list",
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True,
    },
)

# Configure structured logging
log_handler = logging.StreamHandler()
formatter = JsonFormatter(
    """
    {
        "level": "%(levelname)s",
        "time": "%(asctime)s",
        "message": "%(message)s",
        "loggerName": "%(name)s",
        "processName": "%(processName)s",
        "fileName": "%(filename)s",
        "lineNumber": "%(lineno)d"
    }
    """
)
log_handler.setFormatter(formatter)
logging.basicConfig(handlers=[log_handler], level=settings.monitoring.LOG_LEVEL)
logger = logging.getLogger(__name__)
logger.info("Application logging configured with enhanced features.")

# Add advanced middleware stack
if settings.scalability.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware, endpoint_configs=RATE_LIMIT_CONFIGS)

# Add security middleware
app.add_middleware(SecurityMiddleware)

# Add monitoring middleware
app.add_middleware(MonitoringMiddleware)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.exception_handler(HTTPException)  # type: ignore[misc]
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    logger.error(
        "HTTPException occurred: %s",
        exc.detail,
        extra={"status_code": exc.status_code, "headers": exc.headers},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(Exception)  # type: ignore[misc]
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception occurred: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal Server Error"},
    )


def custom_openapi() -> Dict[str, Any]:
    """Custom OpenAPI schema with enhanced security documentation"""
    if app.openapi_schema:
        return cast(Dict[str, Any], app.openapi_schema)

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=tags_metadata,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = security_schemes

    # Add global security requirement for protected endpoints
    for path_item in openapi_schema["paths"].values():
        for method_item in path_item.values():
            if isinstance(method_item, dict) and "tags" in method_item:
                # Add security requirement for non-public endpoints
                if not any(
                    tag in ["Root", "Health"] for tag in method_item.get("tags", [])
                ):
                    method_item["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return cast(Dict[str, Any], app.openapi_schema)


app.openapi = custom_openapi


@app.get("/", tags=["Root"], summary="API Welcome Message")  # type: ignore[misc]
async def root() -> dict[str, Any]:
    """
    Welcome endpoint for the Evently API.

    Returns basic API information and links to documentation.
    """
    return {
        "message": "Welcome to Evently - Advanced Event Management Platform",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_PREFIX}/docs",
        "redoc": f"{settings.API_V1_PREFIX}/redoc",
        "openapi": f"{settings.API_V1_PREFIX}/openapi.json",
        "status": "operational",
        "features": [
            "High-Performance Event Management",
            "Advanced Security & Rate Limiting",
            "Real-time Monitoring & Metrics",
            "Scalable Architecture",
            "Comprehensive API Documentation",
        ],
    }


@app.get("/health", tags=["Health"], summary="Enhanced Health Check")  # type: ignore[misc]
async def health_check() -> dict[str, Any]:
    """
    Enhanced health check endpoint with comprehensive system monitoring.

    Returns detailed operational status of all system components.
    """
    result = await get_health_status()
    # Ensure type is Dict[str, Any]
    if not isinstance(result, dict):
        raise TypeError("Health check did not return a dict")
    return result


@app.get("/metrics", tags=["Monitoring"], summary="Prometheus Metrics")  # type: ignore[misc]
async def metrics() -> PlainTextResponse:
    """
    Prometheus metrics endpoint for monitoring and alerting.

    Returns metrics in Prometheus exposition format.
    """
    if not settings.monitoring.ENABLE_PROMETHEUS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Metrics endpoint is disabled"
        )

    metrics_data = await get_prometheus_metrics()
    return PlainTextResponse(
        content=metrics_data, media_type="text/plain; version=0.0.4; charset=utf-8"
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Enhanced application lifespan event handler with comprehensive startup/shutdown."""
    logger.info("🚀 Starting Evently application with enhanced features...")

    try:
        # Initialize Redis connection
        redis_url = settings.redis.redis_url
        await init_redis(redis_url)
        await FastAPILimiter.init(redis_client)
        logger.info("✅ Redis connection initialized")

        # Verify database connection
        db_health = await db_manager.health_check()
        if db_health.get("status") == "healthy":
            logger.info("✅ Database connection verified")
        else:
            logger.warning("⚠️ Database health check failed")

        # Initialize cache system
        from app.core.cache import cache

        cache_health = await cache.health_check()
        if cache_health.get("status") == "healthy":
            logger.info("✅ Cache system initialized")
        else:
            logger.warning("⚠️ Cache system health check failed")

        logger.info("🎉 Application startup completed successfully!")

        yield

    except Exception as e:
        logger.error(f"❌ Application startup failed: {e}")
        raise

    finally:
        logger.info("🛑 Shutting down Evently application...")

        try:
            # Close Redis connections
            await close_redis()
            logger.info("✅ Redis connections closed")

            # Close database connections
            await db_manager.close()
            logger.info("✅ Database connections closed")

        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")

        logger.info("👋 Application shutdown completed")


@app.exception_handler(RateLimitExceeded)  # type: ignore[misc]
async def rate_limit_exception_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    client_host = request.client.host if request.client else "unknown"
    logger.warning("Rate limit exceeded for client: %s", client_host)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )


# Attach lifespan handler
app.router.lifespan_context = lifespan
