"""Notification utilities.

This module provides a thin compatibility layer used by tasks and CRUD code.
It intentionally accepts both enum and string types for notification types and
returns lightweight objects with attributes consumed by higher-level code so
the rest of the application doesn't need to directly import ORM models.
"""

from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.notification import create_notification as crud_create_notification
from app.models.notification import (
    Notification,
    NotificationPreference,
    NotificationPriority,
    NotificationType,
)
from app.schemas.notification import NotificationCreate


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
    """Create a notification with the given parameters.

    Accepts either NotificationType or raw string for compatibility with tasks.
    """
    # Coerce to NotificationType deterministically. Converting to str first
    # works for both enum members and raw strings and avoids branching that
    # can confuse the type checker.
    nt = NotificationType(str(notification_type))

    notification = NotificationCreate(
        user_id=user_id,
        type=nt,
        title=title,
        message=message,
        data=str(data) if data else None,
        priority=priority,
    )
    return await crud_create_notification(db, notification)


async def get_user_preferences(db: AsyncSession, user_id: int) -> SimpleNamespace:
    """Return a simple object with preference attributes used by tasks.

    The object will have at least: in_app_enabled, email_enabled,
    digest_enabled, digest_threshold.
    """
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    prefs = result.scalars().first()

    if prefs is None:
        # Defaults
        return SimpleNamespace(
            in_app_enabled=True,
            email_enabled=True,
            digest_enabled=False,
            digest_threshold=5,
        )

    # Provide attributes expected by tasks
    return SimpleNamespace(
        in_app_enabled=bool(prefs.in_app_enabled),
        email_enabled=bool(prefs.email_enabled),
        digest_enabled=False,
        digest_threshold=5,
    )


async def get_unread_notifications_since(
    db: AsyncSession,
    user_id: int,
    since: Optional[Union[datetime, str]] = None,
) -> List[Notification]:
    """Return unread notifications for a user since `since`.

    Args:
        db: Async SQLAlchemy session.
        user_id: The ID of the user.
        since: A datetime, ISO 8601 string, or None. If None, returns all unread.

    Returns:
        A list of unread Notification objects.
    """
    query = select(Notification).where(
        Notification.user_id == user_id,
        ~Notification.is_read,
    )

    since_dt: Optional[datetime] = None

    if isinstance(since, str):
        try:
            since_dt = datetime.fromisoformat(since)
        except ValueError:
            since_dt = None
    elif isinstance(since, datetime):
        since_dt = since

    if since_dt:
        query = query.where(Notification.created_at >= since_dt)

    result = await db.execute(query)
    return list(result.scalars().all())
