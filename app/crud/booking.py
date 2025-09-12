from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .. import models, schemas
from . import event as crud_event
from datetime import datetime


async def get_booking(db: AsyncSession, booking_id: int):
    result = await db.execute(select(models.Booking).filter(models.Booking.id == booking_id))
    return result.scalars().first()


async def get_bookings(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Booking).offset(skip).limit(limit))
    return result.scalars().all()


async def create_booking(db: AsyncSession, booking: schemas.BookingCreate, user_id: int):
    async with db.begin_nested():
        try:
            # Use select with for_update to lock the row
            event_result = await db.execute(
                select(models.Event)
                .filter(models.Event.id == booking.event_id)
                .with_for_update()
            )
            db_event = event_result.scalars().first()

            if not db_event:
                await db.rollback()
                return None

            if db_event.available_tickets >= booking.number_of_tickets:
                db_event.available_tickets -= booking.number_of_tickets
                db_booking = models.Booking(
                    **booking.model_dump(),  # Use model_dump for Pydantic v2
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
    db_booking = await get_booking(db, booking_id)
    if db_booking:
        db_event = await crud_event.get_event(db, db_booking.event_id)
        if db_event:
            db_event.available_tickets += db_booking.number_of_tickets
        db_booking.status = "cancelled"
        await db.commit()
        await db.refresh(db_booking)
    return db_booking
