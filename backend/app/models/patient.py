from pydantic import BaseModel, Field, EmailStr, validator
from datetime import datetime
from typing import Optional


class PatientBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = Field(default=None, pattern=r"^(male|female|other|prefer_not_to_say)$")
    contact_phone: Optional[str] = Field(default=None, pattern=r"^\+?[1-9]\d{1,14}$")
    contact_email: Optional[EmailStr] = None
    address: Optional[str] = Field(default=None, max_length=255)
    emergency_contact_name: Optional[str] = Field(default=None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(default=None, pattern=r"^\+?[1-9]\d{1,14}$")
    blood_group: Optional[str] = Field(default=None, pattern=r"^(A|B|AB|O)[+-]$")
    allergies: list[str] = Field(default_factory=list)
    is_active: bool = True
    # Phase 2d: revocable public emergency-card token (None = revoked/none).
    emergency_token: Optional[str] = None
    # A1: unique readable patient code for lookup
    patient_code: str = ""
    # A2: prescribing permission (ON by default)
    allow_prescriptions: bool = True

    @validator("date_of_birth")
    def validate_dob(cls, v):
        if v and v > datetime.now():
            raise ValueError("Date of birth cannot be in the future")
        return v


class PatientCreate(PatientBase):
    user_id: Optional[str] = None


class PatientUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = Field(None, pattern=r"^(male|female|other|prefer_not_to_say)$")
    contact_phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    contact_email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, max_length=255)
    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    blood_group: Optional[str] = Field(None, pattern=r"^(A|B|AB|O)[+-]$")
    allergies: Optional[list[str]] = None
    is_active: Optional[bool] = None
    allow_prescriptions: Optional[bool] = None


class PatientInDB(PatientBase):
    id: str
    user_id: Optional[str] = None
    patient_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Patient(PatientBase):
    id: str
    user_id: Optional[str] = None
    patient_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PatientSearchResult(BaseModel):
    id: str
    patient_id: str = ""
    full_name: str
    patient_code: str
    age: Optional[int] = None

    class Config:
        from_attributes = True
