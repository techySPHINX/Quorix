"""
Production-ready Celery tasks for email notifications and background processing.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud
from .celery_app import celery_app
from .core.email import email_service
from .database import async_session_maker

logger = logging.getLogger(__name__)


async def get_async_db() -> AsyncSession:
    """Get async database session."""
    async with async_session_maker() as session:
        return session


def run_async(coro):
    """Helper to run async functions in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(
    bind=True,
    queue="email",
    rate_limit="10/m",  # Rate limit for email sending
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def send_booking_confirmation_email(self, user_id: int, booking_id: int):
    """
    Send booking confirmation email with comprehensive details.

    Args:
        user_id: ID of the user who made the booking
        booking_id: ID of the booking
    """

    async def _send_email():
        try:
            async with async_session_maker() as db:
                # Get booking with user and event details
                booking = await crud.booking.get_booking(db, booking_id)
                if not booking:
                    logger.error(f"Booking {booking_id} not found")
                    return False

                user = await crud.user.get_user(db, user_id)
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
                success = await email_service.send_booking_confirmation(
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
)
def send_booking_cancellation_email(self, user_id: int, booking_id: int):
    """
    Send booking cancellation email with refund information.

    Args:
        user_id: ID of the user who cancelled the booking
        booking_id: ID of the cancelled booking
    """

    async def _send_email():
        try:
            async with async_session_maker() as db:
                booking = await crud.booking.get_booking(db, booking_id)
                if not booking:
                    logger.error(f"Booking {booking_id} not found")
                    return False

                user = await crud.user.get_user(db, user_id)
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

                success = await email_service.send_booking_cancellation(
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
)
def send_waitlist_notification_email(
    self, user_id: int, event_id: int, available_tickets: int
):
    """
    Send waitlist notification email when tickets become available.

    Args:
        user_id: ID of the waitlisted user
        event_id: ID of the event
        available_tickets: Number of available tickets
    """

    async def _send_email():
        try:
            async with async_session_maker() as db:
                user = await crud.user.get_user(db, user_id)
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

                success = await email_service.send_waitlist_notification(
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
)
def send_event_reminder_emails(self, event_id: int, hours_before: int = 24):
    """
    Send event reminder emails to all confirmed attendees.

    Args:
        event_id: ID of the event
        hours_before: Hours before event to send reminder
    """

    async def _send_reminders():
        try:
            async with async_session_maker() as db:
                event = await crud.event.get_event(db, event_id)
                if not event:
                    logger.error(f"Event {event_id} not found")
                    return 0

                # Get all confirmed bookings for the event
                bookings = await crud.booking.get_event_bookings(db, event_id)
                confirmed_bookings = [b for b in bookings if b.status == "confirmed"]

                sent_count = 0

                for booking in confirmed_bookings:
                    user = await crud.user.get_user(db, booking.user_id)
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
        return run_async(_send_reminders())
    except Exception as exc:
        logger.error(f"Task send_event_reminder_emails failed: {exc}")
        raise self.retry(exc=exc, countdown=300, max_retries=2)


@celery_app.task(
    bind=True,
    queue="notifications",
    rate_limit="30/m",
    max_retries=3,
)
def notify_waitlist_users(self, event_id: int, available_tickets: int):
    """
    Notify waitlist users when tickets become available and trigger email notifications.

    Args:
        event_id: ID of the event
        available_tickets: Number of available tickets
    """

    async def _notify_users():
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
        return run_async(_notify_users())
    except Exception as exc:
        logger.error(f"Task notify_waitlist_users failed: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(queue="notifications")
def schedule_event_reminders():
    """
    Periodic task to schedule event reminders.
    Should be run by celery beat every hour.
    """

    async def _schedule_reminders():
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
                return scheduled_count

        except Exception as e:
            logger.error(f"Error scheduling event reminders: {e}")
            return 0

    return run_async(_schedule_reminders())


# Health check task
@celery_app.task(queue="notifications")
def health_check():
    """Simple health check task for monitoring."""
    logger.info("Celery health check completed successfully")
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "worker": "evently-worker",
    }
