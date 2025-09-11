from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from .... import crud
from .... import schemas
from ....api import deps

router = APIRouter()

@router.get("/statistics", response_model=dict)
def get_booking_statistics(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    Get booking statistics.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    return crud.analytics.get_booking_statistics(db)

@router.get("/popular-events", response_model=List[schemas.Event])
def get_popular_events(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    Get popular events.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    return crud.analytics.get_popular_events(db)
