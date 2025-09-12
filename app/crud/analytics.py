from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from .. import models


async def get_booking_statistics(db: AsyncSession):
    total_bookings_result = await db.execute(select(func.count(models.Booking.id)))
    total_bookings = total_bookings_result.scalar_one()

    total_revenue_result = await db.execute(
        select(func.sum(models.Event.price * models.Booking.number_of_tickets)).join(
            models.Event
        )
    )
    total_revenue = total_revenue_result.scalar_one()
    return {"total_bookings": total_bookings, "total_revenue": total_revenue}


async def get_popular_events(db: AsyncSession):
    result = await db.execute(
        select(models.Event, func.count(models.Booking.id).label("booking_count"))
        .join(models.Booking)
        .group_by(models.Event)
        .order_by(func.count(models.Booking.id).desc())
    )
    return result.all()
