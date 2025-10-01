import statistics
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import and_, case, desc, distinct, extract, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db_utils import PaginatedResponse, PaginationParams
from app.models.booking import Booking, BookingStatus
from app.models.event import Event
from app.models.user import User
from app.models.waitlist import Waitlist, WaitlistStatus

# WARNING: ALL FUNCTIONS IN THIS MODULE ARE ADMIN-ONLY OPERATIONS
# These functions provide sensitive business analytics and should only be
# accessible to users with ADMIN or SUPER_ADMIN roles.
# Access control is enforced at the API layer via require_role(UserRole.ADMIN)


async def get_dashboard_metrics(db: AsyncSession) -> dict[str, Any]:
    """
    Get comprehensive dashboard metrics.

    WARNING: ADMIN-ONLY FUNCTION
    This function exposes sensitive business analytics data and should only
    be called by authenticated admin users. Access control is enforced at
    the API layer via require_role(UserRole.ADMIN).
    """

    # Current period (last 30 days)
    current_period = datetime.utcnow() - timedelta(days=30)
    previous_period = datetime.utcnow() - timedelta(days=60)

    total_events = await db.execute(
        select(func.count(Event.id)).filter(Event.is_active.is_(True))
    )

    active_bookings = await db.execute(
        select(func.count(Booking.id)).filter(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.booked_at >= current_period,
        )
    )

    total_revenue = await db.execute(
        select(func.coalesce(func.sum(Booking.total_price), 0)).filter(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.booked_at >= current_period,
        )
    )

    active_users = await db.execute(
        select(func.count(distinct(Booking.user_id))).filter(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.booked_at >= current_period,
        )
    )

    # Previous period comparison
    prev_bookings = await db.execute(
        select(func.count(Booking.id)).filter(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.booked_at >= previous_period,
            Booking.booked_at < current_period,
        )
    )

    prev_revenue = await db.execute(
        select(func.coalesce(func.sum(Booking.total_price), 0)).filter(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.booked_at >= previous_period,
            Booking.booked_at < current_period,
        )
    )

    current_bookings = active_bookings.scalar_one()
    previous_bookings = prev_bookings.scalar_one()
    current_rev = float(total_revenue.scalar_one())
    previous_rev = float(prev_revenue.scalar_one())

    # Calculate growth rates
    booking_growth = (
        (current_bookings - previous_bookings) / max(previous_bookings, 1)
    ) * 100
    revenue_growth = ((current_rev - previous_rev) / max(previous_rev, 1)) * 100

    return {
        "total_events": total_events.scalar_one(),
        "total_bookings_30d": current_bookings,
        "total_revenue_30d": current_rev,
        "active_users_30d": active_users.scalar_one(),
        "booking_growth_rate": round(booking_growth, 2),
        "revenue_growth_rate": round(revenue_growth, 2),
    }


async def get_booking_statistics(
    db: AsyncSession, period_days: int = 30
) -> dict[str, Any]:
    """
    Get comprehensive booking statistics with period comparison.

    WARNING: ADMIN-ONLY FUNCTION
    This function exposes sensitive booking and revenue analytics.
    Access control is enforced at the API layer via require_role(UserRole.ADMIN).
    """
    current_period = datetime.utcnow() - timedelta(days=period_days)
    previous_period = datetime.utcnow() - timedelta(days=period_days * 2)

    # Current period stats
    current_stats = await db.execute(
        select(
            func.count(Booking.id).label("total_bookings"),
            func.count(case((Booking.status == BookingStatus.CONFIRMED, 1))).label(
                "confirmed_bookings"
            ),
            func.count(case((Booking.status == BookingStatus.CANCELLED, 1))).label(
                "cancelled_bookings"
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Booking.status == BookingStatus.CONFIRMED,
                            Booking.total_price,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_revenue"),
            func.coalesce(
                func.avg(
                    case(
                        (
                            Booking.status == BookingStatus.CONFIRMED,
                            Booking.number_of_tickets,
                        )
                    )
                ),
                0,
            ).label("avg_tickets_per_booking"),
            func.count(distinct(Booking.user_id)).label("unique_customers"),
        ).filter(Booking.booked_at >= current_period)
    )

    current = current_stats.first()

    # Previous period for comparison
    previous_stats = await db.execute(
        select(
            func.count(Booking.id).label("total_bookings"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Booking.status == BookingStatus.CONFIRMED,
                            Booking.total_price,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_revenue"),
        ).filter(
            Booking.booked_at >= previous_period, Booking.booked_at < current_period
        )
    )

    previous = previous_stats.first()

    # Calculate rates and growth
    cancellation_rate = (
        (current.cancelled_bookings if current else 0)
        / max(current.total_bookings if current else 0, 1)
    ) * 100
    conversion_rate = (
        (current.confirmed_bookings if current else 0)
        / max(current.total_bookings if current else 0, 1)
    ) * 100

    booking_growth = (
        (
            (current.total_bookings if current else 0)
            - (previous.total_bookings if previous else 0)
        )
        / max(previous.total_bookings if previous else 0, 1)
        * 100
    )

    current_revenue = float(current.total_revenue if current else 0)
    previous_revenue = float(previous.total_revenue if previous else 0)
    revenue_growth = (
        (current_revenue - previous_revenue) / max(previous_revenue, 1)
    ) * 100

    # Top spending customers
    top_customers = await db.execute(
        select(
            User.email,
            User.full_name,
            func.sum(Booking.total_price).label("total_spent"),
            func.count(Booking.id).label("booking_count"),
        )
        .join(User)
        .filter(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.booked_at >= current_period,
        )
        .group_by(User.id, User.email, User.full_name)
        .order_by(desc(func.sum(Booking.total_price)))
        .limit(5)
    )

    return {
        "period_days": period_days,
        "total_bookings": current.total_bookings if current else 0,
        "confirmed_bookings": current.confirmed_bookings if current else 0,
        "cancelled_bookings": current.cancelled_bookings if current else 0,
        "total_revenue": float(current.total_revenue) if current else 0.0,
        "unique_customers": current.unique_customers if current else 0,
        "average_tickets_per_booking": (
            round(float(current.avg_tickets_per_booking), 2) if current else 0.0
        ),
        "cancellation_rate": round(cancellation_rate, 2),
        "conversion_rate": round(conversion_rate, 2),
        "booking_growth": round(booking_growth, 2),
        "revenue_growth": round(revenue_growth, 2),
        "top_customers": [
            {
                "email": row.email,
                "name": row.full_name,
                "total_spent": float(row.total_spent),
                "booking_count": row.booking_count,
            }
            for row in top_customers.all()
        ],
    }


async def get_popular_events(
    db: AsyncSession, limit: int = 10, period_days: Optional[int] = None
) -> list[Any]:
    """Get most popular events by various metrics"""
    query = select(
        Event,
        func.count(Booking.id).label("booking_count"),
        func.sum(Booking.number_of_tickets).label("total_tickets_sold"),
        func.coalesce(func.sum(Booking.total_price), 0).label("total_revenue"),
        func.coalesce(func.avg(Booking.total_price), 0).label(
            "avg_revenue_per_booking"
        ),
        (func.count(Booking.id) * 100.0 / func.count(distinct(Booking.user_id))).label(
            "conversion_rate"
        ),
    ).join(Booking, Event.id == Booking.event_id)

    if period_days:
        period_start = datetime.utcnow() - timedelta(days=period_days)
        query = query.filter(Booking.booked_at >= period_start)

    query = (
        query.filter(Booking.status == BookingStatus.CONFIRMED)
        .group_by(Event.id)
        .order_by(desc(func.count(Booking.id)))
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.all())


async def get_booking_trends(
    db: AsyncSession, period: str = "daily", days: int = 30
) -> dict[str, Any]:
    """Get booking trends with different time granularities"""
    start_date = datetime.utcnow() - timedelta(days=days)

    # Determine date grouping
    if period == "daily":
        date_group = func.date(Booking.booked_at)
    elif period == "weekly":
        date_group = func.date_trunc("week", Booking.booked_at)
    else:  # monthly
        date_group = func.date_trunc("month", Booking.booked_at)

    trends = await db.execute(
        select(
            date_group.label("period"),
            func.count(Booking.id).label("total_bookings"),
            func.count(case((Booking.status == BookingStatus.CONFIRMED, 1))).label(
                "confirmed_bookings"
            ),
            func.count(case((Booking.status == BookingStatus.CANCELLED, 1))).label(
                "cancelled_bookings"
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Booking.status == BookingStatus.CONFIRMED,
                            Booking.total_price,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("revenue"),
            func.sum(
                case(
                    (
                        Booking.status == BookingStatus.CONFIRMED,
                        Booking.number_of_tickets,
                    ),
                    else_=0,
                )
            ).label("tickets_sold"),
        )
        .filter(Booking.booked_at >= start_date)
        .group_by(date_group)
        .order_by(date_group)
    )

    trend_data = []
    for row in trends.all():
        conversion_rate = (row.confirmed_bookings / max(row.total_bookings, 1)) * 100
        trend_data.append(
            {
                "period": (
                    row.period.strftime("%Y-%m-%d")
                    if period == "daily"
                    else str(row.period)
                ),
                "total_bookings": row.total_bookings,
                "confirmed_bookings": row.confirmed_bookings,
                "cancelled_bookings": row.cancelled_bookings,
                "revenue": float(row.revenue),
                "tickets_sold": row.tickets_sold or 0,
                "conversion_rate": round(conversion_rate, 2),
            }
        )

    return {
        "period_type": period,
        "days_analyzed": days,
        "data_points": len(trend_data),
        "trends": trend_data,
    }


async def get_revenue_analysis(
    db: AsyncSession, period_days: int = 30
) -> dict[str, Any]:
    """Get comprehensive revenue analysis"""
    start_date = datetime.utcnow() - timedelta(days=period_days)

    # Revenue by event category/location
    revenue_by_location = await db.execute(
        select(
            Event.location,
            func.count(Booking.id).label("booking_count"),
            func.coalesce(func.sum(Booking.total_price), 0).label("total_revenue"),
            func.coalesce(func.avg(Booking.total_price), 0).label(
                "avg_revenue_per_booking"
            ),
        )
        .join(Event)
        .filter(
            Booking.status == BookingStatus.CONFIRMED, Booking.booked_at >= start_date
        )
        .group_by(Event.location)
        .order_by(desc(func.sum(Booking.total_price)))
    )

    # Revenue by price range
    revenue_by_price_range = await db.execute(
        select(
            case(
                (Event.price <= 50, "Budget ($0-50)"),
                (Event.price <= 100, "Mid-range ($51-100)"),
                (Event.price <= 200, "Premium ($101-200)"),
                else_="Luxury ($200+)",
            ).label("price_range"),
            func.count(Booking.id).label("booking_count"),
            func.coalesce(func.sum(Booking.total_price), 0).label("total_revenue"),
        )
        .join(Event)
        .filter(
            Booking.status == BookingStatus.CONFIRMED, Booking.booked_at >= start_date
        )
        .group_by("price_range")
        .order_by(desc(func.sum(Booking.total_price)))
    )

    return {
        "period_days": period_days,
        "revenue_by_location": [
            {
                "location": row.location or "Unknown",
                "booking_count": row.booking_count,
                "total_revenue": float(row.total_revenue),
                "avg_revenue_per_booking": float(row.avg_revenue_per_booking),
            }
            for row in revenue_by_location.all()
        ],
        "revenue_by_price_range": [
            {
                "price_range": row.price_range,
                "booking_count": row.booking_count,
                "total_revenue": float(row.total_revenue),
            }
            for row in revenue_by_price_range.all()
        ],
    }


async def get_capacity_utilization(
    db: AsyncSession,
    pagination: PaginationParams,
    min_utilization: Optional[float] = None,
) -> dict[str, Any]:
    """Get capacity utilization metrics with pagination"""

    query = (
        select(
            Event.id,
            Event.name,
            Event.location,
            Event.capacity,
            Event.start_date,
            func.coalesce(
                func.sum(
                    case(
                        (
                            Booking.status == BookingStatus.CONFIRMED,
                            Booking.number_of_tickets,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("tickets_sold"),
            (
                (
                    func.coalesce(
                        func.sum(
                            case(
                                (
                                    Booking.status == BookingStatus.CONFIRMED,
                                    Booking.number_of_tickets,
                                ),
                                else_=0,
                            )
                        ),
                        0,
                    )
                    * 100.0
                )
                / Event.capacity
            ).label("utilization_rate"),
        )
        .outerjoin(Booking)
        .filter(Event.is_active.is_(True))
        .group_by(
            Event.id, Event.name, Event.location, Event.capacity, Event.start_date
        )
    )

    if min_utilization is not None:
        query = query.having(
            (
                (
                    func.coalesce(
                        func.sum(
                            case(
                                (
                                    Booking.status == BookingStatus.CONFIRMED,
                                    Booking.number_of_tickets,
                                ),
                                else_=0,
                            )
                        ),
                        0,
                    )
                    * 100.0
                )
                / Event.capacity
            )
            >= min_utilization
        )

    # Get total count for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.execute(count_query)
    total = total_count.scalar_one()

    # Apply pagination
    query = (
        query.order_by(desc("utilization_rate"))
        .offset(pagination.offset)
        .limit(pagination.limit)
    )

    result = await db.execute(query)

    items = [
        {
            "event_id": row.id,
            "event_name": row.name,
            "location": row.location,
            "capacity": row.capacity,
            "start_date": row.start_date,
            "tickets_sold": row.tickets_sold,
            "utilization_rate": round(float(row.utilization_rate), 2),
            "available_tickets": row.capacity - row.tickets_sold,
        }
        for row in result.all()
    ]

    # model_dump() returns a dict representation suitable for response
    data: dict[str, Any] = PaginatedResponse.create(
        items, total, pagination
    ).model_dump()
    return data


async def get_user_behavior_analysis(
    db: AsyncSession, period_days: int = 30
) -> dict[str, Any]:
    """Get comprehensive user behavior analysis"""
    start_date = datetime.utcnow() - timedelta(days=period_days)

    # User segments by booking frequency
    user_segments = await db.execute(
        select(
            case(
                (func.count(Booking.id) == 1, "One-time"),
                (func.count(Booking.id) <= 3, "Casual"),
                (func.count(Booking.id) <= 10, "Regular"),
                else_="VIP",
            ).label("segment"),
            func.count(distinct(Booking.user_id)).label("user_count"),
            func.coalesce(func.avg(Booking.total_price), 0).label("avg_spend"),
            func.coalesce(func.sum(Booking.total_price), 0).label("total_revenue"),
        )
        .filter(
            Booking.status == BookingStatus.CONFIRMED, Booking.booked_at >= start_date
        )
        .group_by(
            case(
                (func.count(Booking.id) == 1, "One-time"),
                (func.count(Booking.id) <= 3, "Casual"),
                (func.count(Booking.id) <= 10, "Regular"),
                else_="VIP",
            )
        )
    )

    # Booking patterns by time
    booking_by_hour = await db.execute(
        select(
            extract("hour", Booking.booked_at).label("hour"),
            func.count(Booking.id).label("booking_count"),
        )
        .filter(
            Booking.status == BookingStatus.CONFIRMED, Booking.booked_at >= start_date
        )
        .group_by(extract("hour", Booking.booked_at))
        .order_by("hour")
    )

    return {
        "period_days": period_days,
        "user_segments": [
            {
                "segment": row.segment,
                "user_count": row.user_count,
                "avg_spend": float(row.avg_spend),
                "total_revenue": float(row.total_revenue),
            }
            for row in user_segments.all()
        ],
        "booking_patterns_by_hour": [
            {"hour": int(row.hour), "booking_count": row.booking_count}
            for row in booking_by_hour.all()
        ],
    }


async def get_waitlist_analytics(
    db: AsyncSession, period_days: int = 30
) -> dict[str, Any]:
    """Get comprehensive waitlist analytics"""
    start_date = datetime.utcnow() - timedelta(days=period_days)

    # Overall waitlist stats
    overall_stats = await db.execute(
        select(
            func.count(Waitlist.id).label("total_waitlist_entries"),
            func.count(case((Waitlist.status == WaitlistStatus.CONVERTED, 1))).label(
                "converted"
            ),
            func.count(case((Waitlist.status == WaitlistStatus.NOTIFIED, 1))).label(
                "notified"
            ),
            func.count(case((Waitlist.status == WaitlistStatus.EXPIRED, 1))).label(
                "expired"
            ),
        ).filter(Waitlist.joined_at >= start_date)
    )

    stats = overall_stats.first()
    conversion_rate = (
        (stats.converted / max(stats.total_waitlist_entries, 1)) * 100 if stats else 0
    )

    # Waitlist performance by event
    event_waitlist_performance = await db.execute(
        select(
            Event.name,
            Event.capacity,
            func.count(Waitlist.id).label("waitlist_size"),
            func.count(case((Waitlist.status == WaitlistStatus.CONVERTED, 1))).label(
                "conversions"
            ),
            (
                func.count(case((Waitlist.status == WaitlistStatus.CONVERTED, 1)))
                * 100.0
                / func.count(Waitlist.id)
            ).label("conversion_rate"),
        )
        .join(Event)
        .filter(Waitlist.joined_at >= start_date)
        .group_by(Event.id, Event.name, Event.capacity)
        .having(func.count(Waitlist.id) > 0)
        .order_by(desc("conversion_rate"))
        .limit(10)
    )

    return {
        "period_days": period_days,
        "total_waitlist_entries": stats.total_waitlist_entries if stats else 0,
        "converted": stats.converted if stats else 0,
        "notified": stats.notified if stats else 0,
        "expired": stats.expired if stats else 0,
        "overall_conversion_rate": round(conversion_rate, 2),
        "event_performance": [
            {
                "event_name": row.name,
                "capacity": row.capacity,
                "waitlist_size": row.waitlist_size,
                "conversions": row.conversions,
                "conversion_rate": round(float(row.conversion_rate), 2),
            }
            for row in event_waitlist_performance.all()
        ],
    }


async def get_event_performance(db: AsyncSession, event_id: int) -> dict[str, Any]:
    """Get detailed performance metrics for a specific event"""

    # Basic event info
    event_info = await db.execute(select(Event).filter(Event.id == event_id))
    event = event_info.scalar_one_or_none()

    if not event:
        raise ValueError("Event not found")

    # Booking performance
    booking_stats = await db.execute(
        select(
            func.count(Booking.id).label("total_bookings"),
            func.count(case((Booking.status == BookingStatus.CONFIRMED, 1))).label(
                "confirmed"
            ),
            func.count(case((Booking.status == BookingStatus.CANCELLED, 1))).label(
                "cancelled"
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Booking.status == BookingStatus.CONFIRMED,
                            Booking.total_price,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_revenue"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Booking.status == BookingStatus.CONFIRMED,
                            Booking.number_of_tickets,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("tickets_sold"),
        ).filter(Booking.event_id == event_id)
    )

    stats = booking_stats.first()

    # Waitlist stats
    waitlist_stats = await db.execute(
        select(
            func.count(Waitlist.id).label("waitlist_size"),
            func.count(case((Waitlist.status == WaitlistStatus.CONVERTED, 1))).label(
                "conversions"
            ),
        ).filter(Waitlist.event_id == event_id)
    )

    waitlist = waitlist_stats.first()

    event_capacity = getattr(event, "capacity", 0)
    utilization_rate = (
        (stats.tickets_sold / event_capacity) * 100
        if event_capacity > 0 and stats
        else 0
    )
    conversion_rate = (
        (stats.confirmed / max(stats.total_bookings, 1)) * 100 if stats else 0
    )

    return {
        "event": {
            "id": event.id,
            "name": event.name,
            "location": event.location,
            "capacity": event.capacity,
            "price": float(getattr(event, "price", 0)),
            "start_date": event.start_date,
        },
        "performance": {
            "total_bookings": stats.total_bookings if stats else 0,
            "confirmed_bookings": stats.confirmed if stats else 0,
            "cancelled_bookings": stats.cancelled if stats else 0,
            "tickets_sold": stats.tickets_sold if stats else 0,
            "available_tickets": event.capacity - (stats.tickets_sold if stats else 0),
            "utilization_rate": round(utilization_rate, 2),
            "conversion_rate": round(conversion_rate, 2),
            "total_revenue": float(stats.total_revenue) if stats else 0.0,
            "avg_revenue_per_ticket": (
                float(stats.total_revenue / max(stats.tickets_sold, 1))
                if stats
                else 0.0
            ),
        },
        "waitlist": {
            "size": waitlist.waitlist_size if waitlist else 0,
            "conversions": waitlist.conversions if waitlist else 0,
            "conversion_rate": (
                round((waitlist.conversions / max(waitlist.waitlist_size, 1)) * 100, 2)
                if waitlist
                else 0.0
            ),
        },
    }


async def get_geographical_analysis(
    db: AsyncSession, period_days: int = 30
) -> dict[str, Any]:
    """Get geographical distribution analysis"""
    start_date = datetime.utcnow() - timedelta(days=period_days)

    location_stats = await db.execute(
        select(
            Event.location,
            func.count(distinct(Event.id)).label("event_count"),
            func.count(Booking.id).label("total_bookings"),
            func.coalesce(func.sum(Booking.total_price), 0).label("total_revenue"),
            func.coalesce(func.avg(Event.capacity), 0).label("avg_capacity"),
            func.coalesce(
                func.avg(
                    (func.sum(Booking.number_of_tickets) * 100.0) / Event.capacity
                ),
                0,
            ).label("avg_utilization"),
        )
        .outerjoin(
            Booking,
            and_(
                Event.id == Booking.event_id,
                Booking.status == BookingStatus.CONFIRMED,
                Booking.booked_at >= start_date,
            ),
        )
        .filter(Event.is_active.is_(True))
        .group_by(Event.location)
        .having(Event.location.isnot(None))
        .order_by(desc(func.count(distinct(Event.id))))
    )

    return {
        "period_days": period_days,
        "locations": [
            {
                "location": row.location,
                "event_count": row.event_count,
                "total_bookings": row.total_bookings or 0,
                "total_revenue": float(row.total_revenue),
                "avg_capacity": round(float(row.avg_capacity), 0),
                "avg_utilization": round(float(row.avg_utilization), 2),
            }
            for row in location_stats.all()
        ],
    }


async def get_demand_forecasting(
    db: AsyncSession, forecast_days: int = 30
) -> dict[str, Any]:
    """Basic demand forecasting based on historical trends"""

    # Get historical data for the last 90 days
    historical_period = datetime.utcnow() - timedelta(days=90)

    daily_bookings = await db.execute(
        select(
            func.date(Booking.booked_at).label("date"),
            func.count(Booking.id).label("bookings"),
            func.coalesce(func.sum(Booking.total_price), 0).label("revenue"),
        )
        .filter(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.booked_at >= historical_period,
        )
        .group_by(func.date(Booking.booked_at))
        .order_by(func.date(Booking.booked_at))
    )

    historical_data = [
        {"date": row.date, "bookings": row.bookings, "revenue": float(row.revenue)}
        for row in daily_bookings.all()
    ]

    if len(historical_data) < 7:
        return {"error": "Insufficient historical data for forecasting"}

    # Simple moving average forecast (7-day window)
    recent_bookings = [day["bookings"] for day in historical_data[-7:]]
    recent_revenue = [day["revenue"] for day in historical_data[-7:]]

    avg_daily_bookings = statistics.mean(recent_bookings)
    avg_daily_revenue = statistics.mean(recent_revenue)

    # Calculate trend
    if len(historical_data) >= 14:
        first_week = [day["bookings"] for day in historical_data[-14:-7]]
        second_week = recent_bookings
        trend = (
            statistics.mean(second_week) - statistics.mean(first_week)
        ) / statistics.mean(first_week)
    else:
        trend = 0

    # Generate forecast
    forecast_data = []
    for i in range(forecast_days):
        forecast_date = datetime.utcnow().date() + timedelta(days=i + 1)
        trend_factor = 1 + (trend * (i / 7))  # Apply trend weekly

        forecast_data.append(
            {
                "date": forecast_date,
                "predicted_bookings": round(avg_daily_bookings * trend_factor),
                "predicted_revenue": round(avg_daily_revenue * trend_factor, 2),
                "confidence": max(
                    0.5, 1 - (i / forecast_days * 0.5)
                ),  # Decreasing confidence
            }
        )

    return {
        "historical_days": len(historical_data),
        "forecast_days": forecast_days,
        "trend_factor": round(trend, 3),
        "avg_daily_bookings": round(avg_daily_bookings, 1),
        "avg_daily_revenue": round(avg_daily_revenue, 2),
        "historical_data": historical_data[-30:],  # Last 30 days
        "forecast": forecast_data,
    }


async def get_real_time_metrics(db: AsyncSession) -> dict[str, Any]:
    """Get real-time metrics for dashboard monitoring"""
    now = datetime.utcnow()
    today = now.date()

    # Today's metrics
    today_metrics = await db.execute(
        select(
            func.count(Booking.id).label("bookings_today"),
            func.count(case((Booking.status == BookingStatus.CONFIRMED, 1))).label(
                "confirmed_today"
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Booking.status == BookingStatus.CONFIRMED,
                            Booking.total_price,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("revenue_today"),
            func.count(distinct(Booking.user_id)).label("active_users_today"),
        ).filter(func.date(Booking.booked_at) == today)
    )

    today_stats = today_metrics.first()

    # Current hour metrics
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    hour_metrics = await db.execute(
        select(
            func.count(Booking.id).label("bookings_this_hour"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Booking.status == BookingStatus.CONFIRMED,
                            Booking.total_price,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("revenue_this_hour"),
        ).filter(Booking.booked_at >= current_hour)
    )

    hour_stats = hour_metrics.first()

    # Upcoming events (next 24 hours)
    upcoming_events = await db.execute(
        select(func.count(Event.id)).filter(
            Event.start_date >= now,
            Event.start_date <= now + timedelta(hours=24),
            Event.is_active.is_(True),
        )
    )

    # Active waitlists
    active_waitlists = await db.execute(
        select(func.count(Waitlist.id)).filter(
            Waitlist.status == WaitlistStatus.WAITING
        )
    )

    return {
        "timestamp": now,
        "today": {
            "total_bookings": today_stats.bookings_today if today_stats else 0,
            "confirmed_bookings": today_stats.confirmed_today if today_stats else 0,
            "revenue": float(today_stats.revenue_today) if today_stats else 0.0,
            "active_users": today_stats.active_users_today if today_stats else 0,
        },
        "current_hour": {
            "bookings": hour_stats.bookings_this_hour if hour_stats else 0,
            "revenue": float(hour_stats.revenue_this_hour) if hour_stats else 0.0,
        },
        "upcoming_events_24h": upcoming_events.scalar_one(),
        "active_waitlists": active_waitlists.scalar_one(),
    }


async def get_cohort_analysis(db: AsyncSession, months: int = 6) -> dict[str, Any]:
    """Get user cohort analysis showing retention patterns"""
    start_date = datetime.utcnow() - timedelta(days=months * 30)

    # Get user cohorts by first booking month
    cohorts = await db.execute(
        text(
            """
        WITH user_cohorts AS (
            SELECT
                user_id,
                DATE_TRUNC('month', MIN(booked_at)) as cohort_month,
                MIN(booked_at) as first_booking
            FROM bookings
            WHERE booked_at >= :start_date AND status = 'confirmed'
            GROUP BY user_id
        ),
        cohort_data AS (
            SELECT
                uc.cohort_month,
                DATE_TRUNC('month', b.booked_at) as booking_month,
                COUNT(DISTINCT uc.user_id) as users
            FROM user_cohorts uc
            JOIN bookings b ON uc.user_id = b.user_id
            WHERE b.status = 'confirmed' AND b.booked_at >= :start_date
            GROUP BY uc.cohort_month, DATE_TRUNC('month', b.booked_at)
        )
        SELECT
            cohort_month,
            booking_month,
            users,
            EXTRACT(MONTH FROM AGE(booking_month, cohort_month)) as months_diff
        FROM cohort_data
        ORDER BY cohort_month, booking_month
        """
        ),
        {"start_date": start_date},
    )

    cohort_data: dict[str, dict[str, Any]] = {}
    for row in cohorts:
        cohort_key = row.cohort_month.strftime("%Y-%m")
        if cohort_key not in cohort_data:
            cohort_data[cohort_key] = {}

        month_key = f"month_{int(row.months_diff)}"
        cohort_data[cohort_key][month_key] = row.users

    return {"analysis_months": months, "cohorts": cohort_data}


async def get_capacity_utilization_simple(db: AsyncSession) -> list[dict[str, Any]]:
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


async def get_revenue_by_event(
    db: AsyncSession, limit: int = 10
) -> list[dict[str, Any]]:
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


async def get_user_engagement_stats(db: AsyncSession) -> dict[str, Any]:
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


async def get_waitlist_analytics_simple(db: AsyncSession) -> dict[str, Any]:
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
