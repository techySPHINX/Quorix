import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Coroutine, Dict, List, Optional, TypeVar

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud
from .celery_app import celery_app
from .core.sendgrid_email import email_service
from .database import async_session_maker

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


async def get_async_db() -> AsyncSession:
    """Get async database session."""
    async with async_session_maker() as session:
        return session


T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Helper to run async functions in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(  # type: ignore[misc]
    bind=True,
    queue="email",
    rate_limit="10/m",  # Rate limit for email sending
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def send_booking_confirmation_email(self: Any, user_id: int, booking_id: int) -> bool:
    """
    Send booking confirmation email with comprehensive details.

    Args:
        user_id: ID of the user who made the booking
        booking_id: ID of the booking
    """

    async def _send_email() -> bool:
        try:
            async with async_session_maker() as db:
                # Get booking with user and event details
                booking = await crud.booking.get_booking(db, booking_id)
                if not booking:
                    logger.error(f"Booking {booking_id} not found")
                    return False

                user = await crud.user.get_user(db, user_id=user_id)
                if not user:
                    logger.error(f"User {user_id} not found")
                    return False

                event = await crud.event.get_event(db, booking.event_id)
                if not event:
                    logger.error(f"Event {booking.event_id} not found")
                    return False

                # Prepare booking data for email template
                booking_data = {
                    "id": booking.id,
                    "event_name": event.name,
                    "event_date": event.start_date,
                    "event_location": event.location,
                    "number_of_tickets": booking.number_of_tickets,
                    "total_price": event.price * booking.number_of_tickets,
                    "booked_at": booking.booked_at,
                }

                # Send confirmation email
                success: bool = await email_service.send_booking_confirmation(
                    user_email=user.email,
                    user_name=user.full_name or user.email,
                    booking_data=booking_data,
                )

                if success:
                    logger.info(
                        f"Booking confirmation email sent to {user.email} for booking {booking_id}"
                    )
                else:
                    logger.error(
                        f"Failed to send booking confirmation email to {user.email}"
                    )
                    raise Exception("Email sending failed")

                return success

        except Exception as e:
            logger.error(f"Error sending booking confirmation email: {e}")
            raise

    try:
        return run_async(_send_email())
    except Exception as exc:
        logger.error(f"Task send_booking_confirmation_email failed: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(
    bind=True,
    queue="email",
    rate_limit="10/m",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)  # type: ignore[misc]
def send_booking_cancellation_email(self: Any, user_id: int, booking_id: int) -> bool:
    """
    Send booking cancellation email with refund information.

    Args:
        user_id: ID of the user who cancelled the booking
        booking_id: ID of the cancelled booking
    """

    async def _send_email() -> bool:
        try:
            async with async_session_maker() as db:
                booking = await crud.booking.get_booking(db, booking_id)
                if not booking:
                    logger.error(f"Booking {booking_id} not found")
                    return False

                user = await crud.user.get_user(db, user_id=user_id)
                if not user:
                    logger.error(f"User {user_id} not found")
                    return False

                event = await crud.event.get_event(db, booking.event_id)
                if not event:
                    logger.error(f"Event {booking.event_id} not found")
                    return False

                # Prepare cancellation data
                booking_data = {
                    "id": booking.id,
                    "event_name": event.name,
                    "event_date": event.start_date,
                    "cancelled_at": datetime.utcnow(),
                    "refund_info": "Refund will be processed to your original payment method within 5-7 business days.",
                }

                success: bool = await email_service.send_booking_cancellation(
                    user_email=user.email,
                    user_name=user.full_name or user.email,
                    booking_data=booking_data,
                )

                if success:
                    logger.info(
                        f"Booking cancellation email sent to {user.email} for booking {booking_id}"
                    )
                else:
                    logger.error(
                        f"Failed to send booking cancellation email to {user.email}"
                    )
                    raise Exception("Email sending failed")

                return success

        except Exception as e:
            logger.error(f"Error sending booking cancellation email: {e}")
            raise

    try:
        return run_async(_send_email())
    except Exception as exc:
        logger.error(f"Task send_booking_cancellation_email failed: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(
    bind=True,
    queue="notifications",
    rate_limit="20/m",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
)  # type: ignore[misc]
def send_waitlist_notification_email(
    self: Any, user_id: int, event_id: int, available_tickets: int
) -> bool:
    """
    Send waitlist notification email when tickets become available.

    Args:
        user_id: ID of the waitlisted user
        event_id: ID of the event
        available_tickets: Number of available tickets
    """

    async def _send_email() -> bool:
        try:
            async with async_session_maker() as db:
                user = await crud.user.get_user(db, user_id=user_id)
                if not user:
                    logger.error(f"User {user_id} not found")
                    return False

                event = await crud.event.get_event(db, event_id)
                if not event:
                    logger.error(f"Event {event_id} not found")
                    return False

                event_data = {
                    "id": event.id,
                    "name": event.name,
                    "start_date": event.start_date,
                    "location": event.location,
                    "booking_deadline": "24 hours",
                }

                success: bool = await email_service.send_waitlist_notification(
                    user_email=user.email,
                    user_name=user.full_name or user.email,
                    event_data=event_data,
                    available_tickets=available_tickets,
                )

                if success:
                    logger.info(
                        f"Waitlist notification email sent to {user.email} for event {event_id}"
                    )
                else:
                    logger.error(
                        f"Failed to send waitlist notification email to {user.email}"
                    )
                    raise Exception("Email sending failed")

                return success

        except Exception as e:
            logger.error(f"Error sending waitlist notification email: {e}")
            raise

    try:
        return run_async(_send_email())
    except Exception as exc:
        logger.error(f"Task send_waitlist_notification_email failed: {exc}")
        raise self.retry(exc=exc, countdown=30, max_retries=3)


@celery_app.task(
    bind=True,
    queue="notifications",
    rate_limit="5/m",
    max_retries=2,
    default_retry_delay=300,
)  # type: ignore[misc]
def send_event_reminder_emails(self: Any, event_id: int, hours_before: int = 24) -> int:
    """
    Send event reminder emails to all confirmed attendees.

    Args:
        event_id: ID of the event
        hours_before: Hours before event to send reminder
    """

    async def _send_reminders() -> int:
        try:
            async with async_session_maker() as db:
                event = await crud.event.get_event(db, event_id)
                if not event:
                    logger.error(f"Event {event_id} not found")
                    return 0

                # Get all confirmed bookings for the event
                from sqlalchemy import select

                from app.models.booking import Booking, BookingStatus

                result = await db.execute(
                    select(Booking).filter(
                        Booking.event_id == event_id,
                        Booking.status == BookingStatus.CONFIRMED,
                    )
                )
                confirmed_bookings = result.scalars().all()

                sent_count = 0

                for booking in confirmed_bookings:
                    user = await crud.user.get_user(db, user_id=booking.user_id)
                    if not user:
                        continue

                    booking_data = {
                        "id": booking.id,
                        "event_name": event.name,
                        "event_date": event.start_date,
                        "event_location": event.location,
                        "number_of_tickets": booking.number_of_tickets,
                    }

                    success = await email_service.send_event_reminder(
                        user_email=user.email,
                        user_name=user.full_name or user.email,
                        booking_data=booking_data,
                        hours_until_event=hours_before,
                    )

                    if success:
                        sent_count += 1
                        logger.info(
                            f"Event reminder sent to {user.email} for event {event_id}"
                        )

                logger.info(f"Sent {sent_count} event reminders for event {event_id}")
                return sent_count

        except Exception as e:
            logger.error(f"Error sending event reminder emails: {e}")
            raise

    try:
        result = run_async(_send_reminders())
        return int(result)
    except Exception as exc:
        logger.error(f"Task send_event_reminder_emails failed: {exc}")
        raise self.retry(exc=exc, countdown=300, max_retries=2)


@celery_app.task(
    bind=True,
    queue="notifications",
    rate_limit="30/m",
    max_retries=3,
)  # type: ignore[misc]
def notify_waitlist_users(self: Any, event_id: int, available_tickets: int) -> int:
    """
    Notify waitlist users when tickets become available and trigger email notifications.

    Args:
        event_id: ID of the event
        available_tickets: Number of available tickets
    """

    async def _notify_users() -> int:
        try:
            async with async_session_maker() as db:
                # Get waitlist users and notify them
                notified_users = await crud.waitlist.notify_waitlist_users(
                    db, event_id, available_tickets
                )

                # Send email notifications to notified users
                for waitlist_entry in notified_users:
                    send_waitlist_notification_email.delay(
                        user_id=waitlist_entry.user_id,
                        event_id=event_id,
                        available_tickets=waitlist_entry.number_of_tickets,
                    )

                logger.info(
                    f"Notified {len(notified_users)} waitlist users for event {event_id}"
                )
                return len(notified_users)

        except Exception as e:
            logger.error(f"Error notifying waitlist users: {e}")
            raise

    try:
        result = run_async(_notify_users())
        return int(result)
    except Exception as exc:
        logger.error(f"Task notify_waitlist_users failed: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(queue="notifications")  # type: ignore[misc]
def schedule_event_reminders() -> None:
    """
    Periodic task to schedule event reminders.
    Should be run by celery beat every hour.
    """

    async def _schedule_reminders() -> None:
        try:
            async with async_session_maker() as db:
                # Find events that need reminders (24 hours before start)
                tomorrow = datetime.utcnow() + timedelta(hours=24)
                start_time = tomorrow.replace(minute=0, second=0, microsecond=0)
                end_time = start_time + timedelta(hours=1)

                # Get events starting in approximately 24 hours
                events_query = await db.execute(
                    text(
                        """
                        SELECT id FROM events
                        WHERE start_date BETWEEN :start_time AND :end_time
                    """
                    ),
                    {"start_time": start_time, "end_time": end_time},
                )
                events = events_query.fetchall()

                scheduled_count = 0
                for event in events:
                    send_event_reminder_emails.delay(event.id, 24)
                    scheduled_count += 1

                logger.info(f"Scheduled {scheduled_count} event reminder tasks")

        except Exception as e:
            logger.error(f"Error scheduling event reminders: {e}")
            # Intentionally no return; outer function returns None

    run_async(_schedule_reminders())


# Health check task
@celery_app.task(queue="notifications")  # type: ignore[misc]
def health_check() -> str:
    """Simple health check task for monitoring."""
    logger.info("Celery health check completed successfully")
    return "healthy"


# Notification processing tasks
@celery_app.task(
    bind=True,
    queue="email",
    rate_limit="20/m",  # Rate limit for email processing
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)  # type: ignore[misc]
def process_notification_email_queue(self: Any, batch_size: int = 50) -> Dict[str, Any]:
    """
    Process pending email notification deliveries.

    Args:
        batch_size: Number of emails to process in this batch
    """

    async def _process_queue() -> Dict[str, Any]:
        try:
            from .core.notifications import notification_service
            from .database import async_session_maker

            async with async_session_maker() as db:
                result: Dict[str, Any] = await notification_service.process_email_queue(
                    db=db, batch_size=batch_size
                )

                logger.info(f"Email queue processing result: {result}")
                return result

        except Exception as e:
            logger.error(f"Error processing email queue: {e}")
            raise

    # Return the full result dict so callers can inspect fields like 'processed'
    return run_async(_process_queue())


@celery_app.task(
    bind=True,
    queue="notifications",
    rate_limit="5/m",
)  # type: ignore[misc]
def send_bulk_notifications(
    self: Any,
    user_ids: List[int],
    notification_type: str,
    title: str,
    message: str,
    data: Optional[Dict[Any, Any]] = None,
    priority: str = "normal",
    send_email: bool = True,
    email_template: Optional[str] = None,
) -> Dict[str, int]:
    """
    Send bulk notifications to multiple users.

    Args:
        user_ids: List of user IDs to notify
        notification_type: Type of notification
        title: Notification title
        message: Notification message
        data: Additional notification data
        priority: Notification priority
        send_email: Whether to send email notifications
        email_template: Email template to use
    """

    async def _send_bulk() -> Dict[str, int]:
        try:
            from .core.notifications import notification_service
            from .crud.user import get_users_by_ids
            from .database import async_session_maker
            from .models.notification import NotificationPriority, NotificationType

            async with async_session_maker() as db:
                # Convert string enums back to enum objects
                notification_type_enum = NotificationType(notification_type)
                priority_enum = NotificationPriority(priority)

                # Get user details for email sending
                users = await get_users_by_ids(db, user_ids=user_ids)
                user_data = [
                    {"user_id": user.id, "email": user.email, "name": user.full_name}
                    for user in users
                ]

                result: Dict[str, int] = (
                    await notification_service.send_bulk_notifications(
                        db=db,
                        user_data=user_data,
                        notification_type=notification_type_enum,
                        title=title,
                        message=message,
                        data=data,
                        priority=priority_enum,
                        send_email=send_email,
                    )
                )

                logger.info(f"Bulk notification result: {result}")
                return result

        except Exception as e:
            logger.error(f"Error sending bulk notifications: {e}")
            raise

    return run_async(_send_bulk())


# Periodic task to process email queue
@celery_app.task(queue="email")  # type: ignore[misc]
def periodic_email_queue_processing() -> None:
    """Periodic task to process email queue - called by celery beat"""
    logger.info("Starting periodic email queue processing")

    # Process in smaller batches to avoid overwhelming the email service
    batch_size = 25
    total_processed = 0

    # Process multiple batches if needed
    for batch_num in range(5):  # Maximum 5 batches per run
        result = process_notification_email_queue.delay(batch_size)
        try:
            batch_result = result.get(timeout=300)  # 5 minute timeout
            if batch_result and batch_result.get("processed", 0) > 0:
                total_processed += batch_result["processed"]
                logger.info(
                    f"Batch {batch_num + 1} processed {batch_result['processed']} emails"
                )
            else:
                # No more emails to process
                break
        except Exception as e:
            logger.error(f"Error in batch {batch_num + 1}: {e}")
            break

    logger.info(
        f"Periodic email processing completed. Total processed: {total_processed}"
    )
    # No return value expected


@celery_app.task(queue="notifications")  # type: ignore[misc]
def cleanup_old_notifications() -> None:
    """Periodic task to clean up old notifications"""

    async def _cleanup() -> None:
        try:
            from app.crud import notification_crud as notification_crud

            from .database import async_session_maker

            async with async_session_maker() as db:
                # Keep notifications for 90 days
                deleted_count = await notification_crud.cleanup_old_notifications(
                    db=db, days_to_keep=90
                )

                logger.info(f"Cleaned up {deleted_count} old notifications")
                # No return; outer function returns None

        except Exception as e:
            logger.error(f"Error cleaning up notifications: {e}")
            # No return; outer function returns None

    run_async(_cleanup())


@celery_app.task(
    bind=True,
    queue="notifications",
    rate_limit="50/m",
    max_retries=3,
    default_retry_delay=30,
)  # type: ignore[misc]
def process_in_app_notification(self: Any, notification_data: dict) -> None:
    """
    Process and create in-app notifications for users.

    Args:
        notification_data: Dict containing notification details
    """

    async def _create_notification() -> None:
        try:
            from app.crud import notification_crud as notification_crud

            from .database import async_session_maker
            from .models.notification import NotificationPriority, NotificationType

            async with async_session_maker() as db:
                # Create in-app notification
                notification = await notification_crud.create_notification(
                    db=db,
                    user_id=notification_data["user_id"],
                    title=notification_data["title"],
                    message=notification_data["message"],
                    notification_type=NotificationType(notification_data["type"]),
                    priority=NotificationPriority(
                        notification_data.get("priority", "normal")
                    ),
                    data=notification_data.get("data", {}),
                )

                logger.info(
                    f"Created in-app notification {notification.id} for user {notification_data['user_id']}"
                )

        except Exception as e:
            logger.error(f"Error creating in-app notification: {e}")
            raise

    try:
        run_async(_create_notification())
    except Exception as exc:
        logger.error(f"Task process_in_app_notification failed: {exc}")
        raise self.retry(exc=exc, countdown=30, max_retries=3)


@celery_app.task(
    bind=True,
    queue="notifications",
    rate_limit="20/m",
    max_retries=3,
    default_retry_delay=60,
)  # type: ignore[misc]
def process_bulk_notifications(self: Any, notification_batch: list) -> None:
    """
    Process multiple notifications in batch for efficiency.

    Args:
        notification_batch: List of notification data dictionaries
    """

    async def _process_batch() -> None:
        try:
            from app.crud import notification_crud as notification_crud

            from .database import async_session_maker

            async with async_session_maker() as db:
                created_notifications = []

                for notification_data in notification_batch:
                    try:
                        notification = await notification_crud.create_notification(
                            db=db,
                            user_id=notification_data["user_id"],
                            title=notification_data["title"],
                            message=notification_data["message"],
                            notification_type=notification_data["type"],
                            priority=notification_data.get("priority", "normal"),
                            data=notification_data.get("data", {}),
                        )
                        created_notifications.append(notification.id)

                    except Exception as e:
                        logger.error(
                            f"Failed to create notification for user {notification_data['user_id']}: {e}"
                        )
                        continue

                logger.info(
                    f"Created {len(created_notifications)} notifications in batch"
                )

        except Exception as e:
            logger.error(f"Error processing notification batch: {e}")
            raise

    try:
        run_async(_process_batch())
    except Exception as exc:
        logger.error(f"Task process_bulk_notifications failed: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(
    bind=True,
    queue="notifications",
    rate_limit="10/m",
    max_retries=2,
)  # type: ignore[misc]
def send_combined_notification(
    self: Any, user_id: int, notification_type: str, data: dict
) -> None:
    """
    Send both in-app and email notification combined.

    Args:
        user_id: ID of the user to notify
        notification_type: Type of notification (booking_confirmation, etc.)
        data: Additional data for the notification
    """

    async def _send_combined() -> None:
        try:
            from app.crud import notification_crud as notification_crud

            from .database import async_session_maker

            async with async_session_maker() as db:
                # Get user preferences
                user = await crud.user.get_user(db, user_id=user_id)
                if not user:
                    logger.error(f"User {user_id} not found")
                    return

                preferences = await notification_crud.get_user_preferences(db, user_id)

                # Create in-app notification if enabled
                if preferences and preferences.in_app_enabled:
                    await notification_crud.create_notification(
                        db=db,
                        user_id=user_id,
                        title=data["title"],
                        message=data["message"],
                        notification_type=notification_type,
                        priority=data.get("priority", "normal"),
                        data=data.get("extra_data", {}),
                    )
                    logger.info(f"Created in-app notification for user {user_id}")

                # Send email notification if enabled
                if preferences and preferences.email_enabled:
                    # Delegate to appropriate email task based on type
                    if notification_type == "booking_confirmation":
                        send_booking_confirmation_email.delay(
                            user_id, data["booking_id"]
                        )
                    elif notification_type == "booking_cancellation":
                        send_booking_cancellation_email.delay(
                            user_id, data["booking_id"]
                        )
                    elif notification_type == "waitlist_notification":
                        send_waitlist_notification_email.delay(
                            user_id, data["event_id"], data["available_tickets"]
                        )

                    logger.info(f"Queued email notification for user {user_id}")

                # No return; outer function returns None

        except Exception as e:
            logger.error(f"Error sending combined notification: {e}")
            raise

    try:
        run_async(_send_combined())
    except Exception as exc:
        logger.error(f"Task send_combined_notification failed: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=2)


@celery_app.task(queue="notifications")  # type: ignore[misc]
def process_notification_digest() -> None:
    """
    Process daily/weekly notification digest for users.
    Sends summary emails of unread notifications.
    """

    async def _process_digest() -> None:
        try:
            from datetime import timedelta

            from app.crud import notification_crud as notification_crud

            from .crud.user import get_users
            from .database import async_session_maker

            async with async_session_maker() as db:
                # Get users who have unread notifications and digest enabled
                users = await get_users(db)
                digest_count = 0

                for user in users:
                    preferences = await notification_crud.get_user_preferences(
                        db, user.id
                    )

                    if not preferences or not preferences.digest_enabled:
                        continue

                    # Get unread notifications from last 24 hours
                    unread_notifications = (
                        await notification_crud.get_unread_notifications_since(
                            db=db,
                            user_id=user.id,
                            since=datetime.utcnow() - timedelta(hours=24),
                        )
                    )

                    if len(unread_notifications) >= preferences.digest_threshold:
                        # Send digest email
                        digest_data = {
                            "user_name": user.full_name or user.email,
                            "notification_count": len(unread_notifications),
                            "notifications": [
                                {
                                    "title": notif.title,
                                    "message": notif.message,
                                    "created_at": notif.created_at,
                                }
                                # Limit to 10 in digest
                                for notif in unread_notifications[:10]
                            ],
                        }

                        await email_service.send_email(
                            to_email=user.email,
                            subject=f"Daily Digest - {len(unread_notifications)} New Notifications",
                            template_name="notification_digest",
                            context=digest_data,
                        )

                        digest_count += 1
                        logger.info(f"Sent notification digest to {user.email}")

                logger.info(f"Processed {digest_count} notification digests")

        except Exception as e:
            logger.error(f"Error processing notification digest: {e}")
            # No return; outer function returns None

    run_async(_process_digest())


@celery_app.task(
    bind=True,
    queue="notifications",
    rate_limit="5/m",
    max_retries=2,
)  # type: ignore[misc]
def send_system_announcement(self: Any, announcement_data: Dict[str, Any]) -> int:
    """
    Send system-wide announcements to all users or specific user groups.

    Args:
        announcement_data: Dict containing announcement details and targeting
    """

    async def _send_announcement() -> int:
        try:
            from .database import async_session_maker
            from .models.user import UserRole

            async with async_session_maker() as db:
                target_role = announcement_data.get("target_role")

                # Get target users
                if target_role:
                    users = await crud.user.get_users(
                        db, role_filter=UserRole(target_role)
                    )
                else:
                    users = await crud.user.get_users(db)

                # Create notifications for all target users
                notification_batch = []
                for user in users:
                    notification_batch.append(
                        {
                            "user_id": user.id,
                            "title": announcement_data["title"],
                            "message": announcement_data["message"],
                            "type": "system_announcement",
                            "priority": announcement_data.get("priority", "normal"),
                            "data": {
                                "announcement_id": announcement_data.get("id"),
                                "category": announcement_data.get(
                                    "category", "general"
                                ),
                            },
                        }
                    )

                # Process in batches
                batch_size = 50
                for i in range(0, len(notification_batch), batch_size):
                    batch = notification_batch[i : i + batch_size]
                    process_bulk_notifications.delay(batch)

                logger.info(f"Queued system announcement for {len(users)} users")
                return len(users)

        except Exception as e:
            logger.error(f"Error sending system announcement: {e}")
            raise

    try:
        result = run_async(_send_announcement())
        return int(result)
    except Exception as exc:
        logger.error(f"Task send_system_announcement failed: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=2)


@celery_app.task(bind=True, max_retries=2)  # type: ignore[misc]
def send_waitlist_notifications(self: Any, event_id: int) -> None:
    """Notify waitlisted users when spots become available"""
    from sqlalchemy import func

    from app.database import SessionLocal
    from app.models.booking import Booking
    from app.models.event import Event
    from app.models.waitlist import Waitlist

    try:
        db = SessionLocal()

        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            logger.error(f"Event {event_id} not found")
            return

        # Get current availability
        current_bookings = (
            db.query(func.sum(Booking.number_of_tickets))
            .filter(Booking.event_id == event_id, Booking.status == "confirmed")
            .scalar()
            or 0
        )

        available_spots = event.max_attendees - current_bookings

        if available_spots > 0:
            # Get waitlisted users in order
            waitlist_entries = (
                db.query(Waitlist)
                .filter(Waitlist.event_id == event_id, Waitlist.status == "waiting")
                .order_by(Waitlist.created_at)
                .limit(available_spots)
                .all()
            )

            notification_tasks = []
            for entry in waitlist_entries:
                task_data = {
                    "user_id": entry.user_id,
                    "notification_type": "waitlist_notification",
                    "title": f"Spot Available - {event.name}",
                    "message": f"Good news! A spot has opened up for {event.name}. Book now before it's gone!",
                    "data": {
                        "waitlist_id": entry.id,
                        "event_id": event.id,
                        "event_name": event.name,
                        "event_date": event.date.isoformat(),
                        "available_spots": available_spots,
                    },
                    "send_email": True,
                    "email_template": "waitlist_notification",
                    "priority": "high",
                }
                notification_tasks.append(task_data)

                # Update waitlist status
                entry.status = "notified"
                entry.notified_at = datetime.utcnow()

            db.commit()

            # Send notifications in batch
            if notification_tasks:
                process_bulk_notifications.delay(notification_tasks)

        # No return value expected
    except Exception as exc:
        logger.error(f"Failed to send waitlist notifications: {exc}")
        self.retry(countdown=30 * (2**self.request.retries))
    finally:
        db.close()


@celery_app.task  # type: ignore[misc]
def update_notification_stats() -> None:
    """Update notification delivery statistics"""
    from app.database import SessionLocal
    from app.models.user import Notification
    from app.redis import redis_client

    try:
        db = SessionLocal()

        # Calculate stats for the last 24 hours
        since = datetime.utcnow() - timedelta(hours=24)

        stats = {
            "total_sent": db.query(Notification)
            .filter(Notification.created_at >= since)
            .count(),
            "delivered": db.query(Notification)
            .filter(
                Notification.created_at >= since, Notification.status == "delivered"
            )
            .count(),
            "read": db.query(Notification)
            .filter(Notification.created_at >= since, Notification.read_at.isnot(None))
            .count(),
            "failed": db.query(Notification)
            .filter(Notification.created_at >= since, Notification.status == "failed")
            .count(),
        }

        # Store in Redis
        redis_client.hmset("notification_stats:24h", stats)
        redis_client.expire("notification_stats:24h", 86400)  # 24 hours

    except Exception as exc:
        logger.error(f"Failed to update notification stats: {exc}")
    finally:
        db.close()
