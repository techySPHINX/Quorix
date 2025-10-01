import logging
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from redis.asyncio import Redis
from sqlalchemy import and_, case, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import coalesce

from app.core.db_utils import db_transaction
from app.models.booking import Booking, BookingStatus
from app.models.event import Event
from app.models.waitlist import Waitlist, WaitlistStatus
from app.schemas.booking import BookingCreate

logger = logging.getLogger(__name__)


class BookingConcurrencyManager:
    """Manages booking concurrency using distributed locking and atomic operations"""

    def __init__(self, redis_client: Redis):
        self.redis: Redis = redis_client
        self.lock_timeout = 30  # seconds

    async def acquire_booking_lock(self, event_id: int, user_id: int) -> Optional[str]:
        lock_key = f"booking_lock:event:{event_id}:user:{user_id}"
        lock_value = str(uuid.uuid4())
        acquired = await self.redis.set(
            lock_key, lock_value, ex=self.lock_timeout, nx=True
        )
        return lock_value if acquired else None

    async def release_booking_lock(
        self, event_id: int, user_id: int, lock_value: str
    ) -> bool:
        lock_key = f"booking_lock:event:{event_id}:user:{user_id}"
        lua_script = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("DEL", KEYS[1])
        else
            return 0
        end
        """
        result: Any = await self.redis.eval(lua_script, 1, lock_key, lock_value)
        return bool(result)

    async def update_event_booking_stats(
        self, event_id: int, delta: int, status: str = "active"
    ) -> None:
        key = f"event_stats:{event_id}"
        field = f"{status}_bookings"
        pipe = self.redis.pipeline()
        pipe.hincrby(key, field, delta)
        pipe.hset(key, "last_updated", datetime.utcnow().isoformat())
        pipe.expire(key, 3600 * 24)
        await pipe.execute()


# Global instance
concurrency_manager: Optional[BookingConcurrencyManager] = None


def init_concurrency_manager(redis_client: Redis) -> None:
    global concurrency_manager
    concurrency_manager = BookingConcurrencyManager(redis_client)


async def get_booking(db: AsyncSession, booking_id: int) -> Optional[Booking]:
    result = await db.execute(select(Booking).filter(Booking.id == booking_id))
    booking = result.scalars().first()
    return booking if isinstance(booking, Booking) or booking is None else None


async def get_bookings_with_pagination(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[BookingStatus] = None,
    user_id_filter: Optional[int] = None,
    event_id_filter: Optional[int] = None,
) -> Tuple[List[Booking], int]:
    query = select(Booking)
    count_query = select(func.count(Booking.id))
    filters = []
    if status_filter:
        filters.append(Booking.status == status_filter)
    if user_id_filter:
        filters.append(Booking.user_id == user_id_filter)
    if event_id_filter:
        filters.append(Booking.event_id == event_id_filter)
    if filters:
        query = query.filter(and_(*filters))
        count_query = count_query.filter(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    query = query.order_by(Booking.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    # scalars().all() returns a Sequence; convert to list to match the declared return type
    bookings = list(result.scalars().all())
    return bookings, total


async def create_booking_atomic(
    db: AsyncSession,
    booking_data: BookingCreate,
    user_id: int,
    redis_client: Optional[Redis] = None,
) -> Tuple[Optional[Booking], str]:
    if not concurrency_manager and redis_client:
        init_concurrency_manager(redis_client)
    event_id = booking_data.event_id
    requested_tickets = booking_data.number_of_tickets
    lock_value: Optional[str] = None
    if concurrency_manager:
        lock_value = await concurrency_manager.acquire_booking_lock(event_id, user_id)
        if not lock_value:
            return None, "Booking process is busy, please try again"

    try:
        async with db_transaction(db):
            event_result = await db.execute(
                select(Event)
                .filter(Event.id == event_id, Event.is_active.is_(True))
                .with_for_update()
            )
            event = event_result.scalars().first()
            if not event:
                return None, "Event not found or not active"
            if getattr(event, "available_tickets", 0) < requested_tickets:
                return None, f"Only {event.available_tickets} tickets available"
            if getattr(event, "start_date", datetime.min) <= datetime.utcnow():
                return None, "Cannot book tickets for past or ongoing events"

            existing_booking_result = await db.execute(
                select(Booking).filter(
                    Booking.user_id == user_id,
                    Booking.event_id == event_id,
                    Booking.status.in_(
                        [BookingStatus.CONFIRMED, BookingStatus.PENDING]
                    ),
                )
            )
            if existing_booking_result.scalars().first():
                return None, "User already has an active booking for this event"

            total_price = Decimal(str(getattr(event, "price", 0))) * requested_tickets
            booking = Booking(
                user_id=user_id,
                event_id=event_id,
                number_of_tickets=requested_tickets,
                total_price=total_price,
                status=BookingStatus.CONFIRMED,
                booked_at=datetime.utcnow(),
            )
            db.add(booking)

            await db.execute(
                update(Event)
                .where(Event.id == event_id)
                .values(
                    available_tickets=getattr(event, "available_tickets", 0)
                    - requested_tickets,
                    updated_at=datetime.utcnow(),
                )
            )

            await db.flush()
            await db.refresh(booking)

            if concurrency_manager:
                await concurrency_manager.update_event_booking_stats(
                    int(getattr(event, "id", event_id)), 1, "active"
                )

            # Send notification
            try:
                from app.core.notifications import notification_service
                from app.crud.user import get_user
                from app.models.notification import (
                    NotificationPriority,
                    NotificationType,
                )

                user = await get_user(db, user_id=user_id)
                booking_payload = {
                    "booking_id": booking.id,
                    "event_id": event_id,
                    "event_name": event.name,
                    "event_date": str(event.start_date),
                    "event_location": event.location or "TBA",
                    "number_of_tickets": requested_tickets,
                    "total_price": float(total_price),
                    "booking_date": str(booking.booked_at),
                }
                await notification_service.send_notification(
                    db=db,
                    user=user or user_id,
                    notification_type=NotificationType.BOOKING_CONFIRMATION,
                    title=f"Booking Confirmed - {event.name}",
                    message=f"Your booking for {requested_tickets} ticket(s) to {event.name} has been confirmed!",
                    data=booking_payload,
                    priority=NotificationPriority.HIGH,
                    send_email=True,
                )
            except Exception as e:
                logger.warning(f"Failed to send booking notification: {e}")

            return booking, "Booking created successfully"

    except IntegrityError:
        return None, "Booking failed due to data conflict"
    except Exception as e:
        logger.error(f"Booking failed: {str(e)}")
        return None, f"Booking failed: {str(e)}"
    finally:
        if concurrency_manager and lock_value:
            await concurrency_manager.release_booking_lock(
                event_id, user_id, lock_value
            )


async def cancel_booking_atomic(
    db: AsyncSession, booking_id: int, user_id: Optional[int] = None
) -> Tuple[Optional[Booking], str]:
    async with db_transaction(db):
        booking_result = await db.execute(
            select(Booking).filter(Booking.id == booking_id).with_for_update()
        )
        booking = booking_result.scalars().first()
        if not booking:
            return None, "Booking not found"
    if user_id and getattr(booking, "user_id", None) != user_id:
        return None, "Not authorized to cancel this booking"
    status = getattr(booking, "status", None)
    if status != BookingStatus.CONFIRMED:
        status_str = status.value if status and hasattr(status, "value") else "Unknown"
        return None, f"Cannot cancel booking with status: {status_str}"

    event_result = await db.execute(
        select(Event).filter(Event.id == getattr(booking, "event_id", None))
    )
    event = event_result.scalars().first()
    if event and getattr(
        event, "start_date", datetime.min
    ) <= datetime.utcnow() + timedelta(hours=24):
        return None, "Cannot cancel booking within 24 hours of event start"

    # SQLAlchemy instrumented attributes are seen as Column objects by static checkers;
    # silence the assignment type errors at these instance attribute writes.
    booking.status = BookingStatus.CANCELLED
    setattr(booking, "updated_at", datetime.utcnow())

    await db.execute(
        update(Event)
        .where(Event.id == getattr(booking, "event_id", None))
        .values(
            available_tickets=getattr(event, "available_tickets", 0)
            + getattr(booking, "number_of_tickets", 0),
            updated_at=datetime.utcnow(),
        )
    )

    if concurrency_manager:
        await concurrency_manager.update_event_booking_stats(
            int(getattr(booking, "event_id", 0)), -1, "active"
        )

    # Send cancellation notification
    try:
        from app.core.notifications import notification_service
        from app.crud.user import get_user
        from app.models.notification import NotificationPriority, NotificationType

        user_id_val = getattr(booking, "user_id", None)
        user = (
            await get_user(db, user_id=user_id_val) if user_id_val is not None else None
        )
        payload = {
            "booking_id": getattr(booking, "id", None),
            "event_id": getattr(booking, "event_id", None),
            "event_name": getattr(event, "name", "TBA") if event else "TBA",
            "event_date": str(getattr(event, "start_date", "TBA")) if event else "TBA",
            "event_location": getattr(event, "location", "TBA") if event else "TBA",
            "number_of_tickets": getattr(booking, "number_of_tickets", 0),
            "cancelled_at": datetime.utcnow().isoformat(),
        }
        user_id_for_notification = None
        if user and hasattr(user, "id"):
            user_id_for_notification = user.id
        elif hasattr(booking, "user_id"):
            user_id_for_notification = booking.user_id
        if user_id_for_notification is not None:
            # Ensure user_id_for_notification is int, not SQLAlchemy Column
            if not isinstance(user_id_for_notification, int):
                user_id_for_notification = int(str(user_id_for_notification))
            await notification_service.send_notification(
                db=db,
                user=user_id_for_notification,
                notification_type=NotificationType.BOOKING_CANCELLATION,
                title=f"Booking Cancelled - {getattr(event, 'name', 'Event') if event else 'Event'}",
                message=f"Your booking for {getattr(booking, 'number_of_tickets', 0)} ticket(s) has been cancelled.",
                data=payload,
                priority=NotificationPriority.HIGH,
                send_email=True,
            )
    except Exception as e:
        logger.warning(f"Failed to send cancellation notification: {e}")

    return booking, "Booking cancelled successfully"


async def process_waitlist_conversion(
    db: AsyncSession, event_id: int, available_tickets: int, max_conversions: int = 10
) -> List[Dict[str, int]]:
    conversions: List[Dict[str, int]] = []
    remaining_tickets = available_tickets

    async with db_transaction(db):
        waitlist_result = await db.execute(
            select(Waitlist)
            .filter(
                Waitlist.event_id == event_id,
                Waitlist.status == WaitlistStatus.WAITING,
                Waitlist.number_of_tickets <= remaining_tickets,
            )
            .order_by(Waitlist.joined_at)
            .limit(max_conversions)
            .with_for_update()
        )
        waitlist_entries = waitlist_result.scalars().all()

        for entry in waitlist_entries:
            if entry.number_of_tickets > remaining_tickets:
                continue
            event_price_result = await db.execute(
                select(Event.price).filter(Event.id == event_id)
            )
            event_price = event_price_result.scalar_one_or_none()
            if event_price is None:
                continue

            booking = Booking(
                user_id=entry.user_id,
                event_id=event_id,
                number_of_tickets=entry.number_of_tickets,
                total_price=Decimal(str(event_price)) * entry.number_of_tickets,
                status=BookingStatus.CONFIRMED,
                booked_at=datetime.utcnow(),
            )
            db.add(booking)

            entry.status = WaitlistStatus.CONVERTED
            setattr(entry, "updated_at", datetime.utcnow())
            remaining_tickets -= entry.number_of_tickets

            conversions.append(
                {
                    "user_id": entry.user_id,
                    "tickets": entry.number_of_tickets,
                    "booking_id": 0,
                }
            )

        if conversions:
            tickets_converted = sum(c["tickets"] for c in conversions)
            await db.execute(
                update(Event)
                .where(Event.id == event_id)
                .values(available_tickets=Event.available_tickets - tickets_converted)
            )

        await db.flush()

        booking_query = await db.execute(
            select(Booking)
            .filter(
                Booking.event_id == event_id,
                Booking.user_id.in_([c["user_id"] for c in conversions]),
            )
            .order_by(Booking.created_at.desc())
            .limit(len(conversions))
        )
        # Convert to list to satisfy declared return types
        bookings = list(booking_query.scalars().all())

        for i, booking in enumerate(bookings):
            booking_id_val = getattr(booking, "id", None)
            conversions[i]["booking_id"] = (
                int(booking_id_val) if booking_id_val is not None else 0
            )

    return conversions


async def get_event_booking_summary(db: AsyncSession, event_id: int) -> Dict[str, Any]:
    booking_stats_result = await db.execute(
        select(
            func.count(Booking.id).label("total_bookings"),
            func.count(case((Booking.status == BookingStatus.CONFIRMED, 1))).label(
                "confirmed_bookings"
            ),
            func.count(case((Booking.status == BookingStatus.CANCELLED, 1))).label(
                "cancelled_bookings"
            ),
            coalesce(func.sum(Booking.number_of_tickets), 0).label("total_tickets"),
            coalesce(func.sum(Booking.total_price), 0).label("total_revenue"),
        ).filter(Booking.event_id == event_id)
    )
    stats_row = booking_stats_result.first()
    if stats_row is None:
        stats_row = type(
            "StatsRow",
            (),
            {
                "total_bookings": 0,
                "confirmed_bookings": 0,
                "cancelled_bookings": 0,
                "total_tickets": 0,
                "total_revenue": 0,
            },
        )()

    event_result = await db.execute(select(Event).filter(Event.id == event_id))
    event = event_result.scalars().first()
    if not event:
        return {"error": "Event not found"}

    waitlist_result = await db.execute(
        select(
            func.count(Waitlist.id).label("waitlist_size"),
            func.count(case((Waitlist.status == WaitlistStatus.CONVERTED, 1))).label(
                "waitlist_conversions"
            ),
        ).filter(Waitlist.event_id == event_id)
    )
    waitlist_row = waitlist_result.first()
    if waitlist_row is None:
        waitlist_row = type(
            "WaitlistRow", (), {"waitlist_size": 0, "waitlist_conversions": 0}
        )()

    utilization_rate = (
        (
            (getattr(event, "capacity", 0) - getattr(event, "available_tickets", 0))
            / getattr(event, "capacity", 1)
            * 100
        )
        if getattr(event, "capacity", 0) > 0
        else 0
    )

    return {
        "event_id": getattr(event, "id", event_id),
        "event_name": getattr(event, "name", ""),
        "capacity": getattr(event, "capacity", 0),
        "available_tickets": getattr(event, "available_tickets", 0),
        "utilization_rate": utilization_rate,
        "bookings": {
            "total": getattr(stats_row, "total_bookings", 0),
            "confirmed": getattr(stats_row, "confirmed_bookings", 0),
            "cancelled": getattr(stats_row, "cancelled_bookings", 0),
            "tickets_sold": getattr(stats_row, "total_tickets", 0),
            "revenue": float(getattr(stats_row, "total_revenue", 0) or 0),
        },
        "waitlist": {
            "size": getattr(waitlist_row, "waitlist_size", 0),
            "converted": getattr(waitlist_row, "waitlist_conversions", 0),
        },
    }


async def validate_booking_constraints(
    db: AsyncSession, user_id: int, event_id: int, tickets_requested: int
) -> Tuple[bool, str]:
    event_result = await db.execute(select(Event).filter(Event.id == event_id))
    event = event_result.scalars().first()
    if not event or not getattr(event, "is_active", False):
        return False, "Event not found or inactive"
    if getattr(event, "start_date", datetime.min) <= datetime.utcnow():
        return False, "Cannot book tickets for past or ongoing events"
    if tickets_requested > getattr(event, "available_tickets", 0):
        return False, f"Only {getattr(event, 'available_tickets', 0)} tickets available"

    existing_booking_result = await db.execute(
        select(Booking).filter(
            Booking.user_id == user_id,
            Booking.event_id == event_id,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING]),
        )
    )
    if existing_booking_result.scalars().first():
        return False, "User already has an active booking for this event"

    return True, "Constraints validated"


async def get_user_booking_history(
    db: AsyncSession, user_id: int, limit: int = 100, skip: int = 0
) -> List[Booking]:
    result = await db.execute(
        select(Booking)
        .filter(Booking.user_id == user_id)
        .order_by(Booking.booked_at.desc())
        .offset(skip)
        .limit(limit)
    )
    bookings = result.scalars().all()
    return list(bookings)
