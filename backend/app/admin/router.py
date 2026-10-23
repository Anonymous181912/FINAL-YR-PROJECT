"""Admin-only router (Phase 0b): doctor verification queue."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List
from app.auth.dependencies import get_current_admin
from app.schemas.doctor import DoctorResponse
from app.database.repositories.doctor_repository import DoctorRepository
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/pending-doctors", response_model=List[DoctorResponse])
async def list_pending_doctors(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_admin),
):
    repo = DoctorRepository()
    return await repo.list_pending(skip=skip, limit=limit)


@router.post("/doctors/{doctor_id}/approve", response_model=DoctorResponse)
async def approve_doctor(doctor_id: str, current_user: User = Depends(get_current_admin)):
    repo = DoctorRepository()
    updated = await repo.set_verification(doctor_id, "approved")
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return updated


@router.post("/doctors/{doctor_id}/reject", response_model=DoctorResponse)
async def reject_doctor(doctor_id: str, current_user: User = Depends(get_current_admin)):
    repo = DoctorRepository()
    updated = await repo.set_verification(doctor_id, "rejected")
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return updated
