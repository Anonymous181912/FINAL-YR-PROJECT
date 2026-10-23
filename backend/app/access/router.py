"""Consent flow (Phase 3): request -> patient approve/deny -> grant -> revoke."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_patient, get_current_verified_doctor, get_current_user
from app.models.user import User
from app.models.access import AccessRequestInDB, AccessGrantInDB, GRANT_SCOPES
from app.database.repositories.access_repository import (
    AccessRequestRepository,
    AccessGrantRepository,
)
from app.database.repositories.patient_repository import PatientRepository
from app.audit.service import log_access, client_info

router = APIRouter(prefix="/access", tags=["Access & Consent"])


class AccessRequestCreate(BaseModel):
    patient_id: str
    scope: List[str] = Field(default_factory=lambda: list(GRANT_SCOPES))
    message: Optional[str] = Field(None, max_length=500)


class AccessApprove(BaseModel):
    expires_in_days: int = Field(default=30, ge=1, le=365)
    scope: Optional[List[str]] = None


def _check_scope(scope: List[str]) -> List[str]:
    clean = [s for s in (scope or []) if s in GRANT_SCOPES]
    if not clean:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Scope must be a subset of {list(GRANT_SCOPES)}")
    return clean


@router.post("/requests", response_model=AccessRequestInDB, status_code=status.HTTP_201_CREATED)
async def create_access_request(
    payload: AccessRequestCreate,
    request: Request,
    current_user: User = Depends(get_current_verified_doctor),
):
    from app.access import grants as grant_checks

    scope = _check_scope(payload.scope)
    patient_repo = PatientRepository()
    canonical = await grant_checks.canonical_patient_id(patient_repo, payload.patient_id)
    if canonical is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    req_repo = AccessRequestRepository()
    if await req_repo.pending_for(canonical, current_user.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An access request is already pending")
    if await grant_checks.get_active_grant(canonical, current_user.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have active access")

    created = await req_repo.create_request(
        patient_id=canonical, doctor_id=current_user.id, scope=scope,
        message=(payload.message or "").strip() or None, status="pending",
    )
    ip, ua = client_info(request)
    await log_access(current_user.id, current_user.role, "access_requested",
                     "access_request", created.id, canonical, ip, ua)
    return created


@router.get("/requests/incoming", response_model=List[AccessRequestInDB])
async def incoming_requests(
    status_filter: Optional[str] = Query(None, pattern="^(pending|approved|denied|cancelled)$"),
    current_user: User = Depends(get_current_patient),
):
    repo = PatientRepository()
    own = await repo.get_by_user_id(current_user.id)
    if own is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    canonical = own.patient_id or own.user_id or own.id
    return await AccessRequestRepository().incoming(canonical, status=status_filter)


@router.get("/requests/outgoing", response_model=List[AccessRequestInDB])
async def outgoing_requests(current_user: User = Depends(get_current_verified_doctor)):
    return await AccessRequestRepository().outgoing(current_user.id)


@router.post("/requests/{request_id}/approve", response_model=AccessGrantInDB)
async def approve_request(
    request_id: str,
    payload: AccessApprove,
    request: Request,
    current_user: User = Depends(get_current_patient),
):
    req_repo = AccessRequestRepository()
    doc = await req_repo.get_by_id(request_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    access_req = AccessRequestInDB(**doc)

    repo = PatientRepository()
    own = await repo.get_by_user_id(current_user.id)
    canonical = (own.patient_id or own.user_id or own.id) if own else None
    if own is None or access_req.patient_id != canonical:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if access_req.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request already decided")

    scope = _check_scope(payload.scope or access_req.scope)
    grant_repo = AccessGrantRepository()
    existing = await grant_repo.get_active(access_req.patient_id, access_req.doctor_id)
    if existing:
        await req_repo.decide(request_id, "approved")
        return existing
    grant = await grant_repo.create_grant(
        patient_id=access_req.patient_id, doctor_id=access_req.doctor_id,
        scope=scope, status="active", request_id=request_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days),
    )
    # Re-read so expires_at is present even if the driver echoes differently.
    await req_repo.decide(request_id, "approved")
    refreshed = await grant_repo.get_active(access_req.patient_id, access_req.doctor_id)
    ip, ua = client_info(request)
    await log_access(current_user.id, current_user.role, "grant_approved",
                     "access_grant", (refreshed.id if refreshed else grant.id),
                     access_req.patient_id, ip, ua)
    return refreshed or grant


@router.post("/requests/{request_id}/deny", response_model=AccessRequestInDB)
async def deny_request(
    request_id: str,
    request: Request,
    current_user: User = Depends(get_current_patient),
):
    req_repo = AccessRequestRepository()
    doc = await req_repo.get_by_id(request_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    access_req = AccessRequestInDB(**doc)
    repo = PatientRepository()
    own = await repo.get_by_user_id(current_user.id)
    canonical = (own.patient_id or own.user_id or own.id) if own else None
    if own is None or access_req.patient_id != canonical:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if access_req.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request already decided")
    decided = await req_repo.decide(request_id, "denied")
    ip, ua = client_info(request)
    await log_access(current_user.id, current_user.role, "grant_denied",
                     "access_request", request_id, access_req.patient_id, ip, ua)
    return decided


@router.get("/grants/mine", response_model=List[AccessGrantInDB])
async def my_grants(current_user: User = Depends(get_current_patient)):
    repo = PatientRepository()
    own = await repo.get_by_user_id(current_user.id)
    if own is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    canonical = own.patient_id or own.user_id or own.id
    return await AccessGrantRepository().list_for_patient(canonical)


@router.get("/grants/doctor", response_model=List[AccessGrantInDB])
async def doctor_grants(current_user: User = Depends(get_current_verified_doctor)):
    return await AccessGrantRepository().list_active_for_doctor(current_user.id)


@router.delete("/grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_grant(
    grant_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Patients revoke access to their own data; admins may revoke anything."""
    if current_user.role not in ("patient", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    repo = AccessGrantRepository()
    doc = await repo.get_by_id(grant_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grant not found")
    grant = AccessGrantInDB(**doc)
    if current_user.role == "patient":
        patient_repo = PatientRepository()
        own = await patient_repo.get_by_user_id(current_user.id)
        canonical = (own.patient_id or own.user_id or own.id) if own else None
        if own is None or grant.patient_id != canonical:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grant not found")
    revoked = await repo.revoke(grant_id)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grant not found")
    ip, ua = client_info(request)
    await log_access(current_user.id, current_user.role, "grant_revoked",
                     "access_grant", grant_id, grant.patient_id, ip, ua)
    return None
