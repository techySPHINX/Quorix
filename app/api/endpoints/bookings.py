from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .... import crud
from .... import models
from .... import schemas
from ....api import deps

router = APIRouter()

@router.post("/", response_model=schemas.Booking)
def create_booking(
    *, 
    db: Session = Depends(deps.get_db),
    booking_in: schemas.BookingCreate,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    Create new booking.
    """
    booking = crud.booking.create_booking(db=db, booking=booking_in, user_id=current_user.id)
    if not booking:
        raise HTTPException(status_code=400, detail="Not enough tickets available")
    return booking

@router.get("/", response_model=List[schemas.Booking])
def read_bookings(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    Retrieve bookings.
    """
    if current_user.is_superuser:
        bookings = crud.booking.get_bookings(db, skip=skip, limit=limit)
    else:
        bookings = crud.booking.get_bookings_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return bookings

@router.get("/{booking_id}", response_model=schemas.Booking)
def read_booking(
    *, 
    db: Session = Depends(deps.get_db),
    booking_id: int,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    Get booking by ID.
    """
    booking = crud.booking.get_booking(db=db, booking_id=booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if not current_user.is_superuser and booking.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    return booking

@router.put("/{booking_id}/cancel", response_model=schemas.Booking)
def cancel_booking(
    *, 
    db: Session = Depends(deps.get_db),
    booking_id: int,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    Cancel a booking.
    """
    booking = crud.booking.get_booking(db=db, booking_id=booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if not current_user.is_superuser and booking.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    booking = crud.booking.cancel_booking(db=db, booking_id=booking_id)
    return booking
