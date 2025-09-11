from sqlalchemy.orm import Session
from .. import models
from sqlalchemy import func

def get_booking_statistics(db: Session):
    total_bookings = db.query(func.count(models.Booking.id)).scalar()
    total_revenue = db.query(func.sum(models.Event.price * models.Booking.number_of_tickets)).join(models.Event).scalar()
    return {"total_bookings": total_bookings, "total_revenue": total_revenue}

def get_popular_events(db: Session):
    return (
        db.query(models.Event, func.count(models.Booking.id).label("booking_count"))
        .join(models.Booking)
        .group_by(models.Event)
        .order_by(func.count(models.Booking.id).desc())
        .all()
    )
