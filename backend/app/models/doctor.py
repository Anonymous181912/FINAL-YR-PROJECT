from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class DoctorBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    specialization: Optional[str] = Field(default=None, max_length=200)
    contact_phone: Optional[str] = Field(default=None, pattern=r"^\+?[1-9]\d{1,14}$")
    contact_email: Optional[str] = None
    license_number: Optional[str] = Field(default=None, max_length=100)
    is_verified: bool = False
    verification_status: str = Field(default="pending", pattern=r"^(pending|approved|rejected)$")
    is_active: bool = True


class DoctorCreate(DoctorBase):
    user_id: Optional[str] = None


class DoctorUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    specialization: Optional[str] = Field(None, max_length=200)
    contact_phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    contact_email: Optional[str] = None
    license_number: Optional[str] = Field(None, max_length=100)
    is_verified: Optional[bool] = None
    verification_status: Optional[str] = Field(None, pattern=r"^(pending|approved|rejected)$")
    is_active: Optional[bool] = None


class DoctorInDB(DoctorBase):
    id: str
    user_id: Optional[str] = None
    doctor_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Doctor(DoctorBase):
    id: str
    user_id: Optional[str] = None
    doctor_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
