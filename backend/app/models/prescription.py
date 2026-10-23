from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any


class PrescriptionItem(BaseModel):
    medicine_name: str = Field(..., min_length=1, max_length=200)
    dosage: str = Field(..., min_length=1, max_length=100)
    frequency: str = Field(..., min_length=1, max_length=100)
    duration: str = Field(..., min_length=1, max_length=100)
    route: Optional[str] = Field(None, max_length=100)
    instructions: Optional[str] = Field(None, max_length=500)
    quantity: Optional[str] = Field(None, max_length=50)
    timings: Optional[str] = Field(None, max_length=200)


class PrescriptionBase(BaseModel):
    prescription_date: Optional[datetime] = None
    diagnosis_notes: Optional[str] = Field(None, max_length=2000)
    advice: Optional[str] = Field(None, max_length=2000)
    follow_up_date: Optional[datetime] = None
    items: list[PrescriptionItem] = Field(..., min_length=1)
    status: str = "draft"
    file_path: Optional[str] = None
    # Phase 2a: stored safety flags (educational, not clinical advice).
    safety_warnings: list[dict[str, Any]] = Field(default_factory=list)
    acknowledged_warnings: bool = False
    ack_reason: Optional[str] = Field(None, max_length=500)
    # Phase 2b: QR verification (token is public; hash detects tampering).
    verification_token: Optional[str] = None
    verification_hash: Optional[str] = None
    verification_status: str = Field(default="valid", pattern=r"^(valid|revoked)$")
    revoked_at: Optional[datetime] = None


class PrescriptionCreate(BaseModel):
    patient_id: str
    prescription_date: Optional[datetime] = None
    diagnosis_notes: Optional[str] = Field(None, max_length=2000)
    advice: Optional[str] = Field(None, max_length=2000)
    follow_up_date: Optional[datetime] = None
    items: list[PrescriptionItem] = Field(..., min_length=1)


class PrescriptionUpdate(BaseModel):
    prescription_date: Optional[datetime] = None
    diagnosis_notes: Optional[str] = Field(None, max_length=2000)
    advice: Optional[str] = Field(None, max_length=2000)
    follow_up_date: Optional[datetime] = None
    items: Optional[list[PrescriptionItem]] = None
    status: Optional[str] = None
    file_path: Optional[str] = None


class PrescriptionInDB(PrescriptionBase):
    id: str
    patient_id: str
    doctor_id: str
    created_at: datetime
    updated_at: datetime
    issued_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Prescription(PrescriptionBase):
    id: str
    patient_id: str
    doctor_id: str
    created_at: datetime
    updated_at: datetime
    issued_at: Optional[datetime] = None

    class Config:
        from_attributes = True
