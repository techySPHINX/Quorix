import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.api import deps
from app.models.user import User, UserRole
from app.schemas.waitlist import Waitlist, WaitlistCreate

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{event_id}/join", response_model=Waitlist)  # type: ignore[misc]
async def join_event_waitlist(
    *,
    event_id: int,
    waitlist_in: WaitlistCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Waitlist:
    """
    Join waitlist for a sold-out event.
    """
    # Verify event exists and is sold out
    event = await crud.event.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.available_tickets >= waitlist_in.number_of_tickets:
        raise HTTPException(
            status_code=400, detail="Event has available tickets. Please book directly."
        )

    # Ensure the waitlist entry is for the correct event
    waitlist_in.event_id = event_id

    waitlist_entry = await crud.waitlist.join_waitlist(db, waitlist_in, current_user.id)
    if not waitlist_entry:
        raise HTTPException(
            status_code=400, detail="User is already on the waitlist for this event"
        )

    return waitlist_entry


@router.get("/my-waitlist", response_model=List[Waitlist])  # type: ignore[misc]
async def get_my_waitlist(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    skip: int = 0,
    limit: int = 100,
) -> list[Waitlist]:
    """
    Get current user's waitlist entries.
    """
    return await crud.waitlist.get_user_waitlist(db, current_user.id, skip, limit)


@router.delete("/{waitlist_id}")  # type: ignore[misc]
async def leave_waitlist(
    waitlist_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> dict[str, str]:
    """
    Leave a waitlist.
    """
    # Verify user owns this waitlist entry
    waitlist_entry = await crud.waitlist.get_waitlist_entry(db, waitlist_id)
    if not waitlist_entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")

    if waitlist_entry.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    success = await crud.waitlist.remove_from_waitlist(db, waitlist_id)
    if not success:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")

    return {"message": "Successfully removed from waitlist"}


@router.get("/{event_id}/stats")  # type: ignore[misc]
async def get_event_waitlist_stats(
    event_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(UserRole.ADMIN)),
) -> dict[str, int]:
    """
    Get waitlist statistics for an event (admin only).
    """

    # Verify event exists
    event = await crud.event.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return await crud.waitlist.get_waitlist_stats(db, event_id)


@router.get("/{event_id}/list")  # type: ignore[misc]
async def get_event_waitlist(
    event_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> list[Waitlist]:
    """
    Get waitlist for an event (admin only).
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Verify event exists
    event = await crud.event.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return await crud.waitlist.get_event_waitlist(db, event_id)
