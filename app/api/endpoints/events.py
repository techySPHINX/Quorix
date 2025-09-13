import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.api import deps
from app.models.user import User
from app.redis import redis_client
from app.schemas.event import Event as EventSchema
from app.schemas.event import EventCreate

router = APIRouter()


@router.post("/", response_model=EventSchema)
async def create_event(
    *,
    db: AsyncSession = Depends(deps.get_db),
    event_in: EventCreate,
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Create new event.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    event = await crud.event.create_event(
        db=db, event=event_in, organizer_id=current_user.id
    )
    # Invalidate cache for events list
    for key in await redis_client.keys("events:*"):
        await redis_client.delete(key)
    return event


@router.get("/", response_model=List[EventSchema])
async def read_events(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    location: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    available_only: bool = False,
):
    """
    Retrieve events with optional filtering.
    """
    # Build cache key with filters
    cache_key = (
        f"events:skip={skip},limit={limit},loc={location},"
        f"min={min_price},max={max_price},avail={available_only}"
    )
    cached_events = await redis_client.get(cache_key)
    if cached_events:
        return json.loads(cached_events)

    events = await crud.event.get_events_filtered(
        db,
        skip=skip,
        limit=limit,
        location=location,
        min_price=min_price,
        max_price=max_price,
        available_only=available_only,
    )

    await redis_client.setex(
        cache_key, 1800, json.dumps([event.model_dump() for event in events])
    )  # Cache for 30 minutes due to filtering

    return events


@router.get("/{event_id}", response_model=EventSchema)
async def read_event(
    *,
    db: AsyncSession = Depends(deps.get_db),
    event_id: int,
):
    """
    Get event by ID.
    """
    cache_key = f"event_{event_id}"
    cached_event = await redis_client.get(cache_key)
    if cached_event:
        return json.loads(cached_event)

    event = await crud.event.get_event(db=db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    await redis_client.setex(
        cache_key, 3600, json.dumps(event.model_dump())
    )  # Cache for 1 hour
    return event


@router.put("/{event_id}", response_model=EventSchema)
async def update_event(
    *,
    db: AsyncSession = Depends(deps.get_db),
    event_id: int,
    event_in: EventCreate,
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Update an event.
    """
    event = await crud.event.get_event(db=db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    event = await crud.event.update_event(db=db, event_id=event_id, event=event_in)
    # Invalidate cache for this event and events list
    await redis_client.delete(f"event_{event_id}")
    for key in await redis_client.keys("events:*"):
        await redis_client.delete(key)
    return event


@router.delete("/{event_id}", response_model=EventSchema)
async def delete_event(
    *,
    db: AsyncSession = Depends(deps.get_db),
    event_id: int,
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Delete an event.
    """
    event = await crud.event.get_event(db=db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    event = await crud.event.delete_event(db=db, event_id=event_id)
    # Invalidate cache for this event and events list
    await redis_client.delete(f"event_{event_id}")
    for key in await redis_client.keys("events:*"):
        await redis_client.delete(key)
    return event
