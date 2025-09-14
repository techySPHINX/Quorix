from typing import Any, Dict, cast

from fastapi import FastAPI
from sqlalchemy import text
from starlette.middleware.cors import CORSMiddleware

from .api.api import api_router
from .api.openapi_tags import security_schemes, tags_metadata
from .core.config import settings

# API Metadata
app = FastAPI(
    title="Evently - Event Management & Ticketing System",
    description="""
    **Evently** is a comprehensive event management and ticketing platform built with FastAPI.

    ## Features

    * **Event Management**: Create, update, and manage events with detailed information
    * **Booking System**: Production-grade ticket booking with concurrency control and waitlists
    * **User Management**: Role-based access control (Admin/User) with JWT authentication
    * **Analytics**: Advanced reporting with trends, forecasting, and business intelligence
    * **Notifications**: Real-time in-app and email notifications with user preferences
    * **Waitlists**: Automated waitlist management with smart notifications
    * **Security**: JWT-based authentication with hierarchical permissions

    ## Architecture

    * **Backend**: FastAPI with async/await support
    * **Database**: PostgreSQL with SQLAlchemy 2.0 ORM
    * **Caching**: Redis for distributed locking and session management
    * **Queue**: Celery with Redis broker for background tasks
    * **Email**: Production SMTP service with retry logic
    * **Authentication**: JWT tokens with role-based permissions

    ## API Versioning

    This API uses URL path versioning with `/api/v1/` prefix for all endpoints.

    ## Authentication

    Most endpoints require authentication using JWT Bearer tokens:

    ```
    Authorization: Bearer <your_jwt_token>
    ```

    Get your token by authenticating via `/api/v1/auth/login` endpoint.
    """,
    version="1.0.0",
    terms_of_service="https://example.com/terms/",
    contact={
        "name": "Evently Support",
        "url": "https://example.com/contact/",
        "email": "support@evently.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,  # Hide schemas by default
        "docExpansion": "list",  # Expand operations list
        "filter": True,  # Enable filtering
        "showExtensions": True,
        "showCommonExtensions": True,
    },
)

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
app.include_router(api_router, prefix=settings.API_V1_STR)


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
        "message": "Welcome to Evently API",
        "version": "1.0.0",
        "docs": f"{settings.API_V1_STR}/docs",
        "redoc": f"{settings.API_V1_STR}/redoc",
        "openapi": f"{settings.API_V1_STR}/openapi.json",
        "status": "operational",
    }


@app.get("/health", tags=["Health"], summary="Health Check")  # type: ignore[misc]
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint for monitoring and load balancing.

    Returns the current operational status of the API.
    """
    import time

    from app.database import engine
    from app.redis import redis_client

    start_time = time.time()

    # Check database connection
    db_status = "healthy"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    # Check Redis connection
    redis_status = "healthy"
    try:
        redis_client.ping()
    except Exception:
        redis_status = "unhealthy"

    response_time = round((time.time() - start_time) * 1000, 2)

    return {
        "status": (
            "healthy"
            if db_status == "healthy" and redis_status == "healthy"
            else "degraded"
        ),
        "timestamp": time.time(),
        "response_time_ms": response_time,
        "services": {"database": db_status, "redis": redis_status},
        "version": "1.0.0",
    }
