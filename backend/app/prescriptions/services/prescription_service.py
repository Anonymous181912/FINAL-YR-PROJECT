import hashlib
import hmac
import json
import os
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional
from app.core.config import settings
from app.database.repositories.prescription_repository import PrescriptionRepository
from app.database.repositories.patient_repository import PatientRepository
from app.database.repositories.doctor_repository import DoctorRepository
from app.prescriptions.services.pdf_service import PrescriptionPDFService, PrescriptionPDFError
from app.prescriptions.services.safety_service import SafetyService
from app.models.prescription import PrescriptionInDB

logger = logging.getLogger("healthcare_system")


class PrescriptionServiceError(Exception):
    pass


def _content_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hmac.new(settings.secret_key.encode(), canonical.encode(), hashlib.sha256).hexdigest()


def _item_payload(item) -> dict:
    keys = ("medicine_name", "dosage", "frequency", "duration", "route", "instructions", "quantity", "timings")
    if isinstance(item, dict):
        return {k: item.get(k) for k in keys}
    get = getattr
    if hasattr(item, "model_dump"):
        try:
            dumped = item.model_dump()
            return {k: dumped.get(k) for k in keys}
        except Exception:
            pass
    return {k: get(item, k, None) for k in keys}


def verification_payload(prescription) -> dict:
    """Clinical content covered by the tamper-evident HMAC (no meta fields)."""
    if isinstance(prescription, dict):
        items = prescription.get("items") or []
        get = lambda _o, k: prescription.get(k)
    else:
        items = prescription.items or []
        get = lambda _o, k: getattr(_o, k, None)
    return {
        "patient_id": get(prescription, "patient_id"),
        "doctor_id": get(prescription, "doctor_id"),
        "prescription_date": str(get(prescription, "prescription_date")),
        "diagnosis_notes": get(prescription, "diagnosis_notes"),
        "advice": get(prescription, "advice"),
        "follow_up_date": str(get(prescription, "follow_up_date")),
        "items": [_item_payload(i) for i in items],
    }


class PrescriptionService:
    def __init__(self):
        self.repo = PrescriptionRepository()
        self.patient_repo = PatientRepository()
        self.doctor_repo = DoctorRepository()
        self.pdf_service = PrescriptionPDFService()

    async def create_prescription(self, doctor_id: str, patient_id: str, prescription_date: Optional[datetime], **kwargs) -> PrescriptionInDB:
        patient = await self.patient_repo.get_by_patient_id(patient_id)
        if not patient:
            raise PrescriptionServiceError("Patient not found")

        doctor = await self.doctor_repo.get_by_doctor_id(doctor_id)
        if not doctor:
            raise PrescriptionServiceError("Doctor profile not found")

        items = kwargs.get("items") or []
        acknowledge = bool(kwargs.pop("acknowledge_warnings", False))
        ack_reason = kwargs.pop("ack_reason", None)
        allergies = list(getattr(patient, "allergies", None) or [])

        safety = SafetyService()
        warnings = safety.check(items, allergies)
        if safety.blocks_issuing(warnings) and not (acknowledge and (ack_reason or "").strip()):
            raise PrescriptionServiceError(
                "Severe medication safety warnings must be acknowledged with a reason before saving. "
                f"Warnings: {'; '.join(w.get('note', '') for w in warnings if w.get('severity') == 'severe')}"
            )

        token = secrets.token_urlsafe(24)
        prescription_date = prescription_date or datetime.now(timezone.utc)
        data = {
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "prescription_date": prescription_date,
            "safety_warnings": warnings,
            "acknowledged_warnings": acknowledge,
            "ack_reason": (ack_reason or "").strip() or None,
            "verification_token": token,
            "verification_status": "valid",
            **kwargs,
        }
        # Tamper-evident hash over the final clinical content (single DB call).
        data["verification_hash"] = _content_hash(verification_payload(data))
        prescription = await self.repo.create_prescription(**data)
        return prescription

    async def get_prescription(self, prescription_id: str, requester_id: str, requester_role: str) -> Optional[PrescriptionInDB]:
        prescription = await self.repo.get_by_id(prescription_id)
        if not prescription:
            return None

        if requester_role == "doctor" and prescription.doctor_id != requester_id:
            return None
        if requester_role == "patient" and prescription.patient_id != requester_id:
            return None

        return prescription

    async def update_prescription(self, prescription_id: str, doctor_id: str, **kwargs) -> Optional[PrescriptionInDB]:
        prescription = await self.repo.get_by_id(prescription_id)
        if not prescription:
            return None
        if prescription.doctor_id != doctor_id:
            return None

        acknowledge = bool(kwargs.pop("acknowledge_warnings", False))
        ack_reason = kwargs.pop("ack_reason", None)

        new_items = kwargs.get("items", None)
        items_for_check = new_items if new_items is not None else (prescription.items or [])
        target_status = kwargs.get("status", prescription.status)

        safety = SafetyService()
        allergies: list[str] = []
        try:
            patient = await self.patient_repo.get_by_patient_id(prescription.patient_id)
            allergies = list(getattr(patient, "allergies", None) or [])
        except Exception:
            allergies = []
        warnings = safety.check(
            [i if isinstance(i, dict) else i.model_dump() for i in items_for_check],
            allergies,
        )
        if safety.blocks_issuing(warnings) and str(target_status).lower() == "issued":
            if not (acknowledge and (ack_reason or "").strip()):
                raise PrescriptionServiceError(
                    "Severe medication safety warnings must be acknowledged with a reason before issuing. "
                    f"Warnings: {'; '.join(w.get('note', '') for w in warnings if w.get('severity') == 'severe')}"
                )

        update_data = dict(kwargs)
        if new_items is not None:
            update_data["safety_warnings"] = warnings
            update_data["acknowledged_warnings"] = acknowledge
            if ack_reason:
                update_data["ack_reason"] = ack_reason.strip()
        if str(target_status).lower() == "issued" and not prescription.issued_at:
            update_data["issued_at"] = datetime.now(timezone.utc)

        updated = await self.repo.update_prescription(prescription_id, **update_data)
        if not updated:
            return None
        # Refresh tamper-evident hash whenever clinical content may have changed.
        if new_items is not None or any(k in update_data for k in ("diagnosis_notes", "advice", "follow_up_date", "prescription_date")):
            refreshed = await self.repo.update_prescription(
                prescription_id,
                verification_hash=_content_hash(verification_payload(updated)),
            )
            return refreshed or updated
        return updated

    async def delete_prescription(self, prescription_id: str, doctor_id: str) -> bool:
        prescription = await self.repo.get_by_id(prescription_id)
        if not prescription:
            return False
        if prescription.doctor_id != doctor_id:
            return False

        pdf_path = prescription.file_path
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except OSError:
                logger.warning(f"Failed to delete PDF file: {pdf_path}")

        result = await self.repo.delete(prescription_id)
        return result

    async def revoke_prescription(self, prescription_id: str, doctor_id: str) -> Optional[PrescriptionInDB]:
        prescription = await self.repo.get_by_id(prescription_id)
        if not prescription:
            return None
        if prescription.doctor_id != doctor_id:
            return None
        return await self.repo.update_prescription(
            prescription_id,
            verification_status="revoked",
            revoked_at=datetime.now(timezone.utc),
        )

    async def get_by_token(self, token: str) -> Optional[PrescriptionInDB]:
        return await self.repo.get_by_token(token)

    def verify_token(self, prescription: PrescriptionInDB) -> str:
        """valid | revoked | modified (public-safe; no PHI)."""
        if prescription.verification_status == "revoked":
            return "revoked"
        expected = _content_hash(verification_payload(prescription))
        if not prescription.verification_hash or expected != prescription.verification_hash:
            return "modified"
        return "valid"

    async def list_doctor_prescriptions(self, doctor_id: str, skip: int = 0, limit: int = 20) -> list[PrescriptionInDB]:
        return await self.repo.list_by_doctor(doctor_id, skip=skip, limit=limit)

    async def list_patient_prescriptions(self, patient_id: str, skip: int = 0, limit: int = 20) -> list[PrescriptionInDB]:
        return await self.repo.list_by_patient(patient_id, skip=skip, limit=limit)

    async def generate_pdf(self, prescription: PrescriptionInDB) -> str:
        patient = await self.patient_repo.get_by_patient_id(prescription.patient_id)
        doctor = await self.doctor_repo.get_by_doctor_id(prescription.doctor_id)

        verify_url = None
        if prescription.verification_token:
            verify_url = f"{settings.frontend_url.rstrip('/')}/verify/{prescription.verification_token}"
        try:
            pdf_path = self.pdf_service.generate(prescription, patient, doctor, verify_url=verify_url)
        except Exception as exc:
            logger.error(f"PDF generation failed: {exc}")
            raise PrescriptionServiceError("PDF generation failed") from exc

        updated = await self.repo.update_prescription(
            prescription.id,
            file_path=pdf_path,
        )
        if not updated:
            raise PrescriptionServiceError("Failed to update prescription with PDF path")

        return pdf_path
