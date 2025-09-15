from typing import Optional, List, Dict, Any
import hashlib
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import event as event_crud
from app.schemas.event import Event, EventCreate
from app.utils.cache import cache_get, invalidate_cache, get_redis

CACHE_TTL_SECONDS = 60 * 5
EVENTS_LIST_VERSION_KEY = "events_list_version"


async def _invalidate_events_list_cache() -> None:
    """Increments the version key for event lists, invalidating all list caches."""
    r = get_redis()
    await r.incr(EVENTS_LIST_VERSION_KEY)


async def get_event_by_id_cached(
    db: AsyncSession, event_id: int
) -> Optional[Event]:
    """
    Reads an event from the cache if available, otherwise from the database.
    """
    key = f"event:{event_id}"

    async def db_loader() -> Optional[Event]:
        event_obj = await event_crud.get_event(db, event_id=event_id)
        if event_obj:
            return Event.model_validate(event_obj)
        return None

    return await cache_get(
        key=key,
        ttl=CACHE_TTL_SECONDS,
        db_loader=db_loader,
        serializer=lambda pyd: pyd.model_dump_json(),
        deserializer=lambda s: Event.model_validate_json(s),
    )


async def get_events_list_cached(
    db: AsyncSession, filters: Dict[str, Any]
) -> List[Event]:
    """
    Gets a cached list of events based on filters. Caching is versioned to allow
    for robust invalidation when any event is created, updated, or deleted.
    """
    r = get_redis()
    version = await r.get(EVENTS_LIST_VERSION_KEY) or 0
    
    # Create a stable hash of the filters dictionary for the cache key
    filters_json = json.dumps(filters, sort_keys=True)
    filters_hash = hashlib.sha256(filters_json.encode()).hexdigest()
    
    key = f"events_list:v{version}:{filters_hash}"

    async def db_loader() -> List[Event]:
        events_list = await event_crud.get_events_filtered(db, **filters)
        return [Event.model_validate(event) for event in events_list]

    # The serializer needs to handle a list of Pydantic models
    def list_serializer(events: List[Event]) -> str:
        return json.dumps([event.model_dump() for event in events])

    # The deserializer needs to convert a list of dicts back to Event models
    def list_deserializer(data: str) -> List[Event]:
        return [Event(**item) for item in json.loads(data)]

    return await cache_get(
        key=key,
        ttl=CACHE_TTL_SECONDS,
        db_loader=db_loader,
        serializer=list_serializer,
        deserializer=list_deserializer,
    )


async def create_event(
    db: AsyncSession, event_data: EventCreate, organizer_id: int
) -> Event:
    """
    Creates an event, invalidates the event list cache, and returns the new event.
    """
    event_obj = await event_crud.create_event(
        db, event=event_data, organizer_id=organizer_id
    )
    await _invalidate_events_list_cache()
    return Event.model_validate(event_obj)


async def update_event_and_invalidate(
    db: AsyncSession, event_id: int, event_data: EventCreate
) -> Optional[Event]:
    """
    Updates an event, invalidates both single-item and list caches.
    """
    updated_event = await event_crud.update_event(
        db, event_id=event_id, event=event_data
    )
    if updated_event:
        await invalidate_cache(f"event:{event_id}")
        await _invalidate_events_list_cache()
        return Event.model_validate(updated_event)
    return None


async def delete_event_and_invalidate(db: AsyncSession, event_id: int) -> bool:
    """
    Deletes an event, invalidates both single-item and list caches.
    """
    deleted_event = await event_crud.delete_event(db, event_id=event_id)
    if deleted_event:
        await invalidate_cache(f"event:{event_id}")
        await _invalidate_events_list_cache()
        return True
    return False
