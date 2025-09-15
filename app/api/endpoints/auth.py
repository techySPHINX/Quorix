from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.api import deps
from app.core import security
from app.core.config import settings
from app.models.user import User
from app.schemas.user import Token
from app.schemas.user import User as UserSchema
from app.schemas.user import UserCreate

router = APIRouter()


@router.post("/login/access-token", response_model=Token, summary="User Login")  # type: ignore[misc]
async def login_access_token(
    db: AsyncSession = Depends(deps.get_db),
    redis_client: Redis = Depends(deps.get_redis_client),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    **Authenticate User and Get Access Token**

    OAuth2 compatible token login endpoint that validates user credentials
    and returns JWT access and refresh tokens for API authentication.

    **Request Body:**
    - `username` (string): User's email address
    - `password` (string): User's password

    **Response:**
    - `access_token`: JWT token for API authentication (expires in 30 minutes)
    - `refresh_token`: Token for refreshing access tokens (expires in 7 days)
    - `token_type`: Always "bearer"

    **Example Request:**
    ```bash
    curl -X POST "/api/v1/auth/login/access-token" \\
         -H "Content-Type: application/x-www-form-urlencoded" \\
         -d "username=user@example.com&password=securepassword123"
    ```

    **Errors:**
    - `400`: Incorrect email/password or inactive user
    - `422`: Validation error (missing fields)
    """
    user = await crud.user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not crud.user.is_active(user):
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

    # Include role information in the token
    additional_claims = {
        "role": user.role.value,
        "is_admin": crud.user.is_admin(user),
        "is_superuser": user.is_superuser,
    }

    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires, additional_claims=additional_claims
    )
    refresh_token = security.create_refresh_token(
        user.id, expires_delta=refresh_token_expires
    )

    await redis_client.set(
        f"access_token:{user.id}",
        access_token,
        ex=access_token_expires,
    )
    await redis_client.set(
        f"refresh_token:{user.id}",
        refresh_token,
        ex=refresh_token_expires,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post(
    "/login/refresh-token", response_model=Token, summary="Refresh Access Token"
)  # type: ignore[misc]
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(deps.get_db),
    redis_client: Redis = Depends(deps.get_redis_client),
) -> Any:
    """
    **Refresh Expired Access Token**

    Exchange a valid refresh token for a new access token without
    requiring the user to log in again.

    **Request Body:**
    - `refresh_token` (string): Valid refresh token from login

    **Response:**
    - `access_token`: New JWT token for API authentication
    - `token_type`: Always "bearer"

    **Example Request:**
    ```bash
    curl -X POST "/api/v1/auth/login/refresh-token" \\
         -H "Content-Type: application/json" \\
         -d '{"refresh_token": "eyJ0eXAiOiJKV1QiLCJhb..."}'
    ```

    **Errors:**
    - `401`: Invalid, expired, or missing refresh token
    - `422`: Validation error
    """
    try:
        payload = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = await crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    stored_refresh_token = await redis_client.get(f"refresh_token:{user.id}")
    if not stored_refresh_token or stored_refresh_token != refresh_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Include role information in the refreshed token
    additional_claims = {
        "role": user.role.value,
        "is_admin": crud.user.is_admin(user),
        "is_superuser": user.is_superuser,
    }

    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires, additional_claims=additional_claims
    )

    await redis_client.set(
        f"access_token:{user.id}",
        access_token,
        ex=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post(
    "/login/test-token", response_model=UserSchema, summary="Test Token Validity"
)  # type: ignore[misc]
async def test_token(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    **Validate Access Token**

    Test endpoint to verify that an access token is valid and
    retrieve the authenticated user's information.

    **Headers Required:**
    - `Authorization: Bearer <access_token>`

    **Response:**
    Returns the complete user profile associated with the token.

    **Example Request:**
    ```bash
    curl -X POST "/api/v1/auth/login/test-token" \\
         -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhb..."
    ```

    **Errors:**
    - `401`: Invalid, expired, or missing access token
    - `404`: User not found (token valid but user deleted)
    """
    return current_user


@router.post("/logout", summary="User Logout")  # type: ignore[misc]
async def logout(
    current_user: User = Depends(deps.get_current_user),
    redis_client: Redis = Depends(deps.get_redis_client),
) -> Any:
    """
    **Logout User**

    Invalidate the user's access and refresh tokens, effectively
    logging them out of the system.

    **Headers Required:**
    - `Authorization: Bearer <access_token>`

    **Response:**
    - `message`: Confirmation of successful logout

    **Example Request:**
    ```bash
    curl -X POST "/api/v1/auth/logout" \\
         -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhb..."
    ```

    **Errors:**
    - `401`: Invalid or missing access token

    **Note:**
    After logout, both access and refresh tokens will be invalidated
    and the user must log in again to access protected endpoints.
    """
    await redis_client.delete(f"access_token:{current_user.id}")
    await redis_client.delete(f"refresh_token:{current_user.id}")
    return {"message": "Logout successful"}


@router.post("/register", response_model=UserSchema, summary="Register User")  # type: ignore[misc]
async def register_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    Register a new user.

    Creates a new user in the system. Password will be hashed before storage.

    **Request Body:**
    - `email` (string): User email
    - `password` (string): Plain-text password
    - `full_name` (string, optional)
    - `role` (string, optional)

    **Response:**
    Returns the created user (without password fields).

    **Errors:**
    - `400`: Email already registered
    - `422`: Validation errors
    """
    existing = await crud.user.get_by_email(db, email=user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = await crud.user.create(db, obj_in=user_in)
    return user
