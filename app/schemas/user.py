from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole


class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: bool = True
    is_superuser: bool = False
    full_name: Optional[str] = None
    role: Optional[UserRole] = UserRole.USER


# Properties to receive via API on creation
class UserCreate(UserBase):
    email: EmailStr
    password: str
    role: Optional[UserRole] = UserRole.USER


# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None


class UserInDBBase(UserBase):
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class User(UserInDBBase):
    pass


class UserInDB(UserInDBBase):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None


class TokenPayload(BaseModel):
    sub: Optional[int] = None
    role: Optional[str] = None
