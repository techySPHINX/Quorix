from pydantic import BaseModel
from datetime import datetime
from .user import User
from .event import Event
from ..models.booking import BookingStatus

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

    model_config = {'from_attributes': True}
