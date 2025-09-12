from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import json

from .... import crud
from .... import schemas
from ....api import deps
from ....redis import redis_client # Import redis client

router = APIRouter()

@router.post("/", response_model=schemas.Event)
async def create_event(
    *,
    db: AsyncSession = Depends(deps.get_db),
    event_in: schemas.EventCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Create new event.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    event = await crud.event.create_event(db=db, event=event_in, organizer_id=current_user.id)
    # Invalidate cache for events list
    await redis_client.delete("events_list")
    return event

@router.get("/", response_model=List[schemas.Event])
async def read_events(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    Retrieve events.
    """
    cache_key = f"events_list_skip_{skip}_limit_{limit}"
    cached_events = await redis_client.get(cache_key)
    if cached_events:
        return json.loads(cached_events)

    events = await crud.event.get_events(db, skip=skip, limit=limit)
    await redis_client.setex(cache_key, 3600, json.dumps([event.model_dump_json() for event in events])) # Cache for 1 hour
    return events

@router.get("/{event_id}", response_model=schemas.Event)
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
    await redis_client.setex(cache_key, 3600, event.model_dump_json()) # Cache for 1 hour
    return event

@router.put("/{event_id}", response_model=schemas.Event)
async def update_event(
    *,
    db: AsyncSession = Depends(deps.get_db),
    event_id: int,
    event_in: schemas.EventCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
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
    await redis_client.delete("events_list")
    return event

@router.delete("/{event_id}", response_model=schemas.Event)
async def delete_event(
    *,
    db: AsyncSession = Depends(deps.get_db),
    event_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
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
    await redis_client.delete("events_list")
    return event
