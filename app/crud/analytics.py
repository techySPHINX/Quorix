from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.event import Event
from app.models.user import User
from app.models.waitlist import Waitlist, WaitlistStatus


async def get_booking_statistics(db: AsyncSession) -> Dict:
    """Get comprehensive booking statistics"""
    # Total bookings and revenue
    total_bookings_result = await db.execute(
        select(func.count(Booking.id)).filter(Booking.status == BookingStatus.CONFIRMED)
    )
    total_bookings = total_bookings_result.scalar_one()

    total_revenue_result = await db.execute(
        select(func.sum(Event.price * Booking.number_of_tickets))
        .join(Event)
        .filter(Booking.status == BookingStatus.CONFIRMED)
    )
    total_revenue = total_revenue_result.scalar_one() or 0

    # Cancellation rate
    total_bookings_all = await db.execute(select(func.count(Booking.id)))
    total_cancelled = await db.execute(
        select(func.count(Booking.id)).filter(Booking.status == BookingStatus.CANCELLED)
    )

    total_all = total_bookings_all.scalar_one()
    cancelled = total_cancelled.scalar_one()
    cancellation_rate = (cancelled / total_all * 100) if total_all > 0 else 0

    # Average tickets per booking
    avg_tickets_result = await db.execute(
        select(func.avg(Booking.number_of_tickets)).filter(
            Booking.status == BookingStatus.CONFIRMED
        )
    )
    avg_tickets = avg_tickets_result.scalar_one() or 0

    return {
        "total_bookings": total_bookings,
        "total_revenue": float(total_revenue),
        "cancellation_rate": round(cancellation_rate, 2),
        "average_tickets_per_booking": round(float(avg_tickets), 2),
    }


async def get_popular_events(db: AsyncSession, limit: int = 10) -> List:
    """Get most popular events by booking count"""
    result = await db.execute(
        select(
            Event,
            func.count(Booking.id).label("booking_count"),
            func.sum(Booking.number_of_tickets).label("total_tickets_sold"),
            func.avg(Event.price * Booking.number_of_tickets).label(
                "avg_revenue_per_booking"
            ),
        )
        .join(Booking)
        .filter(Booking.status == BookingStatus.CONFIRMED)
        .group_by(Event.id)
        .order_by(func.count(Booking.id).desc())
        .limit(limit)
    )
    return result.all()


async def get_daily_booking_stats(db: AsyncSession, days: int = 30) -> List[Dict]:
    """Get daily booking statistics for the last N days"""
    start_date = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(Booking.booked_at).label("date"),
            func.count(Booking.id).label("bookings"),
            func.sum(Booking.number_of_tickets).label("tickets_sold"),
            func.sum(Event.price * Booking.number_of_tickets).label("revenue"),
        )
        .join(Event)
        .filter(
            Booking.booked_at >= start_date, Booking.status == BookingStatus.CONFIRMED
        )
        .group_by(func.date(Booking.booked_at))
        .order_by(func.date(Booking.booked_at))
    )

    return [
        {
            "date": row.date,
            "bookings": row.bookings,
            "tickets_sold": row.tickets_sold,
            "revenue": float(row.revenue or 0),
        }
        for row in result.all()
    ]


async def get_capacity_utilization(db: AsyncSession) -> List[Dict]:
    """Get capacity utilization for events"""
    result = await db.execute(
        select(
            Event.id,
            Event.name,
            Event.capacity,
            Event.available_tickets,
            func.sum(Booking.number_of_tickets).label("tickets_sold"),
        )
        .outerjoin(
            Booking,
            and_(
                Booking.event_id == Event.id, Booking.status == BookingStatus.CONFIRMED
            ),
        )
        .group_by(Event.id, Event.name, Event.capacity, Event.available_tickets)
    )

    return [
        {
            "event_id": row.id,
            "event_name": row.name,
            "capacity": row.capacity,
            "tickets_sold": row.tickets_sold or 0,
            "available_tickets": row.available_tickets,
            "utilization_percentage": round(
                ((row.tickets_sold or 0) / row.capacity * 100), 2
            ),
        }
        for row in result.all()
    ]


async def get_revenue_by_event(db: AsyncSession, limit: int = 10) -> List[Dict]:
    """Get top revenue generating events"""
    result = await db.execute(
        select(
            Event.id,
            Event.name,
            Event.price,
            func.sum(Booking.number_of_tickets).label("tickets_sold"),
            (Event.price * func.sum(Booking.number_of_tickets)).label("total_revenue"),
        )
        .join(Booking)
        .filter(Booking.status == BookingStatus.CONFIRMED)
        .group_by(Event.id, Event.name, Event.price)
        .order_by((Event.price * func.sum(Booking.number_of_tickets)).desc())
        .limit(limit)
    )

    return [
        {
            "event_id": row.id,
            "event_name": row.name,
            "price": float(row.price),
            "tickets_sold": row.tickets_sold,
            "total_revenue": float(row.total_revenue),
        }
        for row in result.all()
    ]


async def get_user_engagement_stats(db: AsyncSession) -> Dict:
    """Get user engagement statistics"""
    # Total users
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar_one()

    # Active users (users with at least one booking)
    active_users_result = await db.execute(
        select(func.count(func.distinct(Booking.user_id))).filter(
            Booking.status == BookingStatus.CONFIRMED
        )
    )
    active_users = active_users_result.scalar_one()

    # Repeat customers (users with more than one booking)
    repeat_customers_result = await db.execute(
        select(func.count().label("user_count")).select_from(
            select(Booking.user_id)
            .filter(Booking.status == BookingStatus.CONFIRMED)
            .group_by(Booking.user_id)
            .having(func.count(Booking.id) > 1)
            .subquery()
        )
    )
    repeat_customers = repeat_customers_result.scalar_one()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "user_engagement_rate": (
            round((active_users / total_users * 100), 2) if total_users > 0 else 0
        ),
        "repeat_customers": repeat_customers,
        "repeat_customer_rate": (
            round((repeat_customers / active_users * 100), 2) if active_users > 0 else 0
        ),
    }


async def get_waitlist_analytics(db: AsyncSession) -> Dict:
    """Get waitlist analytics"""
    # Total waitlist entries
    total_waiting_result = await db.execute(
        select(func.count(Waitlist.id)).filter(
            Waitlist.status == WaitlistStatus.WAITING
        )
    )
    total_waiting = total_waiting_result.scalar_one()

    # Conversion rate (notified to converted)
    total_notified_result = await db.execute(
        select(func.count(Waitlist.id)).filter(
            Waitlist.status == WaitlistStatus.NOTIFIED
        )
    )
    total_converted_result = await db.execute(
        select(func.count(Waitlist.id)).filter(
            Waitlist.status == WaitlistStatus.CONVERTED
        )
    )

    total_notified = total_notified_result.scalar_one()
    total_converted = total_converted_result.scalar_one()

    conversion_rate = (
        (total_converted / (total_notified + total_converted) * 100)
        if (total_notified + total_converted) > 0
        else 0
    )

    return {
        "total_waiting": total_waiting,
        "total_notified": total_notified,
        "total_converted": total_converted,
        "conversion_rate": round(conversion_rate, 2),
    }
