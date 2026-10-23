from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, Literal


UserRole = Literal["patient", "doctor", "admin"]


class UserBase(BaseModel):
    email: EmailStr
    role: UserRole
    full_name: str = Field(..., min_length=2, max_length=100)
    is_active: bool = True
    # Phase 6c: login lockout state (never exposed via API responses).
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserInDB(UserBase):
    id: str
    hashed_password: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class User(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
