import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.notification import (
    Notification,
    NotificationPriority,
    NotificationType,
)
from ..schemas.notification import NotificationCreate

logger = logging.getLogger(__name__)


async def create_notification(
    db: AsyncSession,
    notification: NotificationCreate
) -> Notification:
    """Create a new in-app notification"""
    db_notification = Notification(**notification.model_dump())
    db.add(db_notification)
    await db.commit()
    await db.refresh(db_notification)
    return db_notification


async def create_bulk(
    db: AsyncSession,
    user_ids: List[int],
    notification_type: NotificationType,
    title: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    priority: NotificationPriority = NotificationPriority.NORMAL,
) -> List[Notification]:
    """Create notifications for multiple users"""
    notifications = []

    for user_id in user_ids:
        db_notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            data=str(data) if data else None,
            priority=priority
        )
        notifications.append(db_notification)

    db.add_all(notifications)
    await db.commit()

    for notification in notifications:
        await db.refresh(notification)

    return notifications


async def get_user_notifications(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    unread_only: bool = False,
    notification_types: Optional[List[NotificationType]] = None,
    priority: Optional[NotificationPriority] = None
) -> List[Notification]:
    """Get user's notifications with filtering and pagination"""
    query = select(Notification).filter(Notification.user_id == user_id)

    # Apply filters
    if unread_only:
        query = query.filter(Notification.is_read == False)

    if notification_types:
        query = query.filter(Notification.type.in_(notification_types))

    if priority:
        query = query.filter(Notification.priority == priority)

    # Apply pagination and ordering
    query = query.order_by(desc(Notification.created_at)).offset(skip).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_notification(
    db: AsyncSession,
    notification_id: int
) -> Optional[Notification]:
    """Get notification by ID"""
    result = await db.execute(
        select(Notification).filter(Notification.id == notification_id)
    )
    return result.scalars().first()


async def mark_read(
    db: AsyncSession,
    notification_id: int
) -> Optional[Notification]:
    """Mark a notification as read"""
    result = await db.execute(
        select(Notification).filter(Notification.id == notification_id)
    )
    notification = result.scalars().first()

    if notification:
        notification.is_read = True  # type: ignore[assignment]
        notification.read_at = datetime.utcnow()  # type: ignore[assignment]
        await db.commit()
        await db.refresh(notification)

    return notification


async def mark_all_read(
    db: AsyncSession,
    user_id: int
) -> int:
    """Mark all user notifications as read"""
    result = await db.execute(
        select(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        )
    )
    notifications = result.scalars().all()

    count = 0
    for notification in notifications:
        notification.is_read = True  # type: ignore[assignment]
        notification.read_at = datetime.utcnow()  # type: ignore[assignment]
        count += 1

    if count > 0:
        await db.commit()

    return count


async def delete_notification(
    db: AsyncSession,
    notification_id: int
) -> bool:
    """Delete a notification"""
    result = await db.execute(
        select(Notification).filter(Notification.id == notification_id)
    )
    notification = result.scalars().first()

    if notification:
        await db.delete(notification)
        await db.commit()
        return True

    return False


async def get_user_stats(
    db: AsyncSession,
    user_id: int
) -> Dict[str, Any]:
    """Get notification statistics for a user"""

    # Get total notifications
    total_result = await db.execute(
        select(func.count(Notification.id)).filter(Notification.user_id == user_id)
    )
    total = total_result.scalar() or 0

    # Get unread count
    unread_result = await db.execute(
        select(func.count(Notification.id)).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        )
    )
    unread = unread_result.scalar() or 0

    # Get recent notifications (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_result = await db.execute(
        select(func.count(Notification.id)).filter(
            Notification.user_id == user_id,
            Notification.created_at >= week_ago
        )
    )
    recent = recent_result.scalar() or 0

    return {
        "total_notifications": total,
        "unread_count": unread,
        "read_count": total - unread,
        "recent_notifications": recent,
    }
