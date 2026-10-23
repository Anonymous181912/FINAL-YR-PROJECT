from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.models.prescription import Prescription, PrescriptionItem


class PrescriptionItemCreate(BaseModel):
    medicine_name: str = Field(..., min_length=1, max_length=200)
    dosage: str = Field(..., min_length=1, max_length=100)
    frequency: str = Field(..., min_length=1, max_length=100)
    duration: str = Field(..., min_length=1, max_length=100)
    route: Optional[str] = Field(None, max_length=100)
    instructions: Optional[str] = Field(None, max_length=500)
    quantity: Optional[str] = Field(None, max_length=50)
    timings: Optional[str] = Field(None, max_length=200)


class PrescriptionCreate(BaseModel):
    patient_id: str
    prescription_date: Optional[datetime] = None
    diagnosis_notes: Optional[str] = None
    advice: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    items: list[PrescriptionItemCreate]
    # Phase 2a: required to save/issue when severe warnings exist.
    acknowledge_warnings: bool = False
    ack_reason: Optional[str] = Field(None, max_length=500)


class PrescriptionUpdate(BaseModel):
    prescription_date: Optional[datetime] = None
    diagnosis_notes: Optional[str] = None
    advice: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    items: Optional[list[PrescriptionItemCreate]] = None
    status: Optional[str] = None
    acknowledge_warnings: bool = False
    ack_reason: Optional[str] = Field(None, max_length=500)


class PrescriptionResponse(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    prescription_date: Optional[datetime] = None
    diagnosis_notes: Optional[str] = None
    advice: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    items: list[PrescriptionItem]
    status: str
    file_path: Optional[str] = None
    safety_warnings: list[dict] = []
    acknowledged_warnings: bool = False
    verification_token: Optional[str] = None
    verification_status: str = "valid"
    created_at: datetime
    updated_at: datetime
    issued_at: Optional[datetime] = None

    class Config:
        from_attributes = True
