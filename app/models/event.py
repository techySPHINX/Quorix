from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    location = Column(String)
    price = Column(Float, nullable=False)
    capacity = Column(Integer, nullable=False)
    available_tickets = Column(Integer, nullable=False)
    organizer_id = Column(Integer, ForeignKey("users.id"))

    organizer = relationship("User")
