from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLEnum


class Base(DeclarativeBase):
    pass


class NotificationType(str, Enum):
    BOOKING_CONFIRMATION = "booking_confirmation"
    BOOKING_CANCELLATION = "booking_cancellation"
    EVENT_REMINDER = "event_reminder"
    WAITLIST_NOTIFICATION = "waitlist_notification"
    PAYMENT_RECEIVED = "payment_received"
    EVENT_UPDATE = "event_update"
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    PASSWORD_RESET = "password_reset"  # nosec B105: Enum label, not a password
    WELCOME = "welcome"


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    IN_APP = "in_app"
    SMS = "sms"
    PUSH = "push"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[NotificationType] = mapped_column(SQLEnum(NotificationType), nullable=False, index=True)
    priority: Mapped[NotificationPriority] = mapped_column(
        SQLEnum(NotificationPriority), default=NotificationPriority.NORMAL, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="notifications")


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    notification_id: Mapped[Optional[int]] = mapped_column(ForeignKey("notifications.id"), nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    channel: Mapped[NotificationChannel] = mapped_column(SQLEnum(NotificationChannel), nullable=False, index=True)
    type: Mapped[NotificationType] = mapped_column(SQLEnum(NotificationType), nullable=False, index=True)
    priority: Mapped[NotificationPriority] = mapped_column(
        SQLEnum(NotificationPriority), default=NotificationPriority.NORMAL
    )

    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    template_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    next_retry_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)

    sent_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User")
    notification = relationship("Notification")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True, index=True)

    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    booking_confirmations: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    booking_cancellations: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    event_reminders: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    waitlist_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    payment_updates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    event_updates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    system_announcements: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    marketing_emails: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    quiet_hours_start: Mapped[Optional[str]] = mapped_column(String(5), default="22:00", nullable=True)
    quiet_hours_end: Mapped[Optional[str]] = mapped_column(String(5), default="08:00", nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="notification_preferences")
