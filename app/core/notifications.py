import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.notification import create_notification
from ..models.notification import NotificationPriority, NotificationType
from ..models.user import User
from ..schemas.notification import NotificationCreate
from .sendgrid_email import SendGridEmailService

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self) -> None:
        self.email_service: SendGridEmailService = SendGridEmailService()
        self.max_concurrent_emails: int = 5
        self.email_batch_delay: float = 0.1

        # Map notification types to email service methods
        self._email_methods = {
            NotificationType.BOOKING_CONFIRMATION: self.email_service.send_booking_confirmation,
            NotificationType.BOOKING_CANCELLATION: self.email_service.send_booking_confirmation,  # Temporary
            NotificationType.EVENT_REMINDER: self.email_service.send_booking_confirmation,  # Temporary
            NotificationType.WAITLIST_NOTIFICATION: self.email_service.send_booking_confirmation,  # Temporary
            NotificationType.PASSWORD_RESET: self.email_service.send_booking_confirmation,  # Temporary
            NotificationType.WELCOME: self.email_service.send_booking_confirmation,  # Temporary
        }

    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        try:
            result = await db.execute(select(User).filter(User.id == user_id))
            user: Optional[User] = result.scalars().first()
            return user
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None

    async def get_users_by_ids(
        self, db: AsyncSession, user_ids: List[int]
    ) -> List[User]:
        try:
            result = await db.execute(select(User).filter(User.id.in_(user_ids)))
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get users {user_ids}: {e}")
            return []

    async def send_notification(
        self,
        db: AsyncSession,
        user: Union[int, User],
        notification_type: NotificationType,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        send_email: bool = True,
    ) -> Dict[str, bool]:
        results: Dict[str, bool] = {"in_app": False, "email": False}

        if isinstance(user, int):
            user_obj = await self.get_user_by_id(db, user)
            user_id = user
        else:
            user_obj = user
            user_id = user.id

        if not user_obj:
            send_email = False

        async def create_in_app_notification() -> bool:
            try:
                notification = NotificationCreate(
                    user_id=user_id,
                    type=notification_type,
                    title=title,
                    message=message,
                    data=str(data) if data else None,
                    priority=priority,
                )
                await create_notification(db, notification)
                return True
            except Exception as e:
                logger.error(f"In-app notification failed for {user_id}: {e}")
                return False

        async def send_email_notification() -> bool:
            if not send_email or not user_obj:
                return False
            try:
                return await self._send_email_by_type(
                    notification_type,
                    user_email=user_obj.email,
                    user_name=user_obj.full_name or f"User {user_obj.id}",
                    data=data or {},
                )
            except Exception as e:
                logger.error(f"Email notification failed for {user_obj.email}: {e}")
                return False

        in_app_task = asyncio.create_task(create_in_app_notification())
        email_task = (
            asyncio.create_task(send_email_notification()) if send_email else None
        )

        results["in_app"] = await in_app_task
        if email_task:
            results["email"] = await email_task

        return results

    async def _send_email_by_type(
        self,
        notification_type: NotificationType,
        user_email: str,
        user_name: str,
        data: Dict[str, Any],
    ) -> bool:
        try:
            if notification_type == NotificationType.BOOKING_CONFIRMATION:
                success = await self.email_service.send_booking_confirmation(
                    user_email=user_email, user_name=user_name, booking_data=data
                )
                return bool(success)
            elif notification_type == NotificationType.BOOKING_CANCELLATION:
                success = await self.email_service.send_booking_confirmation(  # Use confirmation for now
                    user_email=user_email, user_name=user_name, booking_data=data
                )
                return bool(success)
            elif notification_type == NotificationType.EVENT_REMINDER:
                # Temporarily use booking confirmation until proper method is implemented
                success = await self.email_service.send_booking_confirmation(
                    user_email=user_email,
                    user_name=user_name,
                    booking_data={
                        **data,
                        "hours_until_event": data.get("hours_until_event", 24),
                    },
                )
                return bool(success)
            elif notification_type == NotificationType.WAITLIST_NOTIFICATION:
                # Temporarily use booking confirmation until proper method is implemented
                success = await self.email_service.send_booking_confirmation(
                    user_email=user_email,
                    user_name=user_name,
                    booking_data={
                        **data,
                        "event_data": data.get("event_data", {}),
                        "available_tickets": data.get("available_tickets", 1),
                    },
                )
                return bool(success)
            elif notification_type == NotificationType.PASSWORD_RESET:
                # Temporarily use booking confirmation until proper method is implemented
                success = await self.email_service.send_booking_confirmation(
                    user_email=user_email,
                    user_name=user_name,
                    booking_data={"reset_token": data.get("reset_token", "")},
                )
                return bool(success)
            elif notification_type == NotificationType.WELCOME:
                # Temporarily use booking confirmation until proper method is implemented
                success = await self.email_service.send_booking_confirmation(
                    user_email=user_email,
                    user_name=user_name,
                    booking_data={},
                )
                return bool(success)
            else:
                return True
        except Exception as e:
            logger.error(f"Failed to send email for {notification_type}: {e}")
            return False

    async def send_bulk_notifications(
        self,
        db: AsyncSession,
        notification_type: NotificationType,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        send_email: bool = True,
        users: Optional[Union[List[int], List[User], List[Dict[str, Any]]]] = None,
        user_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, int]:
        user_objects: List[User] = []
        # Accept either `users` (ids, User objects, or dicts) or `user_data` (list of dicts with user info)
        if users is None and not user_data:
            return {
                "total": 0,
                "in_app_success": 0,
                "in_app_failed": 0,
                "email_success": 0,
                "email_failed": 0,
            }
        if users is not None and len(users) == 0:
            return {
                "total": 0,
                "in_app_success": 0,
                "in_app_failed": 0,
                "email_success": 0,
                "email_failed": 0,
            }
        # Build user_objects from users or user_data
        if users is not None:
            first_user = users[0]
            if isinstance(first_user, int):
                user_objects = await self.get_users_by_ids(db, cast(List[int], users))
            elif isinstance(first_user, User):
                user_objects = cast(List[User], users)
            elif isinstance(first_user, dict):
                user_ids = [u["user_id"] for u in cast(List[Dict[str, Any]], users)]
                user_objects = await self.get_users_by_ids(db, user_ids)
        else:
            # user_data provided as list of dicts with user_id/email/name
            ids = [u.get("user_id") for u in user_data or []]
            # Filter out None and ensure list[int] for get_users_by_ids
            ids_filtered: List[int] = [int(i) for i in ids if i is not None]
            user_objects = await self.get_users_by_ids(db, ids_filtered)

        results = {
            "total": len(user_objects),
            "in_app_success": 0,
            "in_app_failed": 0,
            "email_success": 0,
            "email_failed": 0,
        }

        batch_size = min(self.max_concurrent_emails, len(user_objects))

        async def process_user_notification(user: User) -> Dict[str, bool]:
            try:
                return await self.send_notification(
                    db=db,
                    user=user,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    data=data,
                    priority=priority,
                    send_email=send_email,
                )
            except Exception as e:
                logger.error(f"Notification failed for {user.id}: {e}")
                return {"in_app": False, "email": False}

        for i in range(0, len(user_objects), batch_size):
            batch = user_objects[i : i + batch_size]
            tasks = [process_user_notification(user) for user in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in batch_results:
                if isinstance(result, Exception):
                    results["in_app_failed"] += 1
                    if send_email:
                        results["email_failed"] += 1
                elif isinstance(result, dict):
                    results[
                        "in_app_success" if result.get("in_app") else "in_app_failed"
                    ] += 1
                    if send_email:
                        results[
                            "email_success" if result.get("email") else "email_failed"
                        ] += 1
            if i + batch_size < len(user_objects):
                await asyncio.sleep(self.email_batch_delay)

        return results

    async def send_notification_to_role(
        self,
        db: AsyncSession,
        role: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        send_email: bool = True,
    ) -> Dict[str, int]:
        try:
            from ..models.user import UserRole

            role_enum = getattr(UserRole, role.upper(), None)
            if not role_enum:
                return {
                    "total": 0,
                    "in_app_success": 0,
                    "in_app_failed": 0,
                    "email_success": 0,
                    "email_failed": 0,
                }

            result = await db.execute(select(User).filter(User.role == role_enum))
            users_list = list(result.scalars().all())
            if not users_list:
                return {
                    "total": 0,
                    "in_app_success": 0,
                    "in_app_failed": 0,
                    "email_success": 0,
                    "email_failed": 0,
                }

            return await self.send_bulk_notifications(
                db=db,
                users=users_list,
                notification_type=notification_type,
                title=title,
                message=message,
                data=data,
                priority=priority,
                send_email=send_email,
            )
        except Exception as e:
            logger.error(f"Failed to send notifications to role {role}: {e}")
            return {
                "total": 0,
                "in_app_success": 0,
                "in_app_failed": 0,
                "email_success": 0,
                "email_failed": 0,
            }

    async def process_email_queue(
        self, db: AsyncSession, batch_size: int = 10
    ) -> Dict[str, Any]:
        try:
            # placeholder
            return {"processed": 0, "failed": 0, "status": "completed"}
        except Exception as e:
            return {
                "processed": 0,
                "failed": batch_size,
                "status": "failed",
                "error": str(e),
            }


notification_service = NotificationService()
