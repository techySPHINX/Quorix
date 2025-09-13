from .celery_app import celery_app
from .redis import redis_client


@celery_app.task(acks_late=True)
def send_booking_confirmation_email(user_id: int, booking_id: int):
    """
    Sends a booking confirmation email and stores a notification in Redis.
    """
    message = f"Booking {booking_id} has been confirmed."
    redis_client.lpush(f"notifications:{user_id}", message)
    print(f"Simulating sending booking confirmation email for booking ID: {booking_id}")


@celery_app.task(acks_late=True)
def send_booking_cancellation_email(user_id: int, booking_id: int):
    """
    Sends a booking cancellation email and stores a notification in Redis.
    """
    message = f"Booking {booking_id} has been cancelled."
    redis_client.lpush(f"notifications:{user_id}", message)
    print(f"Simulating sending booking cancellation email for booking ID: {booking_id}")
