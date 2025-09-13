from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EventBase(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    location: str
    price: float
    capacity: int


class EventCreate(EventBase):
    pass


class Event(EventBase):
    id: int
    organizer_id: int
    available_tickets: int

    model_config = {"from_attributes": True}
