import enum
from typing import Optional

from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..database import Base


class WaitlistStatus(str, enum.Enum):
    WAITING = "waiting"
    NOTIFIED = "notified"
    CONVERTED = "converted"
    EXPIRED = "expired"


class Waitlist(Base):
    __tablename__ = "waitlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id"), nullable=False, index=True
    )
    joined_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, server_default=func.now()
    )
    notified_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    status: Mapped[WaitlistStatus] = mapped_column(
        SQLEnum(WaitlistStatus), default=WaitlistStatus.WAITING, index=True
    )
    number_of_tickets: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User")
    event = relationship("Event")

    # Enhanced indexes for waitlist management
    __table_args__ = (
        Index("idx_waitlist_event_status", "event_id", "status"),
        Index("idx_waitlist_user_status", "user_id", "status"),
        Index("idx_waitlist_status_joined", "status", "joined_at"),
        Index("idx_waitlist_event_joined", "event_id", "joined_at"),
        Index("idx_waitlist_unique_user_event", "user_id", "event_id", unique=True),
        {"postgresql_tablespace": "pg_default"},
    )
