"""Cleanup utilities."""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def cleanup_old_notifications(
    db: AsyncSession, days: Optional[int] = 30
) -> int:
    """Delete notifications older than the specified number of days."""
    if days is None:
        days = 30

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Delete notifications that are read and older than the cutoff date
    result = await db.execute(
        delete(Notification).where(
            Notification.is_read == True,
            Notification.created_at < cutoff_date
        )
    )

    await db.commit()
    return result.rowcount
