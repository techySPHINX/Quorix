from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(
        String(200), index=True, nullable=False
    )  # Set length for better performance
    description = Column(Text)  # Use Text for longer descriptions
    start_date = Column(DateTime(timezone=True), nullable=False, index=True)
    end_date = Column(DateTime(timezone=True), nullable=False, index=True)
    location = Column(String(200), index=True)
    price = Column(Float, nullable=False, index=True)
    capacity = Column(Integer, nullable=False)
    available_tickets = Column(Integer, nullable=False, index=True)
    organizer_id = Column(Integer, ForeignKey("users.id"), index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organizer = relationship("User")

    # Enhanced composite indexes for common queries
    __table_args__ = (
        Index("idx_event_date_location", "start_date", "location"),
        Index("idx_event_date_active", "start_date", "is_active"),
        Index("idx_event_available_tickets", "available_tickets"),
        Index("idx_event_price_date", "price", "start_date"),
        Index("idx_event_organizer_active", "organizer_id", "is_active"),
        Index("idx_event_location_date", "location", "start_date"),
        {"postgresql_tablespace": "pg_default"},
    )
