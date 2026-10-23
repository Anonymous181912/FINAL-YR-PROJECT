from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status, Query, UploadFile, File, Form
from typing import List, Optional
from pydantic import BaseModel, Field
from app.auth.dependencies import get_current_user, get_current_patient
from app.core.rate_limit import limiter
from app.schemas.report import ReportCreate, ReportUpdate, ReportResponse
from app.schemas.ai_interpretation import LLMInterpretationResponse
from app.models.user import User
from app.models.report import Report
from app.reports.services.report_service import ReportService
from app.reports.services.file_validation import FileValidationError
from app.reports.ai.llm import LLMService, LLMServiceError
from app.access import grants as grant_checks
from app.audit.service import log_access, client_info

router = APIRouter(prefix="/reports", tags=["Reports"])


async def _require_verified_doctor_if_doctor(current_user: User) -> None:
    if current_user.role == "doctor":
        from app.database.repositories.doctor_repository import DoctorRepository

        repo = DoctorRepository()
        profile = await repo.get_by_user_id(current_user.id)
        if profile is None or not profile.is_verified or profile.verification_status != "approved":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor account pending approval.",
            )
    elif current_user.role not in ("patient", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


@router.post("/upload", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def upload_report(
    request: Request,
    background: BackgroundTasks,
    category: str = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_patient),
):
    from app.core.config import settings as _settings

    service = ReportService()
    # Phase 4d: async mode returns immediately with status "processing" and
    # finishes OCR/NLP/labs in a background task. Default stays synchronous
    # so existing clients and tests are unaffected.
    if not _settings.sync_upload:
        try:
            full_path, file_size = await service.save_incoming_file(file)
        except FileValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail)
        pending = await service.create_pending_record(
            current_user.id, category, title, file, full_path, file_size
        )
        background.add_task(service.process_saved_file, pending.id, full_path, current_user.id)
        return ReportService.to_response_dict(pending)
    try:
        result = await service.process_upload(
            file=file,
            patient_id=current_user.id,
            category=category,
            title=title,
        )
        return result
    except FileValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Upload failed")


@router.post("/{report_id}/interpret", response_model=LLMInterpretationResponse)
async def interpret_report(
    report_id: str,
    language: str = Query("en", min_length=2, max_length=10),
    current_user: User = Depends(get_current_patient),
):
    language = (language or "en").lower()
    allowed = {"en", "hi", "mr", "ta", "te", "bn", "es", "fr"}
    if language not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language '{language}'. Supported: {sorted(allowed)}",
        )
    service = ReportService()
    report = await service.get_report_for_patient(report_id, current_user.id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if not report.extracted_text and not report.entities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report does not have extracted text or entities available for interpretation",
        )

    try:
        interpretation = await service.interpret_report(report, language=language)
        return interpretation
    except LLMServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Interpretation failed")


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    history: list[dict] = Field(default_factory=list, max_length=20)


@router.post("/{report_id}/chat")
@limiter.limit("30/minute")
async def chat_with_report(
    report_id: str,
    request: Request,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """Chat with your report: answers ONLY from the report text.

    Patients ask about their own reports; verified doctors need an active
    grant (Phase 3). Diagnosis/treatment questions are refused.
    """
    from app.reports.ai.chat import answer_question, MAX_HISTORY_TURNS

    await _require_verified_doctor_if_doctor(current_user)
    service = ReportService()
    report = await service.get_report_for_patient(report_id, current_user.id, current_user.role)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if current_user.role == "doctor":
        await grant_checks.require_active_grant(report.patient_id, current_user.id, "reports")
    if not (report.extracted_text or "").strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Report has no text to chat about")
    history = (payload.history or [])[-MAX_HISTORY_TURNS:]
    result = await answer_question(payload.question, report.extracted_text, history)
    ip, ua = client_info(request)
    await log_access(current_user.id, current_user.role, "chat", "report",
                     report.id, report.patient_id, ip, ua)
    return {"report_id": report.id, **result,
            "disclaimer": "Educational explanation of your report, not a diagnosis. Ask your doctor about treatment."}


@router.get("/", response_model=List[ReportResponse])
async def list_reports(
    request: Request,
    patient_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    await _require_verified_doctor_if_doctor(current_user)
    service = ReportService()
    repo = service.report_repo

    if current_user.role == "patient":
        reports = await repo.list_by_patient(current_user.id, skip=skip, limit=limit)
        return reports
    if current_user.role == "doctor":
        # Phase 3: without a target patient there is nothing listable;
        # with one, an active grant is required (404 otherwise — no leak).
        if not patient_id:
            return []
        from app.database.repositories.patient_repository import PatientRepository

        canonical = await grant_checks.canonical_patient_id(PatientRepository(), patient_id)
        if canonical is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
        await grant_checks.require_active_grant(canonical, current_user.id, "reports")
        ip, ua = client_info(request)
        await log_access(current_user.id, current_user.role, "list", "report",
                         None, canonical, ip, ua)
        return await repo.list_by_patient(canonical, skip=skip, limit=limit)
    # admin
    target_patient_id = patient_id or current_user.id
    return await repo.list_by_patient(target_patient_id, skip=skip, limit=limit)


@router.get("/trends")
async def get_lab_trends(
    request: Request,
    test: str = Query(..., min_length=1, max_length=100),
    patient_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Time series of one lab test across a patient's reports.

    Patients always see their own data; verified doctors pass ``patient_id``
    AND need an active consent grant (Phase 3). Fewer than 2 points is
    still 200 with an empty ``points`` list — never an error.
    """
    from app.reports.services.lab_parser import canonicalize_test_name
    from app.reports.services.reference_ranges import REFERENCE_RANGES
    from app.database.repositories.patient_repository import PatientRepository

    await _require_verified_doctor_if_doctor(current_user)
    canonical = canonicalize_test_name(test)
    if canonical is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown test '{test}'. Supported: {', '.join(sorted(REFERENCE_RANGES))}",
        )

    patient_repo = PatientRepository()
    if current_user.role == "patient":
        own = await patient_repo.get_by_user_id(current_user.id)
        if own is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
        target = await patient_repo.get_by_patient_id(own.patient_id or own.user_id or own.id)
    elif current_user.role == "doctor":
        if not patient_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="patient_id is required for doctor role")
        target = await patient_repo.get_by_patient_id(patient_id)
    else:  # admin
        if not patient_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="patient_id is required for admin role")
        target = await patient_repo.get_by_patient_id(patient_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    canonical_id = target.patient_id or target.user_id or target.id
    if current_user.role == "doctor":
        # Phase 3: per-patient consent on top of verification.
        await grant_checks.require_active_grant(canonical_id, current_user.id, "reports")

    service = ReportService()
    reports = await service.report_repo.list_by_patient(canonical_id, limit=100)
    reports = sorted(reports, key=lambda r: r.created_at or service.report_repo._now())

    points = []
    for rep in reports:
        for lab in rep.lab_results or []:
            if lab.get("canonical_name") == canonical:
                points.append({
                    "report_id": rep.id,
                    "date": rep.created_at.isoformat() if rep.created_at else None,
                    "title": rep.title,
                    "value": lab.get("value"),
                    "unit": lab.get("unit"),
                    "flag": lab.get("flag"),
                    "ref_low": lab.get("ref_low"),
                    "ref_high": lab.get("ref_high"),
                    "range_source": lab.get("range_source"),
                })
    table_range = REFERENCE_RANGES[canonical]["ranges"]["adult"]
    band_low = min([p["ref_low"] for p in points if p["ref_low"] is not None], default=table_range[0])
    band_high = max([p["ref_high"] for p in points if p["ref_high"] is not None], default=table_range[1])
    ip, ua = client_info(request)
    await log_access(current_user.id, current_user.role, "read", "report_trends",
                     canonical, canonical_id, ip, ua)
    return {
        "test": canonical,
        "display_name": REFERENCE_RANGES[canonical]["display_name"],
        "unit": REFERENCE_RANGES[canonical]["standard_unit"],
        "points": points,
        "ref_low": band_low,
        "ref_high": band_high,
        "disclaimer": "Educational reference ranges, not clinical advice. Discuss trends with your doctor — this is an explanation, not a diagnosis.",
    }


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(report_id: str, current_user: User = Depends(get_current_patient)):
    # get_current_patient enforces authentication (401) and patient role (403
    # for doctors). Ownership is verified below: unknown ids and other
    # patients' reports both yield 404 without leaking which case applies.
    service = ReportService()
    report = await service.get_report_for_patient(report_id, current_user.id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    deleted = await service.delete_report(report)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return None
@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str, request: Request, current_user: User = Depends(get_current_user)):
    await _require_verified_doctor_if_doctor(current_user)
    service = ReportService()
    report = await service.get_report_for_patient(report_id, current_user.id, current_user.role)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if current_user.role == "doctor":
        # Phase 3: per-patient consent on top of verification.
        await grant_checks.require_active_grant(report.patient_id, current_user.id, "reports")
    ip, ua = client_info(request)
    await log_access(current_user.id, current_user.role, "read", "report",
                     report.id, report.patient_id, ip, ua)
    return report


@router.get("/{report_id}/labs")
async def get_report_labs(report_id: str, request: Request, current_user: User = Depends(get_current_user)):
    """Lab results parsed from a report (same access rules as the report)."""
    await _require_verified_doctor_if_doctor(current_user)
    service = ReportService()
    report = await service.get_report_for_patient(report_id, current_user.id, current_user.role)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if current_user.role == "doctor":
        await grant_checks.require_active_grant(report.patient_id, current_user.id, "reports")
    ip, ua = client_info(request)
    await log_access(current_user.id, current_user.role, "read", "report_labs",
                     report.id, report.patient_id, ip, ua)
    return {"report_id": report.id, "lab_results": report.lab_results or []}


