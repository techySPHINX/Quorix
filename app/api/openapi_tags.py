"""
OpenAPI Tags Configuration for Evently API

Defines tags and descriptions for organized API documentation.
"""

tags_metadata = [
    {
        "name": "auth",
        "description": """
**Authentication & Authorization**

Endpoints for user authentication, token management, and session control.
Supports JWT-based authentication with access and refresh tokens.

**Authentication Flow:**
1. Login with credentials to get tokens
2. Use access token in Authorization header
3. Refresh tokens before expiration
4. Logout to invalidate tokens
        """,
        "externalDocs": {
            "description": "JWT Authentication Guide",
            "url": "https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/",
        },
    },
    {
        "name": "users",
        "description": """
**User Management**

User profile management, registration, and role-based operations.
Supports hierarchical permissions with User, Admin, and Super Admin roles.

**Key Features:**
- User registration and profile management
- Role-based access control
- Password management and security
- User preferences and settings
        """,
    },
    {
        "name": "events",
        "description": """
**Event Management**

Create, manage, and discover events with comprehensive filtering and search capabilities.
Includes real-time availability tracking and cache optimization.

**Features:**
- Event creation and management (Admin only)
- Advanced filtering (location, price, availability)
- Real-time capacity tracking
- Cached responses for performance
        """,
    },
    {
        "name": "bookings",
        "description": """
**Booking System**

Production-grade ticket booking system with concurrency control, atomic transactions,
and comprehensive booking lifecycle management.

**Key Features:**
- Atomic booking operations with race condition protection
- Distributed locking for high-concurrency scenarios
- Automatic waitlist management
- Booking confirmation and cancellation
- Real-time availability updates
        """,
    },
    {
        "name": "waitlist",
        "description": """
**Waitlist Management**

Intelligent waitlist system that automatically notifies users when tickets become available.
Includes prioritized notifications and automated booking opportunities.

**Features:**
- Automatic waitlist enrollment for sold-out events
- FIFO (First-In-First-Out) notification system
- Smart availability detection
- Email and in-app notifications
        """,
    },
    {
        "name": "notifications",
        "description": """
**Notification System**

Comprehensive notification system supporting both in-app and email delivery
with user preferences, batching, and reliable delivery guarantees.

**Features:**
- Multi-channel notifications (email + in-app)
- User notification preferences
- Bulk notification processing
- Delivery status tracking
- Notification history and management
        """,
    },
    {
        "name": "analytics",
        "description": """
**Analytics & Reporting**

Advanced analytics engine providing insights into event performance,
booking trends, user behavior, and business intelligence.

**Available Reports:**
- Event booking statistics and trends
- User engagement analytics
- Revenue and utilization metrics
- Predictive analytics and forecasting
- Real-time dashboard data
        """,
    },
]

# Response models for common error scenarios
common_responses = {
    400: {
        "description": "Bad Request",
        "content": {
            "application/json": {
                "example": {"detail": "Invalid request parameters or data"}
            }
        },
    },
    401: {
        "description": "Unauthorized",
        "content": {
            "application/json": {
                "examples": {
                    "missing_token": {
                        "summary": "Missing Authentication",
                        "value": {"detail": "Not authenticated"},
                    },
                    "invalid_token": {
                        "summary": "Invalid Token",
                        "value": {"detail": "Could not validate credentials"},
                    },
                    "expired_token": {
                        "summary": "Expired Token",
                        "value": {"detail": "Token has expired"},
                    },
                }
            }
        },
    },
    403: {
        "description": "Forbidden",
        "content": {
            "application/json": {"example": {"detail": "Insufficient permissions"}}
        },
    },
    404: {
        "description": "Not Found",
        "content": {"application/json": {"example": {"detail": "Resource not found"}}},
    },
    422: {
        "description": "Validation Error",
        "content": {
            "application/json": {
                "example": {
                    "detail": [
                        {
                            "loc": ["body", "field_name"],
                            "msg": "field required",
                            "type": "value_error.missing",
                        }
                    ]
                }
            }
        },
    },
    429: {
        "description": "Rate Limited",
        "content": {
            "application/json": {
                "example": {"detail": "Rate limit exceeded. Please try again later."}
            }
        },
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {"example": {"detail": "Internal server error"}}
        },
    },
}

# Security schemes for OpenAPI documentation
security_schemes = {
    "BearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": """
JWT (JSON Web Token) authentication.

**How to authenticate:**
1. Login via `/auth/login/access-token` to get your JWT token
2. Include the token in the Authorization header: `Authorization: Bearer <your_token>`
3. Tokens expire after 30 minutes - use refresh token to get new access token

**Example:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```
        """,
    }
}
