from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.api import deps
from app.models.user import User
from app.schemas.booking import Booking, BookingCreate

router = APIRouter()


@router.post("/", response_model=Booking)  # type: ignore[misc]
async def create_booking(
    *,
    db: AsyncSession = Depends(deps.get_db),
    booking_in: BookingCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Booking:
    """
    Create new booking. If event is sold out, suggests joining waitlist.
    """
    # First check if event has enough tickets
    event = await crud.event.get_event(db, booking_in.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    booking, message = await crud.booking.create_booking_atomic(
        db=db, booking_data=booking_in, user_id=current_user.id
    )
    if not booking:
        # Event is sold out, suggest waitlist
        raise HTTPException(
            status_code=400,
            detail={
                "message": message or "Not enough tickets available",
                "available_tickets": event.available_tickets,
                "requested_tickets": booking_in.number_of_tickets,
                "suggestion": (
                    f"Consider joining the waitlist at "
                    f"/api/v1/waitlist/{event.id}/join"
                ),
            },
        )
    # Send confirmation email
    from app.celery_app import celery_app

    celery_app.send_task(
        "app.tasks.send_booking_confirmation_email",
        args=[current_user.id, booking.id],
    )
    return booking


@router.get("/", response_model=List[Booking])  # type: ignore[misc]
async def read_bookings(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
) -> List[Booking]:
    """
    Retrieve bookings. Regular users see only their own bookings.
    """
    is_superuser = getattr(current_user, "is_superuser", False)
    # If is_superuser is a SQLAlchemy column, compare explicitly
    if is_superuser:
        bookings, _ = await crud.booking.get_bookings_with_pagination(
            db, skip=skip, limit=limit
        )
    else:
        bookings = await crud.booking.get_user_booking_history(
            db, current_user.id, limit=limit, skip=skip
        )
    # Convert model objects to schema objects if needed
    return [Booking.model_validate(b) for b in bookings]


@router.get("/{booking_id}", response_model=Booking)  # type: ignore[misc]
async def read_booking(
    *,
    db: AsyncSession = Depends(deps.get_db),
    booking_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Booking:
    """
    Get booking by ID.
    """
    booking = await crud.booking.get_booking(db=db, booking_id=booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    is_superuser = getattr(current_user, "is_superuser", False)
    superuser_check = bool(is_superuser)
    user_id_check = getattr(booking, "user_id", None) == getattr(
        current_user, "id", None
    )
    if not superuser_check and not user_id_check:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    return booking


@router.put("/{booking_id}/cancel", response_model=Booking)  # type: ignore[misc]
async def cancel_booking(
    *,
    db: AsyncSession = Depends(deps.get_db),
    booking_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Booking:
    """
    Cancel a booking.
    """
    booking = await crud.booking.get_booking(db=db, booking_id=booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    is_superuser = getattr(current_user, "is_superuser", False)
    superuser_check = bool(is_superuser)
    user_id_check = getattr(booking, "user_id", None) == getattr(
        current_user, "id", None
    )
    if not superuser_check and not user_id_check:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    booking, message = await crud.booking.cancel_booking_atomic(
        db=db, booking_id=booking_id, user_id=current_user.id
    )
    if not booking:
        raise HTTPException(
            status_code=400, detail=message or "Unable to cancel booking"
        )
    # Send cancellation email
    from app.celery_app import celery_app

    celery_app.send_task(
        "app.tasks.send_booking_cancellation_email",
        args=[current_user.id, booking.id],
    )
    return booking
