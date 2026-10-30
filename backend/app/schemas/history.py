from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.history_event import HistoryEvent, HistoryEventType


class HistoryEventResponse(BaseModel):
    event_id: str
    patient_id: str
    event_type: HistoryEventType
    event_date: Optional[datetime] = None
    title: str
    summary: str
    source_id: str
    source_reference: Optional[str] = None
    source: Optional[str] = None
    verified: Optional[bool] = None
    created_at: datetime

    class Config:
        from_attributes = True
