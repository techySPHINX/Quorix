"""Notification utilities."""
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.notification import create_notification as crud_create_notification
from app.models.notification import NotificationPriority, NotificationType
from app.schemas.notification import NotificationCreate


async def create_notification(
    db: AsyncSession,
    *,
    user_id: int,
    notification_type: NotificationType,
    title: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    priority: NotificationPriority = NotificationPriority.NORMAL,
) -> Any:
    """Create a notification with the given parameters."""
    notification = NotificationCreate(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        data=str(data) if data else None,
        priority=priority,
    )
    return await crud_create_notification(db, notification)


async def get_user_preferences(db: AsyncSession, user_id: int) -> Dict[str, Any]:
    """Get user notification preferences."""
    # TODO: Implement user preferences
    return {
        "email_notifications": True,
        "digest_frequency": "daily",
        "notification_types": ["all"],
    }


async def get_unread_notifications_since(
    db: AsyncSession, user_id: int, since_timestamp: str
) -> list:
    """Get unread notifications for a user since the given timestamp."""
    # TODO: Implement unread notifications retrieval
    return []
