from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.doctor import Doctor


class DoctorCreate(BaseModel):
    full_name: str
    specialization: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    license_number: Optional[str] = None


class DoctorUpdate(BaseModel):
    full_name: Optional[str] = None
    specialization: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    license_number: Optional[str] = None
    is_active: Optional[bool] = None


class DoctorResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    doctor_id: Optional[str] = None
    full_name: str
    specialization: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    license_number: Optional[str] = None
    is_verified: bool = False
    verification_status: str = "pending"
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
