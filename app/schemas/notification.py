from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from ..models.notification import NotificationPriority, NotificationType


class NotificationBase(BaseModel):
    type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str = Field(..., max_length=255)
    message: str
    data: Optional[str] = None


class NotificationCreate(NotificationBase):
    user_id: int


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
    read_at: Optional[datetime] = None


class NotificationInDB(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Notification(NotificationInDB):
    pass


class NotificationStats(BaseModel):
    total_notifications: int
    unread_count: int
    read_count: int
