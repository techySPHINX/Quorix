from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.api import deps
from app.models.user import User as UserModel
from app.schemas.user import User as UserSchema

router = APIRouter()


@router.get("/", response_model=List[UserSchema])
async def read_users(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    """
    Retrieve users.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    users = await crud.user.get_users(db, skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=UserSchema)
async def read_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_id: int,
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    """
    Get user by ID.
    """
    user = await crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id or current_user.is_superuser:
        return user
    raise HTTPException(status_code=400, detail="Not enough permissions")
