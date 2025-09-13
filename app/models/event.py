from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from ..database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String)
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=False, index=True)
    location = Column(String, index=True)
    price = Column(Float, nullable=False, index=True)
    capacity = Column(Integer, nullable=False)
    available_tickets = Column(Integer, nullable=False, index=True)
    organizer_id = Column(Integer, ForeignKey("users.id"), index=True)

    organizer = relationship("User")

    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_event_date_location", "start_date", "location"),
        Index("idx_event_available_tickets", "available_tickets"),
        Index("idx_event_price_range", "price"),
        {"mysql_engine": "InnoDB"},
    )
