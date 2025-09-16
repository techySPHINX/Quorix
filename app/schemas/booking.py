from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ..models.booking import BookingStatus
from .event import Event
from .user import User


class BookingBase(BaseModel):
    event_id: int
    number_of_tickets: int


class BookingCreate(BookingBase):
    pass


class Booking(BookingBase):
    id: int
    user_id: int
    booked_at: datetime
    status: BookingStatus
    user: User
    event: Event

    model_config = ConfigDict(from_attributes=True)
