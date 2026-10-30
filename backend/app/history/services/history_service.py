from typing import Optional, Any
from datetime import datetime, timezone
from app.models.history_event import HistoryEvent, HistoryEventType
from app.database.repositories.report_repository import ReportRepository
from app.database.repositories.prescription_repository import PrescriptionRepository
from app.database.repositories.patient_repository import PatientRepository
from app.database.repositories.doctor_repository import DoctorRepository


class HistoryServiceError(Exception):
    pass


class HistoryService:
    def __init__(self):
        self.report_repo = ReportRepository()
        self.prescription_repo = PrescriptionRepository()
        self.patient_repo = PatientRepository()
        self.doctor_repo = DoctorRepository()

    async def _resolve_patient(self, patient_id: str):
        patient = await self.patient_repo.get_by_patient_id(patient_id)
        if not patient:
            raise HistoryServiceError("Patient not found")
        return patient

    async def get_patient_history(
        self,
        patient_id: str,
        order: str = "desc",
        limit: int = 50,
    ) -> list[HistoryEvent]:
        patient = await self._resolve_patient(patient_id)
        # Reports/prescriptions are keyed by the canonical patient_id (the
        # user UUID); callers may pass the profile id or user id instead.
        canonical_id = patient.patient_id or patient.user_id or patient.id

        reports = await self.report_repo.list_by_patient(canonical_id, limit=limit)
        prescriptions = await self.prescription_repo.list_by_patient(canonical_id, limit=limit)

        events: list[HistoryEvent] = []

        for report in reports:
            event_date = report.created_at
            events.append(
                HistoryEvent(
                    event_id=str(report.id),
                    patient_id=str(report.patient_id),
                    event_type="REPORT",
                    event_date=event_date,
                    title=str(report.title),
                    summary=f"Report uploaded • {report.status}",
                    source_id=str(report.id),
                    source_reference=f"/reports/{report.id}",
                    created_at=report.created_at,
                )
            )

        for prescription in prescriptions:
            event_date = prescription.prescription_date or prescription.created_at
            source_value = getattr(prescription, "source", "doctor_issued")
            if not isinstance(source_value, str):
                source_value = "doctor_issued"
            verified_value = getattr(prescription, "verified", True)
            if not isinstance(verified_value, bool):
                verified_value = True
            medicine_count = len(prescription.items) if prescription.items else 0

            if source_value == "patient_uploaded":
                prescriber = getattr(prescription, "prescriber_name", None)
                prescriber = prescriber.strip() if isinstance(prescriber, str) else ""
                title = "Paper Prescription"
                summary = "Patient-uploaded \u00b7 not verified by a doctor"
                if prescriber:
                    summary += f" \u00b7 prescriber: {prescriber}"
                if medicine_count:
                    summary += f" \u00b7 {medicine_count} medicine(s)"
            else:
                doctor_name = "Doctor"
                try:
                    doctor = await self.doctor_repo.get_by_doctor_id(prescription.doctor_id)
                    if doctor:
                        doctor_name = doctor.full_name or doctor_name
                except Exception:
                    pass
                title = "Digital Prescription"
                summary = f"Prescription issued by {doctor_name}"
                if medicine_count:
                    summary += f" \u00b7 {medicine_count} medicine(s)"

            events.append(
                HistoryEvent(
                    event_id=str(prescription.id),
                    patient_id=str(prescription.patient_id),
                    event_type="PRESCRIPTION",
                    event_date=event_date,
                    title=title,
                    summary=summary,
                    source_id=str(prescription.id),
                    source_reference=f"/prescriptions/{prescription.id}",
                    source=source_value,
                    verified=verified_value,
                    created_at=prescription.created_at,
                )
            )

        events.sort(key=lambda e: e.event_date or datetime.min.replace(tzinfo=timezone.utc), reverse=(order != "asc"))
        return events
