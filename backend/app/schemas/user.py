from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from app.models.user import User


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "doctor@example.com",
                "password": "securepass123",
                "full_name": "Dr. John Smith",
                "role": "doctor",
            }
        }


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
