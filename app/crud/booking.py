from sqlalchemy.orm import Session
from .. import models, schemas
from . import event as crud_event
from datetime import datetime

def get_booking(db: Session, booking_id: int):
    return db.query(models.Booking).filter(models.Booking.id == booking_id).first()

def get_bookings(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Booking).offset(skip).limit(limit).all()

def create_booking(db: Session, booking: schemas.BookingCreate, user_id: int):
    db.begin_nested()
    try:
        db_event = db.query(models.Event).filter(models.Event.id == booking.event_id).with_for_update().one()

        if db_event.available_tickets >= booking.number_of_tickets:
            db_event.available_tickets -= booking.number_of_tickets
            db_booking = models.Booking(
                **booking.dict(),
                user_id=user_id,
                booked_at=datetime.utcnow(),
                status="confirmed"
            )
            db.add(db_booking)
            db.commit()
            db.refresh(db_booking)
            return db_booking
        else:
            db.rollback()
            return None
    except Exception as e:
        db.rollback()
        raise e

def cancel_booking(db: Session, booking_id: int):
    db_booking = get_booking(db, booking_id)
    if db_booking:
        db_event = crud_event.get_event(db, db_booking.event_id)
        db_event.available_tickets += db_booking.number_of_tickets
        db_booking.status = "cancelled"
        db.commit()
        db.refresh(db_booking)
    return db_booking
