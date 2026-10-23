from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal

HistoryEventType = Literal["REPORT", "PRESCRIPTION"]


class HistoryEvent(BaseModel):
    event_id: str
    patient_id: str
    event_type: HistoryEventType
    event_date: Optional[datetime]
    title: str
    summary: str
    source_id: str
    source_reference: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
