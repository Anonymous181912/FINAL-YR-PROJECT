from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal, Any


ReportCategory = Literal["MRI", "CT", "ECG", "Ultrasound", "X-ray", "Blood Test", "Other"]
ReportStatus = Literal["pending", "processing", "completed", "failed"]


class ReportBase(BaseModel):
    category: ReportCategory
    title: str = Field(..., min_length=1, max_length=200)
    original_text: Optional[str] = None
    extracted_text: Optional[str] = None
    extraction_method: str = "text"
    entities: list[dict[str, Any]] = []
    lab_results: Optional[list[dict[str, Any]]] = None
    nlp_status: str = "pending"
    ai_status: str = "not_started"
    ai_interpretation: Optional[dict[str, Any]] = None
    important_findings: list[str] = []
    simplified_explanation: Optional[str] = None
    glossary: dict[str, str] = {}
    metadata: dict[str, Any] = {}
    status: ReportStatus = "pending"
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    ocr_used: bool = False
    nlp_processed_at: Optional[datetime] = None
    ai_processed_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None


class ReportCreate(BaseModel):
    category: ReportCategory
    title: str = Field(..., min_length=1, max_length=200)
    patient_id: str
    original_text: Optional[str] = None


class ReportUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[ReportStatus] = None
    extracted_text: Optional[str] = None
    important_findings: Optional[list[str]] = None
    simplified_explanation: Optional[str] = None
    glossary: Optional[dict[str, str]] = None
    metadata: Optional[dict[str, Any]] = None
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ReportInDB(ReportBase):
    id: str
    patient_id: str
    doctor_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Report(ReportBase):
    id: str
    patient_id: str
    doctor_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
