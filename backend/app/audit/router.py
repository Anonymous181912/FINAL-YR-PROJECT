"""Audit views (Phase 3): patients see who accessed their data; admin filter."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional

from app.auth.dependencies import get_current_patient, get_current_admin, get_current_user
from app.models.user import User
from app.models.audit import AuditLogInDB
from app.database.repositories.audit_repository import AuditRepository
from app.database.repositories.patient_repository import PatientRepository

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/me", response_model=List[AuditLogInDB])
async def my_audit_trail(
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_patient),
):
    repo = PatientRepository()
    own = await repo.get_by_user_id(current_user.id)
    if own is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    canonical = own.patient_id or own.user_id or own.id
    return await AuditRepository().for_patient(canonical, limit=limit)


@router.get("/", response_model=List[AuditLogInDB])
async def admin_audit_search(
    actor_id: Optional[str] = None,
    action: Optional[str] = None,
    patient_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_admin),
):
    return await AuditRepository().search(
        actor_id=actor_id, action=action, patient_id=patient_id,
        resource_type=resource_type, limit=limit,
    )
