from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate

from ..core.security import get_password_hash, verify_password


async def get(db: AsyncSession, id: Any) -> Optional[User]:
    result = await db.execute(select(User).filter(User.id == id))
    return result.scalars().first()


async def get_by_email(db: AsyncSession, *, email: str) -> Optional[User]:
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()


async def create(db: AsyncSession, *, obj_in: UserCreate) -> User:
    db_obj = User(
        email=obj_in.email,
        hashed_password=get_password_hash(obj_in.password),
        is_superuser=obj_in.is_superuser,
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()


async def authenticate(
    db: AsyncSession, *, email: str, password: str
) -> Optional[User]:
    user = await get_by_email(db, email=email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def is_active(user: User) -> bool:
    return user.is_active


def is_superuser(user: User) -> bool:
    return user.is_superuser
