from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .... import crud, models, schemas
from ....api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.User])
async def read_users(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Retrieve users.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    users = await crud.user.get_users(db, skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=schemas.User)
async def read_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Get user by ID.
    """
    user = await crud.user.get(db, id=user_id) # Changed to crud.user.get
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id or current_user.is_superuser:
        return user
    raise HTTPException(status_code=400, detail="Not enough permissions")
