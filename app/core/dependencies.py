"""
Enhanced Dependencies with Advanced Features
Provides dependency injection for authentication, authorization, and advanced features.
"""
from app.models.user import User
from app.crud.user import get as get_user_by_id
import logging
from typing import AsyncGenerator, Optional, Any, Dict
from functools import wraps

from fastapi import Depends, HTTPException, status, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database_manager import get_db
from app.core.cache import cache
from app.core.security import get_password_hash, verify_password
from jose import jwt
from app.core.settings import get_settings

# Placeholder for verify_token (should be implemented properly)


def verify_token(token: str) -> dict:
    raise NotImplementedError("verify_token function must be implemented.")


logger = logging.getLogger(__name__)
settings = get_settings()
security = HTTPBearer()


class UserDependency:
    """
    Advanced user dependency with caching and performance optimization
    """

    def __init__(
        self,
        require_auth: bool = True,
        require_active: bool = True,
        require_verified: bool = False,
        require_admin: bool = False,
        cache_user: bool = True
    ):
        self.require_auth = require_auth
        self.require_active = require_active
        self.require_verified = require_verified
        self.require_admin = require_admin
        self.cache_user = cache_user

    async def __call__(
        self,
        request: Request,
        db: AsyncSession = Depends(get_db),
        credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
    ) -> Optional[User]:
        """Get authenticated user with advanced validation"""

        if not self.require_auth:
            return None

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify token
        try:
            payload = verify_token(credentials.credentials)
        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Try to get user from cache first
        user = None
        if self.cache_user:
            cached_user_data = await cache.get(f"user:{user_id}")
            if cached_user_data:
                try:
                    user = User(**cached_user_data)
                except Exception as e:
                    logger.warning(f"Failed to deserialize cached user: {e}")

        # If not in cache, get from database
        if not user:
            user = await get_user_by_id(db, id=user_id)

            if user and self.cache_user:
                # Cache user data for future requests
                user_data = {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "is_active": user.is_active,
                    "is_superuser": user.is_superuser,
                    "is_verified": getattr(user, 'is_verified', True),
                    # Add other fields as needed
                }
                await cache.set(f"user:{user_id}", user_data, ttl=1800)  # 30 minutes

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Validation checks
        if self.require_active and not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user account"
            )

        if self.require_verified and not getattr(user, 'is_verified', True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email verification required"
            )

        if self.require_admin and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrative privileges required"
            )

        # Add user to request state for logging/monitoring
        request.state.user_id = user.id
        request.state.user_email = user.email

        return user


class PermissionChecker:
    """
    Advanced permission checking system
    """

    def __init__(self, permission: str, resource_type: Optional[str] = None):
        self.permission = permission
        self.resource_type = resource_type

    async def __call__(
        self,
        request: Request,
        user: User = Depends(UserDependency(require_auth=True))
    ) -> bool:
        """Check if user has required permission"""

        # Super users have all permissions
        if user.is_superuser:
            return True

        # Check cached permissions
        permission_key = f"permissions:{user.id}:{self.permission}"
        if self.resource_type:
            permission_key += f":{self.resource_type}"

        cached_permission = await cache.get(permission_key)
        if cached_permission is not None:
            return cached_permission

        # In a real implementation, you would check permissions from database
        # For now, we'll implement basic role-based permissions
        has_permission = await self._check_user_permission(user)

        # Cache permission result
        await cache.set(permission_key, has_permission, ttl=900)  # 15 minutes

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{self.permission}' required"
            )

        return has_permission

    async def _check_user_permission(self, user: User) -> bool:
        """Check user permission (implement your logic here)"""
        # Basic implementation - extend as needed
        permission_map = {
            "events:create": True,  # All authenticated users can create events
            "events:update": True,  # All authenticated users can update their events
            "events:delete": True,  # All authenticated users can delete their events
            "users:list": user.is_superuser,  # Only admins can list users
            "users:create": user.is_superuser,  # Only admins can create users
            "admin:access": user.is_superuser,  # Only admins can access admin features
        }

        return permission_map.get(self.permission, False)


class RateLimitDependency:
    """
    Dependency for endpoint-specific rate limiting
    """

    def __init__(self, requests: int, window: int):
        self.requests = requests
        self.window = window

    async def __call__(self, request: Request) -> bool:
        """Check rate limit for specific endpoint"""
        # This would integrate with the rate limiting middleware
        # For now, it's a placeholder
        return True


# Common dependency instances
get_current_user = UserDependency(require_auth=True, require_active=True)
get_current_user_optional = UserDependency(require_auth=False)
get_current_admin = UserDependency(require_auth=True, require_active=True, require_admin=True)
get_current_verified_user = UserDependency(require_auth=True, require_active=True, require_verified=True)

# Permission checkers
require_events_create = PermissionChecker("events:create")
require_events_update = PermissionChecker("events:update")
require_events_delete = PermissionChecker("events:delete")
require_users_list = PermissionChecker("users:list")
require_admin_access = PermissionChecker("admin:access")

# Rate limit dependencies
auth_rate_limit = RateLimitDependency(requests=5, window=300)  # 5 requests per 5 minutes
api_rate_limit = RateLimitDependency(requests=100, window=3600)  # 100 requests per hour


def cached_dependency(ttl: int = 300, key_prefix: str = "dep:"):
    """
    Decorator to cache dependency results

    Args:
        ttl: Time to live in seconds
        key_prefix: Cache key prefix
    """
    def decorator(dependency_func):
        @wraps(dependency_func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            import hashlib
            key_data = f"{dependency_func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            cache_key = key_prefix + hashlib.sha256(key_data.encode()).hexdigest()

            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute dependency and cache result
            result = await dependency_func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


async def get_request_context(request: Request) -> Dict[str, Any]:
    """
    Get comprehensive request context for logging and monitoring
    """
    return {
        "request_id": getattr(request.state, 'request_id', None),
        "user_id": getattr(request.state, 'user_id', None),
        "user_email": getattr(request.state, 'user_email', None),
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", ""),
        "method": request.method,
        "url": str(request.url),
        "path": request.url.path,
    }


# Database transaction dependency
class DatabaseTransaction:
    """
    Database transaction context manager dependency
    """

    def __init__(self, read_only: bool = False):
        self.read_only = read_only

    async def __call__(self, db: AsyncSession = Depends(get_db)) -> AsyncSession:
        """Get database session with transaction management"""
        if self.read_only:
            # For read-only operations, we can use regular session
            return db

        # For write operations, ensure proper transaction handling
        return db


# Transaction dependencies
get_db_transaction = DatabaseTransaction(read_only=False)
get_db_readonly = DatabaseTransaction(read_only=True)
