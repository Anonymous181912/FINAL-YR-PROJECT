import os
import logging
from typing import Optional
from fastapi import UploadFile
from app.core.config import settings
from app.reports.services.file_validation import FileValidator, FileValidationError
from app.reports.services.pdf_extraction import PDFExtractionService, PDFExtractionError
from app.reports.services.normalization import TextNormalizationService
from app.reports.ai.ocr import OCRService, OCRServiceError
from app.reports.ai.medical_nlp import MedicalNLPService, MedicalNLPError
from app.reports.ai.llm import LLMService, LLMServiceError
from app.schemas.ai_interpretation import LLMInterpretationResponse
from app.database.repositories.report_repository import ReportRepository
from app.models.report import ReportCreate, ReportUpdate, ReportInDB

logger = logging.getLogger("healthcare_system")


class ReportServiceError(Exception):
    pass


class ReportService:
    def __init__(self):
        self.validator = FileValidator()
        self.pdf_service = PDFExtractionService()
        self.normalizer = TextNormalizationService()
        self.ocr_service = OCRService()
        self.nlp_service = MedicalNLPService()
        self.report_repo = ReportRepository()

    def _resolve_upload_path(self, file_path: Optional[str]) -> Optional[str]:
        """Resolve a stored report file to an absolute path inside the upload dir.

        Returns None when there is no path or it escapes the upload directory
        (path traversal guard) — the DB record can still be deleted safely.
        """
        if not file_path:
            return None
        base_dir = os.path.abspath(settings.upload_dir)
        # Stored paths are written relative to the server working directory
        # (e.g. "uploads/<uuid>.txt"), so resolve against the CWD — never
        # re-anchor them inside the upload dir (that would double the prefix
        # and silently skip deletion).
        resolved = os.path.abspath(file_path)
        if resolved != base_dir and not resolved.startswith(base_dir + os.sep):
            logger.warning(f"Refusing to delete file outside upload dir: {file_path}")
            return None
        return resolved

    async def delete_report(self, report: ReportInDB) -> bool:
        """Delete a report document and its uploaded file (if present).

        AI analysis is embedded in the report document, so removing the
        document removes the analysis as well; history is derived from the
        reports collection and reflects the deletion automatically.
        A missing file never blocks the database deletion.
        """
        target = self._resolve_upload_path(report.file_path)
        if target and os.path.isfile(target):
            try:
                os.remove(target)
            except OSError as exc:
                logger.warning(f"Failed to remove report file {target}: {exc}")
        return await self.report_repo.delete(report.id)

    async def get_report_for_patient(
        self, report_id: str, requester_id: str, requester_role: Optional[str] = None
    ) -> Optional[ReportInDB]:
        report = await self.report_repo.get_by_id(report_id)
        if not report:
            return None
        # Doctors review patient reports as part of the clinical workflow
        # (consistent with the doctor-visible patient directory); patients may
        # only read their own reports.
        if requester_role == "doctor":
            return report
        if report.patient_id != requester_id:
            return None
        return report

    async def interpret_report(self, report: ReportInDB, language: str = "en") -> LLMInterpretationResponse:
        if not report.extracted_text and not report.entities:
            raise ReportServiceError("Report does not have extracted text or entities")

        structured_data = {
            "report_category": report.category,
            "report_title": report.title,
            "extracted_text": report.extracted_text,
            "entities": report.entities,
            "measurements": [e for e in report.entities if e.get("type") == "measurement"],
            "findings": [e for e in report.entities if e.get("type") == "finding"],
            "diseases": [e for e in report.entities if e.get("type") == "disease"],
            "symptoms": [e for e in report.entities if e.get("type") == "symptom"],
            "medications": [e for e in report.entities if e.get("type") == "medication"],
        }

        # Phase 4e: per-feature model override for interpretation.
        from app.core.config import settings

        model = settings.llm_model_interpret or None
        llm_service = LLMService(model=model)
        try:
            interpretation = await llm_service.interpret_report(structured_data, language=language)
            # Phase 4a: verify each source quote against the extracted text.
            try:
                from app.reports.ai.quote_verify import verify_findings

                verify_findings(interpretation.key_findings, report.extracted_text or "")
            except Exception as exc:
                logger.warning(f"Quote verification failed (non-fatal): {exc}")
            ai_interpretation = interpretation.model_dump()
            ai_status = "success"
        except LLMServiceError as exc:
            logger.error(f"LLM interpretation failed: {exc}")
            ai_interpretation = None
            ai_status = "failed"
            raise

        updated = await self.report_repo.update_ai(
            report_id=report.id,
            ai_interpretation=ai_interpretation,
            ai_status=ai_status,
        )
        if not updated:
            raise ReportServiceError("Failed to update report with AI interpretation")

        return interpretation

    async def process_upload(self, file: UploadFile, patient_id: str, category: str, title: str) -> dict:
        self.validator.validate(file)
        safe_filename = self.validator.generate_safe_filename(file.filename)
        full_path = self.validator.get_full_path(safe_filename)

        file_size = 0
        extraction_method = "text"
        extracted_text = ""
        ocr_used = False
        error_message = None
        status = "completed"

        try:
            with open(full_path, "wb") as buffer:
                content = await file.read()
                file_size = len(content)
                buffer.write(content)

            ext = os.path.splitext(safe_filename)[1].lower().lstrip(".")

            if ext == "txt":
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    extracted_text = f.read()
                extraction_method = "text"
            elif ext == "pdf":
                if self.pdf_service.has_embedded_text(full_path):
                    extracted_text = self.pdf_service.extract_text(full_path)
                    extraction_method = "text"
                else:
                    extraction_method = "ocr"
                    ocr_used = True
                    extracted_text = await self.ocr_service.extract_text(full_path)
            else:
                extraction_method = "ocr"
                ocr_used = True
                extracted_text = await self.ocr_service.extract_text(full_path)

            extracted_text = self.normalizer.normalize(extracted_text)

            if not extracted_text.strip():
                status = "completed"
                extracted_text = ""

        except FileValidationError:
            raise
        except (PDFExtractionError, OCRServiceError) as exc:
            logger.error(f"Extraction failed: {exc}")
            status = "failed"
            error_message = str(exc)
            extracted_text = ""
            extraction_method = extraction_method or "text"
        except Exception as exc:
            logger.error(f"Unexpected error during upload processing: {exc}", exc_info=True)
            status = "failed"
            error_message = "Unexpected processing error"
            extracted_text = ""

        entities = []
        nlp_status = "pending"
        if status == "completed" and extracted_text.strip():
            try:
                entities = await self.nlp_service.extract_entities(extracted_text)
                nlp_status = "completed"
            except MedicalNLPError as exc:
                logger.error(f"NLP extraction failed: {exc}")
                nlp_status = "failed"
                if not error_message:
                    error_message = "NLP processing failed"
        elif status == "completed" and not extracted_text.strip():
            nlp_status = "completed"

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        # Phase 1: deterministic lab parsing (never breaks the upload).
        lab_results: list[dict] = []
        if status == "completed" and extracted_text.strip():
            try:
                lab_results = await self._parse_labs(extracted_text, patient_id)
            except Exception as exc:
                logger.warning(f"Lab parsing failed (non-fatal): {exc}")

        report = await self.report_repo.create_report(
            patient_id=patient_id,
            category=category,
            title=title,
            file_path=full_path,
            file_name=file.filename,
            file_size=file_size,
            extraction_method=extraction_method,
            extracted_text=extracted_text,
            ocr_used=ocr_used,
            status=status,
            error_message=error_message,
            entities=entities,
            lab_results=lab_results,
            nlp_status=nlp_status,
            nlp_processed_at=now if nlp_status == "completed" else None,
            processed_at=now if status == "completed" else None,
        )

        return {
            "id": report.id,
            "patient_id": report.patient_id,
            "category": report.category,
            "title": report.title,
            "file_name": report.file_name,
            "file_size": report.file_size,
            "extraction_method": report.extraction_method,
            "ocr_used": report.ocr_used,
            "extracted_text": report.extracted_text,
            "status": report.status,
            "error_message": report.error_message,
            "entities": report.entities,
            "lab_results": report.lab_results or [],
            "nlp_status": report.nlp_status,
            "ai_status": report.ai_status,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "updated_at": report.updated_at.isoformat() if report.updated_at else None,
        }

    async def _parse_labs(self, extracted_text: str, patient_id: str) -> list[dict]:
        """Parse lab values using the patient's gender/age for table ranges."""
        from datetime import datetime, timezone

        from app.database.repositories.patient_repository import PatientRepository
        from app.reports.services.lab_parser import parse_lab_results

        gender = None
        age_years = None
        try:
            repo = PatientRepository()
            profile = await repo.get_by_user_id(patient_id)
            if profile is None:
                profile = await repo.get_by_patient_id(patient_id)
            if profile is not None:
                gender = profile.gender
                if profile.date_of_birth:
                    dob = profile.date_of_birth
                    if dob.tzinfo is None:
                        dob = dob.replace(tzinfo=timezone.utc)
                    age_years = (datetime.now(timezone.utc) - dob).days / 365.25
        except Exception as exc:
            logger.warning(f"Patient lookup for lab parsing failed (non-fatal): {exc}")
        return parse_lab_results(extracted_text, gender=gender, age_years=age_years)

    # ---- Phase 4d: background processing ---------------------------------
    async def save_incoming_file(self, file: UploadFile) -> tuple[str, int]:
        """Validate + persist upload bytes. Returns (full_path, file_size)."""
        self.validator.validate(file)
        safe_filename = self.validator.generate_safe_filename(file.filename)
        full_path = self.validator.get_full_path(safe_filename)
        content = await file.read()
        with open(full_path, "wb") as buffer:
            buffer.write(content)
        return full_path, len(content)

    async def create_pending_record(
        self, patient_id: str, category: str, title: str,
        file: UploadFile, full_path: str, file_size: int,
    ) -> ReportInDB:
        return await self.report_repo.create_report(
            patient_id=patient_id,
            category=category,
            title=title,
            file_path=full_path,
            file_name=file.filename,
            file_size=file_size,
            extraction_method="text",
            extracted_text="",
            ocr_used=False,
            status="processing",
            error_message=None,
            entities=[],
            lab_results=[],
            nlp_status="processing",
        )

    async def process_saved_file(self, report_id: str, full_path: str, patient_id: str) -> None:
        """Background worker: extraction + NLP + labs, then flip the record."""
        import os as _os

        from datetime import datetime, timezone

        ext = _os.path.splitext(full_path)[1].lower().lstrip(".")
        extraction_method = "text"
        extracted_text = ""
        ocr_used = False
        error_message = None
        status = "completed"
        try:
            if ext == "txt":
                with open(full_path, "r", encoding="utf-8", errors="replace") as fh:
                    extracted_text = fh.read()
            elif ext == "pdf":
                if self.pdf_service.has_embedded_text(full_path):
                    extracted_text = self.pdf_service.extract_text(full_path)
                else:
                    extraction_method = "ocr"
                    ocr_used = True
                    extracted_text = await self.ocr_service.extract_text(full_path)
            else:
                extraction_method = "ocr"
                ocr_used = True
                extracted_text = await self.ocr_service.extract_text(full_path)
            extracted_text = self.normalizer.normalize(extracted_text)
            if not extracted_text.strip():
                extracted_text = ""
        except FileValidationError:
            raise
        except (PDFExtractionError, OCRServiceError) as exc:
            logger.error(f"Background extraction failed: {exc}")
            status = "failed"
            error_message = str(exc)
            extracted_text = ""
        except Exception as exc:
            logger.error(f"Background processing failed: {exc}", exc_info=True)
            status = "failed"
            error_message = "Unexpected processing error"
            extracted_text = ""

        entities: list = []
        nlp_status = "pending"
        if status == "completed" and extracted_text.strip():
            try:
                entities = await self.nlp_service.extract_entities(extracted_text)
                nlp_status = "completed"
            except MedicalNLPError as exc:
                logger.error(f"Background NLP failed: {exc}")
                nlp_status = "failed"
                if not error_message:
                    error_message = "NLP processing failed"
        elif status == "completed":
            nlp_status = "completed"

        lab_results: list[dict] = []
        if status == "completed" and extracted_text.strip():
            try:
                lab_results = await self._parse_labs(extracted_text, patient_id)
            except Exception as exc:
                logger.warning(f"Background lab parsing failed (non-fatal): {exc}")

        now = datetime.now(timezone.utc)
        await self.report_repo.update_processing(
            report_id,
            extraction_method=extraction_method,
            extracted_text=extracted_text,
            ocr_used=ocr_used,
            status=status,
            error_message=error_message,
            entities=entities,
            lab_results=lab_results,
            nlp_status=nlp_status,
            nlp_processed_at=now if nlp_status == "completed" else None,
            processed_at=now if status == "completed" else None,
        )

    @staticmethod
    def to_response_dict(report: ReportInDB) -> dict:
        return {
            "id": report.id,
            "patient_id": report.patient_id,
            "category": report.category,
            "title": report.title,
            "file_name": report.file_name,
            "file_size": report.file_size,
            "extraction_method": report.extraction_method,
            "ocr_used": report.ocr_used,
            "extracted_text": report.extracted_text,
            "status": report.status,
            "error_message": report.error_message,
            "entities": report.entities,
            "lab_results": report.lab_results or [],
            "nlp_status": report.nlp_status,
            "ai_status": report.ai_status,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "updated_at": report.updated_at.isoformat() if report.updated_at else None,
        }
