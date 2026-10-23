from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.dependencies import get_current_user, get_current_doctor
from app.schemas.doctor import DoctorCreate, DoctorUpdate, DoctorResponse
from app.database.repositories.doctor_repository import DoctorRepository
from app.models.user import User

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get("/me", response_model=DoctorResponse)
async def get_my_profile(current_user: User = Depends(get_current_doctor)):
    repo = DoctorRepository()
    profile = await repo.get_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")
    return profile


@router.put("/me", response_model=DoctorResponse)
async def update_my_profile(doctor_in: DoctorUpdate, current_user: User = Depends(get_current_doctor)):
    repo = DoctorRepository()
    existing = await repo.get_by_user_id(current_user.id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")

    update_data = doctor_in.model_dump(exclude_unset=True)
    updated = await repo.update_profile(existing.id, **update_data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update profile")
    return updated
