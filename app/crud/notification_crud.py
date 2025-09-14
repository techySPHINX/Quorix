"""Notification CRUD operations."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.cleanup import cleanup_old_notifications as core_cleanup
from ..core.notification_utils import (
    create_notification as utils_create_notification,
    get_unread_notifications_since as utils_get_unread,
    get_user_preferences as utils_get_preferences,
)
from ..models.notification import NotificationPriority, NotificationType
from ..schemas.notification import NotificationCreate


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
    """Create a notification."""
    notification = NotificationCreate(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        data=str(data) if data else None,
        priority=priority,
    )
    return await utils_create_notification(db, notification)


async def get_user_preferences(
    db: AsyncSession, user_id: int
) -> Dict[str, Any]:
    """Get user notification preferences."""
    return await utils_get_preferences(db, user_id)


async def get_unread_notifications_since(
    db: AsyncSession, user_id: int, since_timestamp: str
) -> List[Any]:
    """Get unread notifications for a user since the given timestamp."""
    return await utils_get_unread(db, user_id, since_timestamp)


async def cleanup_old_notifications(
    db: AsyncSession, days: Optional[int] = None, days_to_keep: Optional[int] = None
) -> int:
    """Delete notifications older than the specified number of days.

    Accepts both `days` and `days_to_keep` for backwards compatibility.
    """
    keep = days if days is not None else days_to_keep
    return await core_cleanup(db, keep)
