import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import relationship

from ..database import Base


class WaitlistStatus(str, enum.Enum):
    WAITING = "waiting"
    NOTIFIED = "notified"
    CONVERTED = "converted"
    EXPIRED = "expired"


class Waitlist(Base):
    __tablename__ = "waitlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    joined_at = Column(DateTime, nullable=False)
    notified_at = Column(DateTime, nullable=True)
    status = Column(Enum(WaitlistStatus), default=WaitlistStatus.WAITING)
    number_of_tickets = Column(Integer, nullable=False)

    user = relationship("User")
    event = relationship("Event")

    __table_args__ = {"mysql_engine": "InnoDB"}
