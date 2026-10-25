import re
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from typing import List, Optional
from app.auth.dependencies import (
    get_current_user,
    get_current_patient,
    get_current_verified_doctor,
)
from app.access import grants as grant_checks
from app.audit.service import log_access, client_info
from app.schemas.patient import PatientCreate, PatientUpdate, PatientResponse
from app.models.patient import PatientSearchResult
from app.database.repositories.patient_repository import PatientRepository
from app.models.user import User

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("/me", response_model=PatientResponse)
async def get_my_profile(current_user: User = Depends(get_current_patient)):
    repo = PatientRepository()
    profile = await repo.get_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    return profile


@router.put("/me", response_model=PatientResponse)
async def update_my_profile(patient_in: PatientUpdate, current_user: User = Depends(get_current_patient)):
    repo = PatientRepository()
    existing = await repo.get_by_user_id(current_user.id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")

    update_data = patient_in.model_dump(exclude_unset=True)
    updated = await repo.update_profile(existing.id, **update_data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update profile")
    return updated


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(patient_in: PatientCreate, current_user: User = Depends(get_current_verified_doctor)):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not yet implemented")


@router.get("/search", response_model=List[PatientSearchResult])
async def search_patients(
    q: str = Query(..., min_length=1, max_length=100, description="Search by name, email, or patient code"),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_verified_doctor),
):
    """Doctor searches for a patient by name, email, or patient_code.
    Returns minimal fields: id, full_name, patient_code, age."""
    repo = PatientRepository()
    patients = await repo.search_patients(q, limit=limit)
    
    results = []
    for p in patients:
        age = None
        if p.date_of_birth:
            from datetime import datetime
            today = datetime.now()
            age = today.year - p.date_of_birth.year - (
                (today.month, today.day) < (p.date_of_birth.month, p.date_of_birth.day)
            )
        results.append(PatientSearchResult(
            id=p.id,
            patient_id=p.patient_id or p.user_id or p.id,
            full_name=p.full_name,
            patient_code=p.patient_code or "",
            age=age,
        ))
    return results


@router.get("/me/emergency-card")
async def get_emergency_card(current_user: User = Depends(get_current_patient)):
    """Printable emergency PDF (blood group, allergies, emergency contact) + QR
    to a revocable public page showing only those fields."""
    import secrets

    from fastapi.responses import FileResponse

    from app.core.config import settings
    from app.prescriptions.services.pdf_service import PrescriptionPDFService, PrescriptionPDFError

    repo = PatientRepository()
    profile = await repo.get_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    if not profile.emergency_token:
        profile = await repo.update_profile(profile.id, emergency_token=secrets.token_urlsafe(24))
        if not profile:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to prepare emergency card")
    verify_url = f"{settings.frontend_url.rstrip('/')}/emergency/{profile.emergency_token}"
    try:
        pdf_path = PrescriptionPDFService().generate_emergency_card(profile, verify_url)
    except PrescriptionPDFError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return FileResponse(pdf_path, media_type="application/pdf", filename="emergency_card.pdf")


@router.post("/me/emergency-token/rotate")
async def rotate_emergency_token(current_user: User = Depends(get_current_patient)):
    """Issue a new public emergency token (revokes the old link)."""
    import secrets

    repo = PatientRepository()
    profile = await repo.get_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    updated = await repo.update_profile(profile.id, emergency_token=secrets.token_urlsafe(24))
    return {"emergency_token": updated.emergency_token if updated else None}


@router.delete("/me/emergency-token", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_emergency_token(current_user: User = Depends(get_current_patient)):
    """Revoke the public emergency page (old links stop working)."""
    repo = PatientRepository()
    profile = await repo.get_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    await repo.update_profile(profile.id, emergency_token=None)
    return None


@router.get("/", response_model=List[PatientResponse])
async def list_patients(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(default=None, max_length=100),
    current_user: User = Depends(get_current_verified_doctor),
):
    """Phase 3: doctors list ONLY patients with an active grant."""
    repo = PatientRepository()
    allowed_ids = await grant_checks.granted_patient_ids(current_user.id)
    if not allowed_ids:
        return []
    filter_query: dict = {"$or": [
        {"patient_id": {"$in": allowed_ids}},
        {"user_id": {"$in": allowed_ids}},
    ]}
    if search:
        # Phase 0d: cap length (also enforced by Query max_length) and escape
        # regex metacharacters so user input cannot inject $regex patterns.
        safe = re.escape(search[:50])
        filter_query = {"$and": [filter_query, {"full_name": {"$regex": safe, "$options": "i"}}]}

    cursor = repo.collection.find(filter_query)
    cursor.skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [PatientResponse(**doc) for doc in docs]


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: str, request: Request, current_user: User = Depends(get_current_user)):
    """Phase 0c + Phase 3: patients read only their own profile; verified
    doctors only WITH an active grant (404 when missing — no leak).

    Unknown ids and forbidden ids both yield 404 so existence is not leaked.
    """
    from app.database.repositories.doctor_repository import DoctorRepository

    repo = PatientRepository()
    profile = await repo.get_by_patient_id(patient_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    if current_user.role == "patient":
        own = await repo.get_by_user_id(current_user.id)
        own_ids = set()
        if own is not None:
            own_ids = {own.id, own.user_id, own.patient_id}
        if patient_id not in own_ids and profile.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
        ip, ua = client_info(request)
        await log_access(current_user.id, current_user.role, "read", "patient",
                         profile.id, profile.patient_id or profile.user_id, ip, ua)
        return profile

    if current_user.role == "doctor":
        doctor_repo = DoctorRepository()
        doc_profile = await doctor_repo.get_by_user_id(current_user.id)
        if (
            doc_profile is None
            or not doc_profile.is_verified
            or doc_profile.verification_status != "approved"
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor account pending approval.")
        canonical = profile.patient_id or profile.user_id or profile.id
        await grant_checks.require_active_grant(canonical, current_user.id, "reports")
        ip, ua = client_info(request)
        await log_access(current_user.id, current_user.role, "read", "patient",
                         profile.id, canonical, ip, ua)
        return profile

    if current_user.role == "admin":
        return profile

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: str, patient_in: PatientUpdate, request: Request, current_user: User = Depends(get_current_verified_doctor)):
    """Phase 3: doctor writes need an active grant (404 without — no leak)."""
    repo = PatientRepository()
    profile = await repo.get_by_patient_id(patient_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    canonical = profile.patient_id or profile.user_id or profile.id
    await grant_checks.require_active_grant(canonical, current_user.id, "reports")
    updated = await repo.update_profile(profile.id, **patient_in.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    ip, ua = client_info(request)
    await log_access(current_user.id, current_user.role, "update", "patient",
                     updated.id, canonical, ip, ua)
    return updated
