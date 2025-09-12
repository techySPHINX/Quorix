from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .... import crud
from .... import models
from .... import schemas
from ....api import deps
# from ....celery_app import celery_app # Uncomment when celery is implemented

router = APIRouter()


@router.post("/", response_model=schemas.Booking)
async def create_booking(
    *,
    db: AsyncSession = Depends(deps.get_db),
    booking_in: schemas.BookingCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Create new booking.
    """
    booking = await crud.booking.create_booking(
        db=db, booking=booking_in, user_id=current_user.id
    )
    if not booking:
        raise HTTPException(status_code=400, detail="Not enough tickets available")
    # celery_app.send_task("app.tasks.send_booking_confirmation_email", args=[booking.id]) # Uncomment when celery is implemented
    return booking


@router.get("/", response_model=List[schemas.Booking])
async def read_bookings(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Retrieve bookings.
    """
    if current_user.is_superuser:
        bookings = await crud.booking.get_bookings(db, skip=skip, limit=limit)
    else:
        # Assuming a get_bookings_by_user function exists or will be created
        # For now, filtering after fetching all, which is not ideal for large datasets
        all_bookings = await crud.booking.get_bookings(db)
        bookings = [b for b in all_bookings if b.user_id == current_user.id][skip:skip+limit]
    return bookings


@router.get("/{booking_id}", response_model=schemas.Booking)
async def read_booking(
    *,
    db: AsyncSession = Depends(deps.get_db),
    booking_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Get booking by ID.
    """
    booking = await crud.booking.get_booking(db=db, booking_id=booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if not current_user.is_superuser and booking.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    return booking


@router.put("/{booking_id}/cancel", response_model=schemas.Booking)
async def cancel_booking(
    *,
    db: AsyncSession = Depends(deps.get_db),
    booking_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Cancel a booking.
    """
    booking = await crud.booking.get_booking(db=db, booking_id=booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if not current_user.is_superuser and booking.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    booking = await crud.booking.cancel_booking(db=db, booking_id=booking_id)
    # celery_app.send_task("app.tasks.send_booking_cancellation_email", args=[booking.id]) # Uncomment when celery is implemented
    return booking
