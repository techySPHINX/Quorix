from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .... import crud
from .... import schemas
from ....api import deps

router = APIRouter()

@router.post("/", response_model=schemas.Event)
def create_event(
    *, 
    db: Session = Depends(deps.get_db),
    event_in: schemas.EventCreate,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    Create new event.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    event = crud.event.create_event(db=db, event=event_in, organizer_id=current_user.id)
    return event

@router.get("/", response_model=List[schemas.Event])
def read_events(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    Retrieve events.
    """
    events = crud.event.get_events(db, skip=skip, limit=limit)
    return events

@router.get("/{event_id}", response_model=schemas.Event)
def read_event(
    *, 
    db: Session = Depends(deps.get_db),
    event_id: int,
):
    """
    Get event by ID.
    """
    event = crud.event.get_event(db=db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@router.put("/{event_id}", response_model=schemas.Event)
def update_event(
    *, 
    db: Session = Depends(deps.get_db),
    event_id: int,
    event_in: schemas.EventCreate,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    Update an event.
    """
    event = crud.event.get_event(db=db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    event = crud.event.update_event(db=db, event_id=event_id, event=event_in)
    return event

@router.delete("/{event_id}", response_model=schemas.Event)
def delete_event(
    *, 
    db: Session = Depends(deps.get_db),
    event_id: int,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    Delete an event.
    """
    event = crud.event.get_event(db=db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    event = crud.event.delete_event(db=db, event_id=event_id)
    return event
