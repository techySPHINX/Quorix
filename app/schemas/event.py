from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class EventBase(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    location: str
    price: float
    capacity: int = Field(..., gt=0, description="Capacity must be positive.")


class EventCreate(EventBase):
    pass


class Event(EventBase):
    id: int
    organizer_id: int
    available_tickets: int

    model_config = ConfigDict(from_attributes=True)
