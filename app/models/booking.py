import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer
from sqlalchemy.orm import relationship

from ..database import Base


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    booked_at = Column(DateTime, nullable=False, index=True)
    number_of_tickets = Column(Integer, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING, index=True)

    user = relationship("User")
    event = relationship("Event")

    # Composite indexes for analytics queries
    __table_args__ = (
        Index("idx_booking_user_status", "user_id", "status"),
        Index("idx_booking_event_status", "event_id", "status"),
        Index("idx_booking_date_status", "booked_at", "status"),
        {"mysql_engine": "InnoDB"},
    )
