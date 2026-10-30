from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Optional
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


class PaperPrescriptionConfirm(BaseModel):
    """Patient-reviewed rows for a paper prescription.

    ``confirmed_by_patient`` must be true: the patient is asserting they
    checked the digitized details against the physical paper.
    """

    temp_upload_id: str = Field(..., min_length=1, max_length=100)
    prescriber_name: Optional[str] = Field(None, max_length=200)
    prescription_date: Optional[datetime] = None
    note: Optional[str] = Field(None, max_length=2000)
    items: list[PrescriptionItemCreate] = Field(..., min_length=1)
    confirmed_by_patient: bool = False


class PaperPrescriptionScanItem(BaseModel):
    medicine_name: str = ""
    dosage: str = ""
    frequency: str = ""
    duration: str = ""
    instructions: str = ""
    route: Optional[str] = None
    confidence: float = 0.0
    needs_review: bool = True


class PaperPrescriptionScanResponse(BaseModel):
    temp_upload_id: str
    original_filename: Optional[str] = None
    ocr_used: bool = False
    raw_text: str = ""
    items: list[PaperPrescriptionScanItem] = Field(default_factory=list)
    detected_doctor_name: Optional[str] = None
    detected_prescription_date: Optional[str] = None
    extraction_method: Optional[str] = None
    note: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


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
    items: list[PrescriptionItem] = Field(default_factory=list)
    status: str
    file_path: Optional[str] = None
    source: str = "doctor_issued"
    verified: bool = True
    confirmed_by_patient: bool = False
    prescriber_name: Optional[str] = None
    original_file_name: Optional[str] = None
    safety_warnings: list[dict] = []
    acknowledged_warnings: bool = False
    verification_token: Optional[str] = None
    verification_status: str = "valid"
    created_at: datetime
    updated_at: datetime
    issued_at: Optional[datetime] = None

    class Config:
        from_attributes = True
