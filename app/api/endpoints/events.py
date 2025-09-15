from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.schemas.event import Event as EventSchema
from app.schemas.event import EventCreate
from app.services import event_service

router = APIRouter()


@router.post("/", response_model=EventSchema, summary="Create New Event")  # type: ignore[misc]
async def create_event(
    *,
    db: AsyncSession = Depends(deps.get_db),
    event_in: EventCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> EventSchema:
    """
    **Create New Event** (Admin Only)

    Create a new event with complete details including pricing,
    location, capacity, and scheduling information.

    **Required Permissions:** Admin/Super User

    **Request Body:**
    - `name` (string): Event title
    - `description` (string): Detailed event description
    - `date` (datetime): Event date and time (ISO format)
    - `location` (string): Event venue/location
    - `max_attendees` (integer): Maximum capacity
    - `price` (float): Ticket price (0 for free events)
    - `category` (string): Event category/type

    **Example Request:**
    ```json
    {
        "name": "Tech Conference 2024",
        "description": "Annual technology conference featuring industry leaders",
        "date": "2024-06-15T09:00:00Z",
        "location": "Convention Center, Downtown",
        "max_attendees": 500,
        "price": 299.99,
        "category": "Technology"
    }
    ```

    **Response:**
    Returns the created event with assigned ID and metadata.

    **Errors:**
    - `400`: Insufficient permissions or validation error
    - `401`: Authentication required
    - `422`: Invalid event data
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    event = await event_service.create_event(
        db=db, event_data=event_in, organizer_id=current_user.id
    )
    return event


@router.get("/", response_model=List[EventSchema], summary="List Events with Filters")  # type: ignore[misc]
async def read_events(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    location: Optional[str] = Query(None, description="Filter by location"),
    min_price: Optional[float] = Query(None, description="Minimum ticket price"),
    max_price: Optional[float] = Query(None, description="Maximum ticket price"),
    available_only: bool = Query(
        False, description="Show only events with available tickets"
    ),
) -> list[EventSchema]:
    """
    **Retrieve Events with Advanced Filtering**

    Get a paginated list of events with optional filtering by location,
    price range, and availability. Results are cached for performance.

    **Query Parameters:**
    - `skip` (int): Number of events to skip (pagination)
    - `limit` (int): Maximum events to return (max 100)
    - `location` (string, optional): Filter by event location
    - `min_price` (float, optional): Minimum ticket price filter
    - `max_price` (float, optional): Maximum ticket price filter
    - `available_only` (bool): Only show events with available tickets

    **Example Requests:**
    ```bash
    # Get all events
    GET /api/v1/events/

    # Get events in New York with tickets under $100
    GET /api/v1/events/?location=New%20York&max_price=100

    # Get available events only, skip first 20
    GET /api/v1/events/?skip=20&limit=10&available_only=true
    ```

    **Response:**
    Array of event objects with complete details including availability status.

    **Caching:**
    Results are cached using a versioned, hash-based strategy to ensure
    data consistency and performance.
    """
    filters = {
        "skip": skip,
        "limit": limit,
        "location": location,
        "min_price": min_price,
        "max_price": max_price,
        "available_only": available_only,
    }
    events = await event_service.get_events_list_cached(db=db, filters=filters)
    return events


@router.get("/{event_id}", response_model=EventSchema, summary="Get Event Details")  # type: ignore[misc]
async def read_event(
    *,
    db: AsyncSession = Depends(deps.get_db),
    event_id: int,
) -> EventSchema:
    """
    **Get Event by ID**

    Retrieve complete details for a specific event including
    current availability, booking statistics, and metadata.

    **Path Parameters:**
    - `event_id` (integer): Unique event identifier

    **Example Request:**
    ```bash
    GET /api/v1/events/123
    ```

    **Response:**
    Complete event object with:
    - Basic details (name, description, date, location)
    - Pricing and capacity information
    - Current availability and booking stats
    - Organizer information

    **Errors:**
    - `404`: Event not found
    - `422`: Invalid event ID format

    **Caching:**
    Event details are cached for 1 hour for optimal performance.
    """
    event = await event_service.get_event_by_id_cached(db=db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put("/{event_id}", response_model=EventSchema, summary="Update Event")  # type: ignore[misc]
async def update_event(
    *,
    db: AsyncSession = Depends(deps.get_db),
    event_id: int,
    event_in: EventCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> EventSchema:
    """
    **Update Event Details** (Admin Only)

    Modify an existing event's information including pricing,
    capacity, description, and scheduling.

    **Required Permissions:** Admin/Super User

    **Path Parameters:**
    - `event_id` (integer): Event to update

    **Request Body:**
    Complete event object with updated fields (same as create event).

    **Example Request:**
    ```json
    {
        "name": "Updated Event Name",
        "description": "New description",
        "date": "2024-07-15T10:00:00Z",
        "location": "New Venue",
        "max_attendees": 600,
        "price": 349.99,
        "category": "Technology"
    }
    ```

    **Errors:**
    - `400`: Insufficient permissions
    - `401`: Authentication required
    - `404`: Event not found
    - `422`: Invalid update data

    **Note:**
    Updating an event invalidates related caches and may affect existing bookings.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")

    event = await event_service.update_event_and_invalidate(
        db=db, event_id=event_id, event_data=event_in
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.delete("/{event_id}", response_model=EventSchema, summary="Delete Event")  # type: ignore[misc]
async def delete_event(
    *,
    db: AsyncSession = Depends(deps.get_db),
    event_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> dict:
    """
    **Delete Event** (Admin Only)

    Permanently delete an event and all associated data.
    This action cannot be undone.

    **Required Permissions:** Admin/Super User

    **Path Parameters:**
    - `event_id` (integer): Event to delete

    **Example Request:**
    ```bash
    DELETE /api/v1/events/123
    ```

    **Response:**
    Returns the deleted event object for confirmation.

    **Errors:**
    - `400`: Insufficient permissions
    - `401`: Authentication required
    - `404`: Event not found

    **Warning:**
    Deleting an event will:
    - Cancel all existing bookings
    - Remove waitlist entries
    - Delete associated notifications
    - Clear related analytics data

    Consider updating the event status instead of deletion for historical records.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")

    if not await event_service.delete_event_and_invalidate(db=db, event_id=event_id):
        raise HTTPException(status_code=404, detail="Event not found")

    return {"detail": "Event deleted successfully"}
