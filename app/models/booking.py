import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

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
    booked_at = Column(
        DateTime(timezone=True), nullable=False, index=True, server_default=func.now()
    )
    number_of_tickets = Column(Integer, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=True)  # Store calculated price
    status: BookingStatus = Column(
        Enum(BookingStatus), default=BookingStatus.PENDING, index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User")
    event = relationship("Event")

    # Enhanced composite indexes for analytics and performance
    __table_args__ = (
        Index("idx_booking_user_status", "user_id", "status"),
        Index("idx_booking_event_status", "event_id", "status"),
        Index("idx_booking_date_status", "booked_at", "status"),
        Index("idx_booking_user_date", "user_id", "booked_at"),
        Index("idx_booking_event_date", "event_id", "booked_at"),
        Index("idx_booking_status_date", "status", "booked_at"),
        {"postgresql_tablespace": "pg_default"},
    )
