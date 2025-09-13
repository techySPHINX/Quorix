from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.event import Event
from app.schemas.booking import BookingCreate

from . import waitlist as crud_waitlist


async def get_booking(db: AsyncSession, booking_id: int):
    result = await db.execute(select(Booking).filter(Booking.id == booking_id))
    return result.scalars().first()


async def get_bookings(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(Booking).offset(skip).limit(limit))
    return result.scalars().all()


async def create_booking(db: AsyncSession, booking: BookingCreate, user_id: int):
    async with db.begin_nested():
        try:
            # Use select with for_update to lock the row
            event_result = await db.execute(
                select(Event).filter(Event.id == booking.event_id).with_for_update()
            )
            db_event = event_result.scalars().first()

            if not db_event:
                await db.rollback()
                return None

            if db_event.available_tickets >= booking.number_of_tickets:
                db_event.available_tickets -= booking.number_of_tickets
                db_booking = Booking(
                    **booking.model_dump(),
                    user_id=user_id,
                    booked_at=datetime.utcnow(),
                    status="confirmed",
                )
                db.add(db_booking)
                await db.commit()
                await db.refresh(db_booking)
                return db_booking
            else:
                await db.rollback()
                return None
        except Exception as e:
            await db.rollback()
            raise e


async def cancel_booking(db: AsyncSession, booking_id: int):
    async with db.begin():
        try:
            # Lock the booking record first
            booking_result = await db.execute(
                select(Booking).filter(Booking.id == booking_id).with_for_update()
            )
            db_booking = booking_result.scalars().first()

            if not db_booking or db_booking.status != "confirmed":
                return None

            # Lock the event record to update available tickets
            event_result = await db.execute(
                select(Event).filter(Event.id == db_booking.event_id).with_for_update()
            )
            db_event = event_result.scalars().first()

            if db_event:
                db_event.available_tickets += db_booking.number_of_tickets
                db_booking.status = "cancelled"

                # Notify waitlist users about available tickets
                await crud_waitlist.notify_waitlist_users(
                    db, db_booking.event_id, db_booking.number_of_tickets
                )

                await db.commit()
                await db.refresh(db_booking)
                return db_booking
            else:
                await db.rollback()
                return None
        except Exception as e:
            await db.rollback()
            raise e


async def get_user_bookings(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
):
    """Get bookings for a specific user"""
    result = await db.execute(
        select(Booking)
        .filter(Booking.user_id == user_id)
        .order_by(Booking.booked_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_event_bookings(
    db: AsyncSession, event_id: int, skip: int = 0, limit: int = 100
):
    """Get bookings for a specific event"""
    result = await db.execute(
        select(Booking)
        .filter(Booking.event_id == event_id)
        .order_by(Booking.booked_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
