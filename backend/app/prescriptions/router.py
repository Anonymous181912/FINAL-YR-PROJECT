from fastapi import APIRouter, Depends, HTTPException, Request, status, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from datetime import date
from typing import List, Optional
from app.auth.dependencies import get_current_user, get_current_verified_doctor, get_current_patient
from app.schemas.prescription import (
    PaperPrescriptionConfirm,
    PaperPrescriptionScanResponse,
    PrescriptionCreate,
    PrescriptionResponse,
    PrescriptionUpdate,
)
from app.models.user import User
from app.prescriptions.services.prescription_service import PrescriptionService, PrescriptionServiceError
from app.prescriptions.services.paper_prescription_service import (
    PaperPrescriptionError,
    PaperPrescriptionService,
)
from app.prescriptions.services.pdf_service import PrescriptionPDFError
from app.reports.services.file_validation import FileValidationError
from app.access import grants as grant_checks
from app.audit.service import log_access, client_info
from app.database.repositories.patient_repository import PatientRepository
from app.database.repositories.doctor_repository import DoctorRepository
from app.database.repositories.notification_repository import NotificationRepository

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])


@router.post("/", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_prescription(prescription_in: PrescriptionCreate, request: Request, current_user: User = Depends(get_current_verified_doctor)):
    service = PrescriptionService()
    try:
        # A2: Check patient's prescribing permission setting
        patient_repo = PatientRepository()
        canonical = await grant_checks.canonical_patient_id(patient_repo, prescription_in.patient_id)
        if canonical is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
        
        patient = await patient_repo.get_by_patient_id(canonical)
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
        
        # If patient has disabled prescriptions, return 403
        if not patient.allow_prescriptions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This patient has disabled prescription writing. Contact the patient to enable it in Access & Privacy."
            )
        
        # If allow_prescriptions is ON, no grant needed for prescribing
        # (Reading reports/labs/history still requires an approved grant)
        
        prescription = await service.create_prescription(
            doctor_id=current_user.id,
            patient_id=canonical,
            prescription_date=prescription_in.prescription_date,
            diagnosis_notes=prescription_in.diagnosis_notes,
            advice=prescription_in.advice,
            follow_up_date=prescription_in.follow_up_date,
            items=[item.model_dump() for item in prescription_in.items],
            status="draft",
            acknowledge_warnings=prescription_in.acknowledge_warnings,
            ack_reason=prescription_in.ack_reason,
        )
        ip, ua = client_info(request)
        await log_access(current_user.id, current_user.role, "create", "prescription",
                         prescription.id, canonical, ip, ua)
        return prescription
    except PrescriptionServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create prescription")


@router.get("/doctor", response_model=List[PrescriptionResponse])
async def list_doctor_prescriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_verified_doctor),
):
    service = PrescriptionService()
    prescriptions = await service.list_doctor_prescriptions(current_user.id, skip=skip, limit=limit)
    return prescriptions


@router.get("/patient", response_model=List[PrescriptionResponse])
async def list_patient_prescriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_patient),
):
    service = PrescriptionService()
    prescriptions = await service.list_patient_prescriptions(current_user.id, skip=skip, limit=limit)
    return prescriptions


@router.post("/paper", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_paper_prescription(
    request: Request,
    file: UploadFile = File(...),
    prescriber_name: Optional[str] = Form(None),
    prescription_date: Optional[date] = Form(None),
    note: Optional[str] = Form(None),
    current_user: User = Depends(get_current_patient),
):
    """Store a patient's paper prescription file as an unverified record.

    This endpoint intentionally does not run OCR or create medicine rows.
    """
    service = PaperPrescriptionService()
    try:
        record = await service.create(
            current_user.id,
            file,
            prescriber_name=prescriber_name,
            prescription_date=prescription_date,
            note=note,
        )
        ip, ua = client_info(request)
        await log_access(current_user.id, current_user.role, "create", "prescription",
                         record.id, record.patient_id, ip, ua)
        return record
    except PaperPrescriptionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save paper prescription")


@router.get("/paper/{prescription_id}/file")
async def get_paper_prescription_file(
    prescription_id: str,
    current_user: User = Depends(get_current_patient),
):
    """Serve the original paper file to its owner only."""
    service = PaperPrescriptionService()
    file_info = await service.get_file(prescription_id, current_user.id)
    if not file_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper prescription file not found")
    return FileResponse(
        file_info["path"],
        media_type=file_info["media_type"],
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/paper/scan", response_model=PaperPrescriptionScanResponse)
async def scan_paper_prescription(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_patient),
):
    """Patient digitizes a paper prescription into DRAFT rows.

    Reuses the existing scan pipeline and stores only a temporary upload copy.
    Nothing is added to the medical history until the patient confirms.
    """
    service = PaperPrescriptionService()
    try:
        return await service.scan(file, current_user.id)
    except (FileValidationError, ValueError) as exc:
        detail = exc.detail if isinstance(exc, FileValidationError) else str(exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Scan failed")


@router.post("/paper/confirm", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
async def confirm_paper_prescription(
    payload: PaperPrescriptionConfirm,
    request: Request,
    current_user: User = Depends(get_current_patient),
):
    """Save the patient-reviewed paper rows as an unverified paper record."""
    service = PaperPrescriptionService()
    try:
        record = await service.confirm(current_user.id, payload)
        ip, ua = client_info(request)
        await log_access(current_user.id, current_user.role, "create", "prescription",
                         record.id, record.patient_id, ip, ua)
        return record
    except PaperPrescriptionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save paper prescription")


@router.delete("/paper/{prescription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper_prescription(
    prescription_id: str,
    current_user: User = Depends(get_current_patient),
):
    service = PaperPrescriptionService()
    deleted = await service.delete(prescription_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper prescription not found")
    return None


@router.get("/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription(prescription_id: str, request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role == "doctor":
        from app.database.repositories.doctor_repository import DoctorRepository

        repo = DoctorRepository()
        profile = await repo.get_by_user_id(current_user.id)
        if profile is None or not profile.is_verified or profile.verification_status != "approved":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor account pending approval.",
            )
    service = PrescriptionService()
    prescription = await service.get_prescription(prescription_id, current_user.id, current_user.role)
    if not prescription and current_user.role == "doctor":
        # Paper prescriptions have no issuing doctor. A verified doctor may
        # read them only with an active patient grant; the response carries
        # source/verified so the UI can show the "not verified" badge.
        candidate = await service.repo.get_by_id(prescription_id)
        if candidate and getattr(candidate, "source", None) == "patient_uploaded":
            await grant_checks.require_active_grant(
                candidate.patient_id, current_user.id, "prescriptions"
            )
            prescription = candidate
    if not prescription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    ip, ua = client_info(request)
    await log_access(current_user.id, current_user.role, "read", "prescription",
                     prescription.id, prescription.patient_id, ip, ua)
    return prescription


@router.put("/{prescription_id}", response_model=PrescriptionResponse)
async def update_prescription(prescription_id: str, prescription_in: PrescriptionUpdate, request: Request, current_user: User = Depends(get_current_verified_doctor)):
    service = PrescriptionService()
    try:
        updated = await service.update_prescription(
            prescription_id,
            doctor_id=current_user.id,
            prescription_date=prescription_in.prescription_date,
            diagnosis_notes=prescription_in.diagnosis_notes,
            advice=prescription_in.advice,
            follow_up_date=prescription_in.follow_up_date,
            items=[item.model_dump() for item in prescription_in.items] if prescription_in.items else None,
            status=prescription_in.status,
            acknowledge_warnings=prescription_in.acknowledge_warnings,
            ack_reason=prescription_in.ack_reason,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
        ip, ua = client_info(request)
        await log_access(current_user.id, current_user.role, "update", "prescription",
                         updated.id, updated.patient_id, ip, ua)
        return updated
    except PrescriptionServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update prescription")


@router.delete("/{prescription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prescription(prescription_id: str, current_user: User = Depends(get_current_verified_doctor)):
    service = PrescriptionService()
    deleted = await service.delete_prescription(prescription_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    return None


@router.post("/{prescription_id}/revoke", response_model=PrescriptionResponse)
async def revoke_prescription(prescription_id: str, current_user: User = Depends(get_current_verified_doctor)):
    """Author doctor revokes the QR verification (public page shows revoked)."""
    service = PrescriptionService()
    revoked = await service.revoke_prescription(prescription_id, current_user.id)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    return revoked


@router.post("/{prescription_id}/issue", response_model=PrescriptionResponse)
async def issue_prescription(prescription_id: str, request: Request, current_user: User = Depends(get_current_verified_doctor)):
    """Issue a draft prescription to the patient: sets status=issued, issued_at, generates PDF,
    adds history event, and creates patient notification."""
    service = PrescriptionService()
    try:
        # First, get the prescription to verify ownership and get patient info
        prescription = await service.get_prescription(prescription_id, current_user.id, "doctor")
        if not prescription:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
        
        if prescription.status == "issued":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prescription already issued")
        
        # Update status to issued (this will set issued_at)
        updated = await service.update_prescription(
            prescription_id,
            doctor_id=current_user.id,
            status="issued",
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
        
        # Generate PDF
        try:
            pdf_path = await service.generate_pdf(updated)
        except PrescriptionPDFError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
        
        # Create notification for patient
        notification_repo = NotificationRepository()
        doctor_repo = DoctorRepository()
        doctor = await doctor_repo.get_by_doctor_id(current_user.id)
        doctor_name = doctor.full_name if doctor else "Your doctor"
        
        await notification_repo.create_notification(
            user_id=updated.patient_id,
            kind="prescription_issued",
            title="New Prescription Issued",
            body=f"Dr {doctor_name} issued a new prescription for you.",
            link="/patient/prescriptions",
            ref_id=updated.id,
        )
        
        # Audit log
        ip, ua = client_info(request)
        await log_access(current_user.id, current_user.role, "issue", "prescription",
                         updated.id, updated.patient_id, ip, ua)
        
        return updated
    except PrescriptionServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to issue prescription")


@router.post("/scan")
async def scan_prescription(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_verified_doctor),
):
    """Handwritten prescription upload -> DRAFT items for doctor review.

    Runs OCR (or reads text directly), applies deterministic rules first and
    falls back to the LLM with schema validation. NEVER saves anything: the
    doctor must review and submit the draft through the normal create flow.
    """
    from app.prescriptions.services.scan_service import parse_prescription_scan

    try:
        draft = await parse_prescription_scan(file)
        return draft
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Scan failed")


@router.post("/{prescription_id}/pdf")
async def generate_prescription_pdf(prescription_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role == "doctor":
        from app.database.repositories.doctor_repository import DoctorRepository

        repo = DoctorRepository()
        profile = await repo.get_by_user_id(current_user.id)
        if profile is None or not profile.is_verified or profile.verification_status != "approved":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor account pending approval.",
            )
    service = PrescriptionService()
    prescription = await service.get_prescription(prescription_id, current_user.id, current_user.role)
    if not prescription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")

    try:
        pdf_path = await service.generate_pdf(prescription)
    except PrescriptionPDFError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    return FileResponse(pdf_path, media_type="application/pdf", filename=f"prescription_{prescription.id}.pdf")
