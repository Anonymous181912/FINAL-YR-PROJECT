"""Patient-uploaded paper prescription storage.

The primary create flow stores the original file immediately as an
``source="patient_uploaded"``, ``verified=False`` record. It does not run OCR
or require medicine rows. Paper records never run interaction/allergy blocking
and never get a QR verification token.

The legacy scan/confirm helpers are kept for the old digitization screen, but
the simplified patient flow uses :meth:`create` directly.
"""

from __future__ import annotations

import io
import logging
import mimetypes
import os
import re
import shutil
import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from starlette.datastructures import UploadFile

from app.core.config import settings
from app.database.collections import PAPER_UPLOADS
from app.database.repositories.base_repository import BaseRepository
from app.database.repositories.patient_repository import PatientRepository
from app.database.repositories.prescription_repository import PrescriptionRepository
from app.prescriptions.services.scan_service import parse_prescription_scan
from app.reports.services.file_validation import FileValidationError, FileValidator

logger = logging.getLogger("healthcare_system")

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_DOCTOR_RE = re.compile(
    r"(?i:\b(?:dr\.?|doctor)\s*:?\s*)"
    r"([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){0,3})"
)
_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_NUMERIC_DATE_RE = re.compile(r"\b(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})\b")
_WORD_DATE_RE = re.compile(
    r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?\s+(\d{4})\b", re.IGNORECASE
)

PAPER_ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "pdf"}
PAPER_MAX_SIZE_MB = 10


class PaperPrescriptionError(Exception):
    pass


class PaperPrescriptionService:
    def __init__(self):
        self.validator = FileValidator()
        self.temp_repo = BaseRepository(PAPER_UPLOADS)
        self.rx_repo = PrescriptionRepository()
        self.patient_repo = PatientRepository()

    # ---- helpers -----------------------------------------------------
    @property
    def paper_dir(self) -> str:
        return os.path.join(self.validator.upload_dir, "paper_prescriptions")

    def _stored_path(self, filename: str) -> str:
        return os.path.join(self.paper_dir, filename)

    def _resolve_path(self, file_path: Optional[str]) -> Optional[str]:
        if not file_path:
            return None
        base = os.path.abspath(self.validator.upload_dir)
        target = os.path.abspath(file_path)
        if target != base and not target.startswith(base + os.sep):
            logger.warning("Refusing to access paper file outside upload dir: %s", file_path)
            return None
        return target

    def _remove_file(self, file_path: Optional[str]) -> None:
        target = self._resolve_path(file_path)
        if target and os.path.isfile(target):
            try:
                os.remove(target)
            except OSError as exc:
                logger.warning("Failed to remove paper prescription file %s: %s", target, exc)

    def _validate_create_file(self, file: UploadFile) -> str:
        filename = (getattr(file, "filename", None) or "").strip()
        if not filename:
            raise PaperPrescriptionError("Choose a file to upload.")

        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if ext not in PAPER_ALLOWED_EXTENSIONS:
            raise PaperPrescriptionError(
                "Unsupported file type. Upload a JPG, PNG, WEBP or PDF."
            )

        max_size = PAPER_MAX_SIZE_MB * 1024 * 1024
        size = getattr(file, "size", None)
        if size is not None and size > max_size:
            raise PaperPrescriptionError(
                f"File is too large. Maximum size is {PAPER_MAX_SIZE_MB} MB."
            )
        return ext

    @staticmethod
    def _media_type(extension: str) -> str:
        ext = (extension or "").lower().lstrip(".")
        known = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
            "pdf": "application/pdf",
        }
        return known.get(ext) or mimetypes.guess_type(f"file.{ext}")[0] or "application/octet-stream"

    async def _canonical_patient_id(self, patient_id: str) -> str:
        try:
            profile = await self.patient_repo.get_by_patient_id(patient_id)
        except Exception:
            profile = None
        if profile is None:
            return patient_id
        return (
            getattr(profile, "patient_id", None)
            or getattr(profile, "user_id", None)
            or getattr(profile, "id", None)
            or patient_id
        )

    async def _patient_identifiers(self, patient_id: str) -> set[str]:
        ids = {patient_id} if patient_id else set()
        try:
            profile = await self.patient_repo.get_by_user_id(patient_id)
        except Exception:
            profile = None
        if profile is not None:
            for value in (
                getattr(profile, "patient_id", None),
                getattr(profile, "user_id", None),
                getattr(profile, "id", None),
            ):
                if isinstance(value, str) and value:
                    ids.add(value)
        return ids

    @staticmethod
    def _coerce_datetime(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
        if isinstance(value, str) and value.strip():
            try:
                parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            except ValueError:
                return None
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        return None

    @staticmethod
    def _confidence(item: dict[str, Any]) -> float:
        value = item.get("confidence")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return max(0.0, min(1.0, round(float(value), 2)))
        missing = not all(
            str(item.get(key) or "").strip()
            for key in ("medicine_name", "dosage", "frequency", "duration")
        )
        return 0.45 if missing else 0.65

    @classmethod
    def _normalize_item(cls, item: dict[str, Any]) -> dict[str, Any]:
        normalized = {
            "medicine_name": str(item.get("medicine_name") or "").strip(),
            "dosage": str(item.get("dosage") or "").strip(),
            "frequency": str(item.get("frequency") or "").strip(),
            "duration": str(item.get("duration") or "").strip(),
            "instructions": str(item.get("instructions") or "").strip(),
            "route": item.get("route") or None,
            "confidence": cls._confidence(item),
            "needs_review": True,
        }
        return normalized

    @staticmethod
    def _detect_doctor_name(text: str) -> Optional[str]:
        for match in _DOCTOR_RE.finditer(text or ""):
            name = match.group(1).strip(" .,:;-")
            if name and name.upper() not in {"DR", "DOCTOR"}:
                return name[:200]
        return None

    @staticmethod
    def _safe_date(year: int, month: int, day: int) -> Optional[str]:
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None

    @classmethod
    def _detect_date(cls, text: str) -> Optional[str]:
        text = text or ""
        for match in _ISO_DATE_RE.finditer(text):
            value = cls._safe_date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            if value:
                return value

        for match in _WORD_DATE_RE.finditer(text):
            month = _MONTHS.get(match.group(2).lower())
            if month:
                value = cls._safe_date(int(match.group(3)), month, int(match.group(1)))
                if value:
                    return value

        for match in _NUMERIC_DATE_RE.finditer(text):
            first, second, year = (int(g) for g in match.groups())
            if year < 100:
                year += 2000
            # Prefer day/month (common on prescriptions) unless impossible.
            day, month = first, second
            if month > 12 and day <= 12:
                day, month = month, day
            value = cls._safe_date(year, month, day)
            if value:
                return value
        return None

    # ---- direct create -----------------------------------------------
    async def create(
        self,
        patient_id: str,
        file: UploadFile,
        prescriber_name: Optional[str] = None,
        prescription_date: Optional[date | datetime | str] = None,
        note: Optional[str] = None,
    ) -> Any:
        """Store the original upload and insert the paper record.

        No OCR, extraction, or medicine rows are involved. The patient owns the
        record via the authenticated id passed by the router.
        """
        ext = self._validate_create_file(file)
        content = await file.read()
        if not content:
            raise PaperPrescriptionError("The selected file is empty.")

        max_size = PAPER_MAX_SIZE_MB * 1024 * 1024
        if len(content) > max_size:
            raise PaperPrescriptionError(
                f"File is too large. Maximum size is {PAPER_MAX_SIZE_MB} MB."
            )

        if prescription_date is None:
            resolved_date = datetime.now(timezone.utc)
        else:
            resolved_date = self._coerce_datetime(prescription_date)
            if resolved_date is None:
                raise PaperPrescriptionError("Prescription date is not valid.")
            if resolved_date.tzinfo is None:
                resolved_date = resolved_date.replace(tzinfo=timezone.utc)
            if resolved_date.date() > datetime.now(timezone.utc).date():
                raise PaperPrescriptionError(
                    "Prescription date must be in the past, not in the future."
                )

        canonical_id = await self._canonical_patient_id(patient_id)
        original_name = (file.filename or "prescription").strip() or "prescription"
        final_name = f"paper_{uuid.uuid4().hex}.{ext}"
        os.makedirs(self.paper_dir, exist_ok=True)
        final_path = self._stored_path(final_name)
        with open(final_path, "wb") as buffer:
            buffer.write(content)

        try:
            return await self.rx_repo.create_prescription(
                patient_id=canonical_id,
                doctor_id="",
                prescription_date=resolved_date,
                diagnosis_notes=(note or "").strip() or None,
                items=[],
                status="issued",
                source="patient_uploaded",
                verified=False,
                confirmed_by_patient=True,
                prescriber_name=(prescriber_name or "").strip() or None,
                file_path=final_path,
                file_type=ext,
                original_file_name=original_name,
                safety_warnings=[],
                acknowledged_warnings=False,
            )
        except Exception:
            self._remove_file(final_path)
            raise

    async def get_file(self, prescription_id: str, patient_id: str) -> Optional[dict[str, str]]:
        prescription = await self.rx_repo.get_by_id(prescription_id)
        if not prescription:
            return None
        if getattr(prescription, "source", None) != "patient_uploaded":
            return None

        identifiers = await self._patient_identifiers(patient_id)
        if getattr(prescription, "patient_id", None) not in identifiers:
            return None

        file_path = self._resolve_path(getattr(prescription, "file_path", None))
        if not file_path or not os.path.isfile(file_path):
            return None

        file_type = (
            getattr(prescription, "file_type", None)
            or os.path.splitext(file_path)[1]
        )
        return {
            "path": file_path,
            "media_type": self._media_type(file_type),
        }

    # ---- legacy scan --------------------------------------------------
    async def scan(self, file: UploadFile, patient_id: str) -> dict[str, Any]:
        self.validator.validate(file)
        content = await file.read()
        if not content:
            raise FileValidationError("No file content provided")
        if len(content) > self.validator.max_size:
            max_mb = self.validator.max_size / (1024 * 1024)
            raise FileValidationError(
                f"File size exceeds maximum allowed size of {max_mb:.1f} MB"
            )

        original_name = file.filename or "prescription"
        ext = os.path.splitext(original_name)[1].lower() or ".png"
        temp_id = uuid.uuid4().hex
        temp_filename = f"tmp_{temp_id}{ext}"
        os.makedirs(self.paper_dir, exist_ok=True)
        temp_path = self._stored_path(temp_filename)
        with open(temp_path, "wb") as buffer:
            buffer.write(content)

        try:
            await self.temp_repo.create({
                "id": temp_id,
                "patient_id": patient_id,
                "file_path": temp_path,
                "original_filename": original_name,
                "file_size": len(content),
                "created_at": datetime.now(timezone.utc),
            })
        except Exception:
            self._remove_file(temp_path)
            raise

        try:
            draft = await parse_prescription_scan(
                UploadFile(filename=original_name, file=io.BytesIO(content))
            )
        except Exception:
            self._remove_file(temp_path)
            try:
                await self.temp_repo.delete(temp_id)
            except Exception:
                pass
            raise

        raw_text = str(draft.get("raw_text") or "")
        items = [self._normalize_item(item) for item in draft.get("items") or []]
        extraction_method = str(draft.get("extraction_method") or "")
        detected_doctor_name = self._detect_doctor_name(raw_text)
        detected_prescription_date = self._detect_date(raw_text)
        # Keep the detected values with the temporary upload so confirm can
        # fall back to them when the patient leaves the optional fields blank.
        try:
            await self.temp_repo.update(temp_id, {
                "detected_doctor_name": detected_doctor_name,
                "detected_prescription_date": detected_prescription_date,
            })
        except Exception as exc:
            logger.warning("Failed to store detected paper fields: %s", exc)
        return {
            "temp_upload_id": temp_id,
            "original_filename": original_name,
            "ocr_used": extraction_method.startswith("ocr+"),
            "raw_text": raw_text,
            "items": items,
            "detected_doctor_name": detected_doctor_name,
            "detected_prescription_date": detected_prescription_date,
            "extraction_method": extraction_method,
            "note": (
                "Handwriting OCR is often imperfect. Check every row against the "
                "paper before saving. Nothing has been added to your history yet."
            ),
        }

    # ---- confirm -----------------------------------------------------
    async def confirm(self, patient_id: str, payload) -> Any:
        if not payload.confirmed_by_patient:
            raise PaperPrescriptionError(
                "Please tick the confirmation that you checked these details "
                "against the paper prescription."
            )

        temp = await self.temp_repo.get_by_id(payload.temp_upload_id)
        if not temp or temp.get("patient_id") != patient_id:
            raise PaperPrescriptionError("Upload not found or expired. Please scan again.")

        prescriber_name = (payload.prescriber_name or "").strip()
        if not prescriber_name:
            prescriber_name = str(temp.get("detected_doctor_name") or "").strip()
        prescriber_name = prescriber_name or None

        prescription_date = payload.prescription_date
        if prescription_date is None:
            prescription_date = self._coerce_datetime(temp.get("detected_prescription_date"))
        if prescription_date is None:
            prescription_date = datetime.now(timezone.utc)
        elif prescription_date.tzinfo is None:
            prescription_date = prescription_date.replace(tzinfo=timezone.utc)

        temp_path = self._resolve_path(temp.get("file_path"))
        if not temp_path or not os.path.isfile(temp_path):
            raise PaperPrescriptionError("Stored upload is no longer available. Please scan again.")

        items = [item.model_dump() for item in payload.items]
        if not items:
            raise PaperPrescriptionError("At least one medicine row is required.")

        note = (payload.note or "").strip() or None

        canonical_id = await self._canonical_patient_id(patient_id)
        ext = os.path.splitext(temp_path)[1].lower()
        final_name = f"paper_{uuid.uuid4().hex}{ext}"
        final_path = self._stored_path(final_name)
        try:
            shutil.move(temp_path, final_path)
        except OSError as exc:
            logger.error("Failed to move paper upload into permanent storage: %s", exc)
            raise PaperPrescriptionError("Could not store the uploaded file. Please try again.")

        try:
            record = await self.rx_repo.create_prescription(
                patient_id=canonical_id,
                doctor_id="",
                prescription_date=prescription_date,
                diagnosis_notes=note,
                items=items,
                status="issued",
                source="patient_uploaded",
                verified=False,
                confirmed_by_patient=True,
                prescriber_name=prescriber_name,
                file_path=final_path,
                original_file_name=temp.get("original_filename"),
                safety_warnings=[],
                acknowledged_warnings=False,
            )
        except Exception:
            self._remove_file(final_path)
            raise

        try:
            await self.temp_repo.delete(payload.temp_upload_id)
        except Exception as exc:
            logger.warning("Failed to delete temporary paper upload record: %s", exc)

        return record

    # ---- delete ------------------------------------------------------
    async def delete(self, prescription_id: str, patient_id: str) -> bool:
        prescription = await self.rx_repo.get_by_id(prescription_id)
        if not prescription:
            return False
        if getattr(prescription, "source", None) != "patient_uploaded":
            return False

        identifiers = await self._patient_identifiers(patient_id)
        if getattr(prescription, "patient_id", None) not in identifiers:
            return False

        self._remove_file(getattr(prescription, "file_path", None))
        return await self.rx_repo.delete(prescription_id)
