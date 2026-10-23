"""Consent-based access: requests + grants (Phase 3)."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

GRANT_SCOPES = ("reports", "prescriptions", "history")


class AccessRequestBase(BaseModel):
    patient_id: str
    doctor_id: str
    scope: list[str] = Field(default_factory=lambda: list(GRANT_SCOPES))
    message: Optional[str] = Field(None, max_length=500)
    status: str = Field(default="pending", pattern=r"^(pending|approved|denied|cancelled)$")


class AccessRequestInDB(AccessRequestBase):
    id: str
    created_at: datetime
    updated_at: datetime
    decided_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AccessGrantBase(BaseModel):
    patient_id: str
    doctor_id: str
    scope: list[str] = Field(default_factory=lambda: list(GRANT_SCOPES))
    status: str = Field(default="active", pattern=r"^(active|revoked|expired)$")
    request_id: Optional[str] = None


class AccessGrantInDB(AccessGrantBase):
    id: str
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

    class Config:
        from_attributes = True
