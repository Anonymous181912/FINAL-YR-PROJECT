"""Longitudinal health trend endpoints (deterministic, no LLM calls)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.access import grants as grant_checks
from app.audit.service import client_info, log_access
from app.auth.dependencies import get_current_patient, get_current_user
from app.database.repositories.patient_repository import PatientRepository
from app.database.repositories.report_repository import ReportRepository
from app.models.user import User
from app.reports.services.lab_parser import canonicalize_test_name
from app.reports.services.reference_ranges import REFERENCE_RANGES
from app.reports.services.trend_service import (
    apply_patient_point_update,
    build_test_series,
    build_trend_summary,
)

router = APIRouter(prefix="/trends", tags=["Health Trends"])


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


async def _resolve_target(
    current_user: User,
    patient_id: Optional[str],
) -> tuple[str, list[str], PatientRepository]:
    """Return ``(canonical_patient_id, lookup_ids, patient_repo)``."""
    patient_repo = PatientRepository()

    if current_user.role == "patient":
        profile = await patient_repo.get_by_user_id(current_user.id)
        if profile is None:
            profile = await patient_repo.get_by_patient_id(current_user.id)
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient profile not found",
            )
        canonical = profile.patient_id or profile.user_id or profile.id
        ids = [
            value
            for value in (
                current_user.id,
                profile.id,
                profile.user_id,
                profile.patient_id,
            )
            if value
        ]
        return (canonical, list(dict.fromkeys(ids)), patient_repo)

    if current_user.role == "doctor":
        if not patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="patient_id is required for doctor role",
            )
        canonical = await grant_checks.canonical_patient_id(patient_repo, patient_id)
        if canonical is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
            )
        await grant_checks.require_active_grant(canonical, current_user.id, "reports")
        target = await patient_repo.get_by_patient_id(patient_id)
        ids = [
            value
            for value in (
                target.id,
                target.user_id,
                target.patient_id,
                patient_id,
            )
            if value
        ] if target else [patient_id, canonical]
        return (canonical, list(dict.fromkeys(ids)), patient_repo)

    # Admin
    if not patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="patient_id is required for admin role",
        )
    target = await patient_repo.get_by_patient_id(patient_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    canonical = target.patient_id or target.user_id or target.id
    ids = [
        value
        for value in (target.id, target.user_id, target.patient_id, patient_id)
        if value
    ]
    return (canonical, list(dict.fromkeys(ids)), patient_repo)


@router.get("/summary")
async def get_trend_summary(
    request: Request,
    patient_id: Optional[str] = Query(None, description="Required for doctors/admins"),
    current_user: User = Depends(get_current_user),
):
    """Two-or-more-report trend cards for the target patient."""
    await _require_verified_doctor_if_doctor(current_user)
    canonical_patient, lookup_ids, _ = await _resolve_target(current_user, patient_id)
    reports = await ReportRepository().list_all_for_patients(lookup_ids)
    summary = build_trend_summary(reports, patient_id=canonical_patient)

    ip, ua = client_info(request)
    await log_access(
        current_user.id,
        current_user.role,
        "read",
        "health_trends",
        None,
        canonical_patient,
        ip,
        ua,
    )
    return summary


@router.get("/{canonical_test}")
async def get_trend_detail(
    canonical_test: str,
    request: Request,
    patient_id: Optional[str] = Query(None, description="Required for doctors/admins"),
    current_user: User = Depends(get_current_user),
):
    """Full series, explanation, comparison, events and point table data."""
    await _require_verified_doctor_if_doctor(current_user)
    canonical = canonicalize_test_name(canonical_test)
    if canonical is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unknown test '{canonical_test}'. Supported: "
                f"{', '.join(sorted(REFERENCE_RANGES))}"
            ),
        )

    canonical_patient, lookup_ids, _ = await _resolve_target(current_user, patient_id)
    reports = await ReportRepository().list_all_for_patients(lookup_ids)
    series = build_test_series(reports, canonical)
    series["patient_id"] = canonical_patient

    ip, ua = client_info(request)
    await log_access(
        current_user.id,
        current_user.role,
        "read",
        "health_trend",
        canonical,
        canonical_patient,
        ip,
        ua,
    )
    return series


class TrendPointUpdate(BaseModel):
    excluded: Optional[bool] = None
    excluded_by_patient: Optional[bool] = None
    corrected_value: Optional[float] = Field(None, ge=0)
    value: Optional[float] = Field(None, ge=0, description="Alias for corrected_value")


@router.patch("/{canonical_test}/points/{report_id}")
async def update_trend_point(
    canonical_test: str,
    report_id: str,
    payload: TrendPointUpdate,
    request: Request,
    current_user: User = Depends(get_current_patient),
):
    """Patient-only exclusion/correction of one report's value for a test."""
    canonical = canonicalize_test_name(canonical_test)
    if canonical is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown test '{canonical_test}'",
        )

    canonical_patient, lookup_ids, _ = await _resolve_target(current_user, None)
    report_repo = ReportRepository()
    report = await report_repo.get_by_id(report_id)
    if report is None or report.patient_id not in lookup_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    excluded = (
        payload.excluded_by_patient
        if payload.excluded_by_patient is not None
        else payload.excluded
    )
    corrected = (
        payload.corrected_value
        if payload.corrected_value is not None
        else payload.value
    )
    if excluded is None and corrected is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide excluded_by_patient or corrected_value",
        )

    labs = [dict(lab) for lab in (report.lab_results or [])]
    target_index = next(
        (
            index
            for index, lab in enumerate(labs)
            if (lab.get("canonical_test") or lab.get("canonical_name")) == canonical
        ),
        None,
    )
    if target_index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This report does not contain the requested test",
        )

    try:
        labs[target_index] = apply_patient_point_update(
            labs[target_index],
            excluded_by_patient=excluded,
            corrected_value=corrected,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    updated = await report_repo.update(report_id, {"lab_results": labs})
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    reports = await ReportRepository().list_all_for_patients(lookup_ids)
    series = build_test_series(reports, canonical)
    series["patient_id"] = canonical_patient

    ip, ua = client_info(request)
    await log_access(
        current_user.id,
        current_user.role,
        "update",
        "health_trend_point",
        report_id,
        canonical_patient,
        ip,
        ua,
    )
    return {
        "report_id": report_id,
        "canonical_test": canonical,
        "lab_results": labs,
        "series": series,
    }
