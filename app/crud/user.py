from typing import Any, Dict, Optional, Union

from sqlalchemy.orm import Session

from ..core.security import get_password_hash, verify_password
from .. import models, schemas


def get(db: Session, id: Any) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == id).first()


def get_by_email(db: Session, *, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def create(db: Session, *, obj_in: schemas.UserCreate) -> models.User:
    db_obj = models.User(
        email=obj_in.email,
        hashed_password=get_password_hash(obj_in.password),
        is_superuser=obj_in.is_superuser,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def authenticate(
    db: Session, *, email: str, password: str
) -> Optional[models.User]:
    user = get_by_email(db, email=email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def is_active(user: models.User) -> bool:
    return user.is_active


def is_superuser(user: models.User) -> bool:
    return user.is_superuser
