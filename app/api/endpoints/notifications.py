from typing import Annotated  # <-- Add this
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user, get_current_user, get_db
from app.core.notifications import notification_service
from app.crud.notification import create_bulk
from app.crud.notification import delete_notification as delete_notification_crud
from app.crud.notification import get_notification as get_notification_crud
from app.crud.notification import (
    get_user_notifications,
    get_user_stats,
    mark_all_read,
    mark_read,
)
from app.models.notification import NotificationPriority, NotificationType
from app.models.user import User
from app.schemas.notification import Notification

router = APIRouter()


@router.get("/", response_model=List[Notification])  # type: ignore[misc]
async def get_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    notification_types: Optional[List[NotificationType]] = Query(None),
    priority: Optional[NotificationPriority] = Query(None),
) -> List[Notification]:
    notifications = await get_user_notifications(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        unread_only=unread_only,
        notification_types=notification_types,
        priority=priority,
    )
    # Convert model objects to schema objects if needed
    return [Notification.model_validate(n) for n in notifications]


@router.get("/{notification_id}", response_model=Notification)  # type: ignore[misc]
async def get_notification(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Notification:
    notification_obj = await get_notification_crud(
        db=db, notification_id=notification_id
    )
    from app import crud

    if not notification_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )
    if notification_obj.user_id != current_user.id and not crud.user.is_admin(
        current_user
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    validated = Notification.model_validate(notification_obj)
    if not isinstance(validated, Notification):
        raise TypeError("Validated object is not of type Notification")
    return validated


@router.put("/{notification_id}/mark-read")  # type: ignore[misc]
async def mark_notification_read(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    notification_obj = await get_notification_crud(
        db=db, notification_id=notification_id
    )
    if not notification_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )
    if notification_obj.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    updated_notification = await mark_read(db=db, notification_id=notification_id)
    return {
        "message": "Notification marked as read",
        "notification": (
            Notification.model_validate(updated_notification)
            if updated_notification
            else None
        ),
    }


@router.put("/mark-all-read")  # type: ignore[misc]
async def mark_all_notifications_read(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    marked_count = await mark_all_read(db=db, user_id=current_user.id)
    return {"message": f"Marked {marked_count} notifications as read"}


@router.delete("/{notification_id}")  # type: ignore[misc]
async def delete_notification(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    notification_obj = await get_notification_crud(
        db=db, notification_id=notification_id
    )
    if not notification_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )
    if notification_obj.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    deleted = await delete_notification_crud(db=db, notification_id=notification_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete notification",
        )
    return {"message": "Notification deleted successfully"}


@router.get("/stats/summary")  # type: ignore[misc]
async def get_notification_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    return await get_user_stats(db=db, user_id=current_user.id)


@router.post("/admin/send-notification")  # type: ignore[misc]
async def send_comprehensive_notification(
    user_id: int,
    notification_type: NotificationType,
    title: str,
    message: str,
    _: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    data: Optional[dict] = None,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    send_email: bool = True,
) -> dict[str, Any]:
    from app.crud.user import get_user

    target_user = await get_user(db, user_id=user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    results = await notification_service.send_notification(
        db=db,
        user=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        data=data,
        priority=priority,
        send_email=send_email,
    )
    return {
        "message": "Notification sent",
        "results": results,
        "user": {
            "id": target_user.id,
            "email": target_user.email,
            "name": target_user.full_name,
        },
    }


@router.post("/admin/send-bulk")  # type: ignore[misc]
async def send_bulk_notifications(
    user_ids: List[int],
    notification_type: NotificationType,
    title: str,
    message: str,
    _: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    data: Optional[dict] = None,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    send_email: bool = True,
) -> dict[str, Any]:
    from app.crud.user import get_users_by_ids

    users = await get_users_by_ids(db, user_ids=user_ids)
    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No valid users found"
        )
    results = await notification_service.send_bulk_notifications(
        db=db,
        users=users,
        notification_type=notification_type,
        title=title,
        message=message,
        data=data,
        priority=priority,
        send_email=send_email,
    )
    return {
        "message": f"Bulk notifications processed for {len(users)} users",
        "results": results,
        "users_processed": len(users),
        "users_found": len(users),
    }


@router.post("/admin/create-bulk")  # type: ignore[misc]
async def create_bulk_notifications(
    user_ids: List[int],
    notification_type: NotificationType,
    title: str,
    message: str,
    _: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    data: Optional[dict] = None,
    priority: NotificationPriority = NotificationPriority.NORMAL,
) -> dict[str, Any]:
    notifications = await create_bulk(
        db=db,
        user_ids=user_ids,
        notification_type=notification_type,
        title=title,
        message=message,
        data=data,
        priority=priority,
    )
    return {
        "message": f"Created {len(notifications)} notifications",
        "notifications": notifications,
    }
