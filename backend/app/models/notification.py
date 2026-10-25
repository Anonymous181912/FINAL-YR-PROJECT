"""Notifications (Phase 2c): in-app reminders, optional SMTP email."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class NotificationBase(BaseModel):
    user_id: str
    kind: str = Field(..., pattern=r"^(follow_up|medication_end|general|prescription_issued)$")
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(default="", max_length=2000)
    link: Optional[str] = None
    ref_id: Optional[str] = None
    dedupe_key: Optional[str] = None
    is_read: bool = False


class NotificationInDB(NotificationBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
