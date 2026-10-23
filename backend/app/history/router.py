from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from typing import List, Optional
from app.auth.dependencies import get_current_user, get_current_verified_doctor, get_current_patient
from app.models.user import User
from app.schemas.history import HistoryEventResponse
from app.history.services.history_service import HistoryService, HistoryServiceError
from app.access import grants as grant_checks
from app.audit.service import log_access, client_info
from app.database.repositories.patient_repository import PatientRepository

router = APIRouter(prefix="/history", tags=["History"])


@router.get("/", response_model=List[HistoryEventResponse])
async def get_my_history(
    request: Request,
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_patient),
):
    service = HistoryService()
    try:
        events = await service.get_patient_history(
            patient_id=current_user.id,
            order=order,
            limit=limit,
        )
        ip, ua = client_info(request)
        await log_access(current_user.id, current_user.role, "read", "history",
                         "self", current_user.id, ip, ua)
        return events
    except HistoryServiceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load history")


@router.get("/patient/{patient_id}", response_model=List[HistoryEventResponse])
async def get_patient_history_doctor(
    patient_id: str,
    request: Request,
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_verified_doctor),
):
    # Phase 3: per-patient consent on top of verification (404 — no leak).
    canonical = await grant_checks.canonical_patient_id(PatientRepository(), patient_id)
    if canonical is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    await grant_checks.require_active_grant(canonical, current_user.id, "history")
    service = HistoryService()
    try:
        events = await service.get_patient_history(
            patient_id=patient_id,
            order=order,
            limit=limit,
        )
        ip, ua = client_info(request)
        await log_access(current_user.id, current_user.role, "read", "history",
                         patient_id, canonical, ip, ua)
        return events
    except HistoryServiceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load history")
