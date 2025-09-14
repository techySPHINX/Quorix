from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate

from ..core.security import get_password_hash, verify_password


async def get(db: AsyncSession, id: Any) -> Optional[User]:
    result = await db.execute(select(User).filter(User.id == id))
    first: Optional[User] = result.scalars().first()
    return first


async def get_user(db: AsyncSession, *, user_id: int) -> Optional[User]:
    """Get user by ID - alias for get function"""
    return await get(db, user_id)


async def get_users_by_ids(db: AsyncSession, *, user_ids: List[int]) -> List[User]:
    """Get multiple users by their IDs"""
    result = await db.execute(select(User).filter(User.id.in_(user_ids)))
    return list(result.scalars().all())


async def get_by_email(db: AsyncSession, *, email: str) -> Optional[User]:
    result = await db.execute(select(User).filter(User.email == email))
    first: Optional[User] = result.scalars().first()
    return first


async def create(db: AsyncSession, *, obj_in: UserCreate) -> User:
    db_obj = User(
        email=obj_in.email,
        hashed_password=get_password_hash(obj_in.password),
        full_name=obj_in.full_name,
        role=obj_in.role or UserRole.USER,
        is_superuser=obj_in.is_superuser or (obj_in.role == UserRole.SUPER_ADMIN),
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def update(db: AsyncSession, *, db_obj: User, obj_in: UserUpdate) -> User:
    update_data = obj_in.model_dump(exclude_unset=True)

    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = get_password_hash(update_data["password"])
        del update_data["password"]

    # Update is_superuser based on role
    if "role" in update_data:
        update_data["is_superuser"] = update_data["role"] == UserRole.SUPER_ADMIN

    update_data["updated_at"] = datetime.utcnow()

    for field, value in update_data.items():
        if hasattr(db_obj, field):
            setattr(db_obj, field, value)

    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    role_filter: Optional[UserRole] = None,
) -> list[User]:
    query = select(User).offset(skip).limit(limit)

    if role_filter:
        query = query.filter(User.role == role_filter)

    result = await db.execute(query)
    return list(result.scalars().all())


async def authenticate(
    db: AsyncSession, *, email: str, password: str
) -> Optional[User]:
    user = await get_by_email(db, email=email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None

    # Update last login
    await db.execute(
        sa_update(User).where(User.id == user.id).values(last_login=datetime.utcnow())
    )
    await db.commit()

    return user


def is_active(user: User) -> bool:
    return bool(user.is_active)


def is_superuser(user: User) -> bool:
    return bool(user.is_superuser)


def is_admin(user: User) -> bool:
    """Check if user has admin privileges (admin or super_admin role)"""
    return user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]


def has_role(user: User, required_role: UserRole) -> bool:
    """Check if user has the required role or higher privileges"""
    role_hierarchy = {UserRole.USER: 1, UserRole.ADMIN: 2, UserRole.SUPER_ADMIN: 3}

    user_level = role_hierarchy.get(user.role, 0)
    required_level = role_hierarchy.get(required_role, 0)

    return user_level >= required_level
