"""Audit log entries (Phase 3): who accessed whose data, when, for what."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class AuditLogBase(BaseModel):
    actor_id: str
    actor_role: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    patient_id: Optional[str] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None


class AuditLogInDB(AuditLogBase):
    id: str
    timestamp: datetime

    class Config:
        from_attributes = True
