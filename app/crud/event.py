from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.schemas.event import EventCreate


async def get_event(db: AsyncSession, event_id: int):
    result = await db.execute(select(Event).filter(Event.id == event_id))
    return result.scalars().first()


async def get_events(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(Event).offset(skip).limit(limit))
    return result.scalars().all()


async def get_events_filtered(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    location: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    available_only: bool = False,
):
    """Get events with optional filtering"""
    query = select(Event)

    filters = []
    if location:
        filters.append(Event.location.ilike(f"%{location}%"))
    if min_price is not None:
        filters.append(Event.price >= min_price)
    if max_price is not None:
        filters.append(Event.price <= max_price)
    if available_only:
        filters.append(Event.available_tickets > 0)

    if filters:
        query = query.filter(and_(*filters))

    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


async def create_event(db: AsyncSession, event: EventCreate, organizer_id: int):
    db_event = Event(
        **event.model_dump(),
        organizer_id=organizer_id,
        available_tickets=event.capacity,
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event


async def update_event(db: AsyncSession, event_id: int, event: EventCreate):
    db_event = await get_event(db, event_id)
    if db_event:
        for key, value in event.model_dump(exclude_unset=True).items():
            setattr(db_event, key, value)
        await db.commit()
        await db.refresh(db_event)
    return db_event


async def delete_event(db: AsyncSession, event_id: int):
    db_event = await get_event(db, event_id)
    if db_event:
        await db.delete(db_event)
        await db.commit()
    return db_event
