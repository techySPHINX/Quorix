from typing import Any, AsyncGenerator, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from jose.exceptions import JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.models.user import User, UserRole
from app.schemas.user import TokenPayload

from ..core import security
from ..core.config import settings
from ..database import SessionLocal
from ..redis import redis_client

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = await crud.user.get(db, id=token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not crud.user.is_superuser(current_user):
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user


def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Require admin or super_admin role"""
    if not crud.user.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user


def require_role(required_role: UserRole) -> Any:
    """Dependency factory for role-based access control"""

    def role_dependency(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if not crud.user.has_role(current_user, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role.value}' or higher required",
            )
        return current_user

    return role_dependency


def require_roles(required_roles: List[UserRole]) -> Any:
    """Dependency factory for multiple role access"""

    def roles_dependency(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.role not in required_roles:
            roles_str = ", ".join([role.value for role in required_roles])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {roles_str}",
            )
        return current_user

    return roles_dependency


async def get_redis_client() -> Any:
    return redis_client
