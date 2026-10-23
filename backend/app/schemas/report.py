from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any
from app.models.report import Report
from app.schemas.ai_interpretation import LLMInterpretationResponse


class ReportCreate(BaseModel):
    category: str
    title: str
    patient_id: str
    original_text: Optional[str] = None


class ReportUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    extracted_text: Optional[str] = None
    extraction_method: Optional[str] = None
    entities: Optional[list[dict[str, Any]]] = None
    nlp_status: Optional[str] = None
    ai_status: Optional[str] = None
    ai_interpretation: Optional[dict[str, Any]] = None
    important_findings: Optional[list[str]] = None
    simplified_explanation: Optional[str] = None
    glossary: Optional[dict[str, str]] = None
    metadata: Optional[dict[str, str]] = None
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ReportResponse(BaseModel):
    id: str
    category: str
    title: str
    patient_id: str
    doctor_id: Optional[str] = None
    original_text: Optional[str] = None
    extracted_text: Optional[str] = None
    extraction_method: str
    entities: list[dict[str, Any]] = []
    lab_results: Optional[list[dict[str, Any]]] = None
    nlp_status: str
    ai_status: str
    ai_interpretation: Optional[dict[str, Any]] = None
    important_findings: list[str] = []
    simplified_explanation: Optional[str] = None
    glossary: dict[str, str] = {}
    metadata: dict[str, str] = {}
    status: str
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    ocr_used: bool
    nlp_processed_at: Optional[datetime] = None
    ai_processed_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
