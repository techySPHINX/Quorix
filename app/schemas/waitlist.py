from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from ..models.waitlist import WaitlistStatus
from .event import Event
from .user import User


class WaitlistBase(BaseModel):
    event_id: int
    number_of_tickets: int = Field(
        ..., gt=0, description="Number of tickets must be positive."
    )


class WaitlistCreate(WaitlistBase):
    pass


class Waitlist(WaitlistBase):
    id: int
    user_id: int
    joined_at: datetime
    notified_at: Optional[datetime] = None
    status: WaitlistStatus
    user: User
    event: Event

    model_config = ConfigDict(from_attributes=True)
