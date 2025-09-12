from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .. import models, schemas


async def get_event(db: AsyncSession, event_id: int):
    result = await db.execute(select(models.Event).filter(models.Event.id == event_id))
    return result.scalars().first()


async def get_events(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Event).offset(skip).limit(limit))
    return result.scalars().all()


async def create_event(db: AsyncSession, event: schemas.EventCreate, organizer_id: int):
    db_event = models.Event(
        **event.model_dump(),  # Use model_dump for Pydantic v2
        organizer_id=organizer_id,
        available_tickets=event.capacity,
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event


async def update_event(db: AsyncSession, event_id: int, event: schemas.EventCreate):
    db_event = await get_event(db, event_id)
    if db_event:
        for key, value in event.model_dump(exclude_unset=True).items():  # Use model_dump for Pydantic v2
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
