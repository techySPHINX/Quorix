from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .... import crud, models, schemas
from ....api import deps

router = APIRouter()


@router.get("/statistics", response_model=dict)
async def get_booking_statistics(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Get booking statistics.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    return await crud.analytics.get_booking_statistics(db)


@router.get("/popular-events", response_model=List[schemas.Event])
async def get_popular_events(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Get popular events.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    return await crud.analytics.get_popular_events(db)
