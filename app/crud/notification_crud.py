"""Notification CRUD operations."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.cleanup import cleanup_old_notifications as core_cleanup
from ..core.notification_utils import get_unread_notifications_since as utils_get_unread
from ..core.notification_utils import get_user_preferences as utils_get_preferences
from ..models.notification import NotificationPriority, NotificationType
from ..schemas.notification import NotificationCreate
from .notification import create_notification as crud_create_notification


async def create_notification(
    db: AsyncSession,
    *,
    user_id: int,
    notification_type: Union[NotificationType, str],
    title: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    priority: NotificationPriority = NotificationPriority.NORMAL,
) -> Any:
    """Create a notification."""
    # Accept either enum or raw string for notification_type
    # Check for NotificationType first because Enum members subclass str and
    # isinstance(x, str) would be True for enum members which makes the
    # alternate branch unreachable.
    if isinstance(notification_type, NotificationType):
        nt = notification_type
    else:
        nt = NotificationType(notification_type)

    notification = NotificationCreate(
        user_id=user_id,
        type=nt,
        title=title,
        message=message,
        data=str(data) if data else None,
        priority=priority,
    )
    # Call the lower-level CRUD implementation which accepts NotificationCreate
    return await crud_create_notification(db, notification)


async def get_user_preferences(db: AsyncSession, user_id: int) -> Any:
    """Get user notification preferences."""
    return await utils_get_preferences(db, user_id)


async def get_unread_notifications_since(
    db: AsyncSession, user_id: int, since: Optional[Union[datetime, str]] = None
) -> List[Any]:
    """Get unread notifications for a user since the given timestamp.

    Accepts keyword `since` (datetime or str) for compatibility with tasks.
    """
    return await utils_get_unread(db, user_id, since)


async def cleanup_old_notifications(
    db: AsyncSession, days: Optional[int] = None, days_to_keep: Optional[int] = None
) -> int:
    """Delete notifications older than the specified number of days.

    Accepts both `days` and `days_to_keep` for backwards compatibility.
    """
    keep = days if days is not None else days_to_keep
    return await core_cleanup(db, keep)
