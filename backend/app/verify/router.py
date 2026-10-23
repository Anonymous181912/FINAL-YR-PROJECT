"""Public verification endpoints (Phase 2b/2d). No auth on purpose.

Only non-sensitive facts are ever returned: validity, doctor name, issue
date. Nothing about the patient, medicines, or clinical content.
"""

from fastapi import APIRouter, HTTPException, status
from app.prescriptions.services.prescription_service import PrescriptionService
from app.database.repositories.doctor_repository import DoctorRepository
from app.database.repositories.patient_repository import PatientRepository

router = APIRouter(prefix="/verify", tags=["Verification"])


@router.get("/prescription/{token}")
async def verify_prescription(token: str):
    service = PrescriptionService()
    prescription = await service.get_by_token(token)
    if not prescription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification code not found")

    state = service.verify_token(prescription)
    doctor_name = "Doctor"
    try:
        doctor = await DoctorRepository().get_by_doctor_id(prescription.doctor_id)
        if doctor and doctor.full_name:
            doctor_name = doctor.full_name
    except Exception:
        pass
    issue_date = prescription.issued_at or prescription.prescription_date or prescription.created_at
    return {
        "status": state,
        "doctor_name": doctor_name,
        "issue_date": issue_date.isoformat() if issue_date else None,
        "prescription_ref": prescription.id[-6:].upper() if prescription.id else None,
        "disclaimer": "This page confirms a prescription's authenticity only. It is not medical advice.",
    }


@router.get("/emergency/{token}")
async def verify_emergency_card(token: str):
    """Revocable public emergency page: ONLY blood group, allergies and
    emergency contact. No name, no history, no medicines."""
    repo = PatientRepository()
    try:
        doc = await repo.get_by_field("emergency_token", token)
    except Exception:
        doc = None
    if not doc or not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergency code not found")
    return {
        "blood_group": doc.get("blood_group"),
        "allergies": doc.get("allergies") or [],
        "emergency_contact_name": doc.get("emergency_contact_name"),
        "emergency_contact_phone": doc.get("emergency_contact_phone"),
        "disclaimer": "Emergency information only. Call local emergency services for help.",
    }
