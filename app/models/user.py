import enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

if TYPE_CHECKING:
    from .booking import Booking
    from .notification import Notification, NotificationPreference
    from .waitlist import Waitlist


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole), default=UserRole.USER, nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_login: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Relationships
    bookings: Mapped[List["Booking"]] = relationship(
        "Booking", back_populates="user", cascade="all, delete-orphan"
    )
    waitlist_entries: Mapped[List["Waitlist"]] = relationship(
        "Waitlist", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
    notification_preferences: Mapped[Optional["NotificationPreference"]] = relationship(
        "NotificationPreference",
        back_populates="user",
        uselist=False,  # One-to-one relationship
        cascade="all, delete-orphan",
    )

    # Composite indexes
    __table_args__ = (
        Index("idx_user_active_role", "is_active", "role"),
        Index("idx_user_created_role", "created_at", "role"),
        {"postgresql_tablespace": "pg_default"},
    )
