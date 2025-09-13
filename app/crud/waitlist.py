from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.waitlist import Waitlist, WaitlistStatus
from app.schemas.waitlist import WaitlistCreate


async def get_waitlist_entry(db: AsyncSession, waitlist_id: int) -> Optional[Waitlist]:
    result = await db.execute(select(Waitlist).filter(Waitlist.id == waitlist_id))
    return result.scalars().first()


async def get_waitlist_by_user_event(
    db: AsyncSession, user_id: int, event_id: int
) -> Optional[Waitlist]:
    result = await db.execute(
        select(Waitlist).filter(
            Waitlist.user_id == user_id,
            Waitlist.event_id == event_id,
            Waitlist.status == WaitlistStatus.WAITING,
        )
    )
    return result.scalars().first()


async def get_event_waitlist(
    db: AsyncSession, event_id: int, status: WaitlistStatus = WaitlistStatus.WAITING
) -> List[Waitlist]:
    result = await db.execute(
        select(Waitlist)
        .filter(Waitlist.event_id == event_id, Waitlist.status == status)
        .order_by(Waitlist.joined_at.asc())
    )
    return result.scalars().all()


async def join_waitlist(
    db: AsyncSession, waitlist: WaitlistCreate, user_id: int
) -> Optional[Waitlist]:
    # Check if user is already on waitlist for this event
    existing = await get_waitlist_by_user_event(db, user_id, waitlist.event_id)
    if existing:
        return None

    db_waitlist = Waitlist(
        **waitlist.model_dump(),
        user_id=user_id,
        joined_at=datetime.utcnow(),
        status=WaitlistStatus.WAITING
    )
    db.add(db_waitlist)
    await db.commit()
    await db.refresh(db_waitlist)
    return db_waitlist


async def notify_waitlist_users(
    db: AsyncSession, event_id: int, available_tickets: int
) -> List[Waitlist]:
    """Notify waitlist users when tickets become available"""
    notified_users = []

    # Get waiting users in order of joining
    waiting_users = await get_event_waitlist(db, event_id, WaitlistStatus.WAITING)

    for waitlist_entry in waiting_users:
        if available_tickets >= waitlist_entry.number_of_tickets:
            waitlist_entry.status = WaitlistStatus.NOTIFIED
            waitlist_entry.notified_at = datetime.utcnow()
            notified_users.append(waitlist_entry)
            available_tickets -= waitlist_entry.number_of_tickets
        else:
            break

    if notified_users:
        await db.commit()

    return notified_users


async def remove_from_waitlist(db: AsyncSession, waitlist_id: int) -> bool:
    waitlist_entry = await get_waitlist_entry(db, waitlist_id)
    if waitlist_entry:
        await db.delete(waitlist_entry)
        await db.commit()
        return True
    return False


async def get_user_waitlist(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
) -> List[Waitlist]:
    result = await db.execute(
        select(Waitlist)
        .filter(Waitlist.user_id == user_id)
        .order_by(Waitlist.joined_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_waitlist_stats(db: AsyncSession, event_id: int) -> dict:
    """Get waitlist statistics for an event"""
    result = await db.execute(
        select(
            func.count(Waitlist.id).label("total_waiting"),
            func.sum(Waitlist.number_of_tickets).label("total_tickets_needed"),
        ).filter(
            Waitlist.event_id == event_id, Waitlist.status == WaitlistStatus.WAITING
        )
    )
    stats = result.first()
    return {
        "total_waiting": stats.total_waiting or 0,
        "total_tickets_needed": stats.total_tickets_needed or 0,
    }
