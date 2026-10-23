from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MedicalEntity(BaseModel):
    type: str
    text: str
    normalized_text: Optional[str] = None
    value: Optional[str] = None
    unit: Optional[str] = None
    severity: Optional[str] = None
    negated: bool = False
    context: Optional[str] = None
    confidence: float = 0.0
    source_text: Optional[str] = None

    class Config:
        from_attributes = True
