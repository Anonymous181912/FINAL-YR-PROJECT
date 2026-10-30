import io
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.history.services.history_service import HistoryService
from app.main import app
from app.models.prescription import PrescriptionInDB
from app.prescriptions.services.paper_prescription_service import (
    PaperPrescriptionError,
    PaperPrescriptionService,
)
from app.prescriptions.services.scan_service import parse_prescription_scan
from app.schemas.prescription import PaperPrescriptionConfirm, PrescriptionItemCreate

client = TestClient(app)


def _user(role="patient", user_id="user-1"):
    return SimpleNamespace(
        id=user_id,
        email=f"{role}@test.com",
        role=role,
        full_name="Test User",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _payload(confirmed=True, temp_upload_id="temp-1", patient_name="Dr. Smith"):
    return PaperPrescriptionConfirm(
        temp_upload_id=temp_upload_id,
        prescriber_name=patient_name,
        prescription_date=datetime(2026, 10, 28, tzinfo=timezone.utc),
        items=[
            PrescriptionItemCreate(
                medicine_name="Aspirin",
                dosage="100mg",
                frequency="OD",
                duration="3 days",
            )
        ],
        confirmed_by_patient=confirmed,
    )


def _paper_record(file_path=None):
    now = datetime.now(timezone.utc)
    return PrescriptionInDB(
        id="rx-paper",
        patient_id="patient-1",
        doctor_id="",
        prescription_date=now,
        items=[
            {
                "medicine_name": "Aspirin",
                "dosage": "100mg",
                "frequency": "OD",
                "duration": "3 days",
            }
        ],
        status="issued",
        source="patient_uploaded",
        verified=False,
        confirmed_by_patient=True,
        prescriber_name="Dr. Smith",
        file_path=file_path,
        original_file_name="paper.txt",
        created_at=now,
        updated_at=now,
    )


def _service(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    return PaperPrescriptionService()


@pytest.mark.asyncio
async def test_scan_saves_only_a_temporary_upload(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    service.temp_repo = AsyncMock()
    service.rx_repo = AsyncMock()
    draft = {
        "extraction_method": "ocr+rule-based",
        "raw_text": "Dr. Smith\n2026-10-28\nAspirin 100mg OD for 3 days",
        "items": [
            {
                "medicine_name": "Aspirin",
                "dosage": "100mg",
                "frequency": "OD",
                "duration": "3 days",
                "confidence": 0.82,
            }
        ],
    }

    with patch(
        "app.prescriptions.services.paper_prescription_service.parse_prescription_scan",
        new=AsyncMock(return_value=draft),
    ):
        result = await service.scan(
            UploadFile(file=io.BytesIO(b"paper"), filename="scan.txt"),
            "user-1",
        )

    assert result["temp_upload_id"]
    assert result["ocr_used"] is True
    assert result["items"][0]["confidence"] == 0.82
    assert result["items"][0]["needs_review"] is True
    assert result["detected_doctor_name"] == "Smith"
    assert result["detected_prescription_date"] == "2026-10-28"
    assert service.temp_repo.create.await_count == 1
    assert service.rx_repo.create_prescription.await_count == 0
    assert len(list((tmp_path / "paper_prescriptions").iterdir())) == 1


@pytest.mark.asyncio
async def test_scan_removes_temp_file_when_extraction_fails(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    service.temp_repo = AsyncMock()
    service.temp_repo.delete.return_value = True

    with patch(
        "app.prescriptions.services.paper_prescription_service.parse_prescription_scan",
        new=AsyncMock(side_effect=ValueError("OCR failed")),
    ):
        with pytest.raises(ValueError, match="OCR failed"):
            await service.scan(
                UploadFile(file=io.BytesIO(b"paper"), filename="scan.txt"),
                "user-1",
            )

    assert list((tmp_path / "paper_prescriptions").iterdir()) == []
    service.temp_repo.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirm_requires_patient_confirmation(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    service.temp_repo = AsyncMock()
    service.rx_repo = AsyncMock()

    with pytest.raises(PaperPrescriptionError, match="tick the confirmation"):
        await service.confirm("user-1", _payload(confirmed=False))

    service.temp_repo.get_by_id.assert_not_awaited()
    service.rx_repo.create_prescription.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirm_blank_optional_fields_fall_back_to_detected_values(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    paper_dir = tmp_path / "paper_prescriptions"
    paper_dir.mkdir(parents=True)
    temp_path = paper_dir / "tmp_1.txt"
    temp_path.write_bytes(b"paper")

    service.temp_repo = AsyncMock()
    service.temp_repo.get_by_id.return_value = {
        "id": "temp-1",
        "patient_id": "user-1",
        "file_path": str(temp_path),
        "original_filename": "scan.txt",
        "detected_doctor_name": "Dr. Detected",
        "detected_prescription_date": "2026-10-20",
    }
    service.temp_repo.delete.return_value = True
    service.patient_repo = AsyncMock()
    service.patient_repo.get_by_patient_id.return_value = None
    service.rx_repo = AsyncMock()
    service.rx_repo.create_prescription.return_value = _paper_record()

    payload = _payload(patient_name="   ").model_copy(update={"prescription_date": None})
    await service.confirm("user-1", payload)

    kwargs = service.rx_repo.create_prescription.await_args.kwargs
    assert kwargs["prescriber_name"] == "Dr. Detected"
    assert kwargs["prescription_date"].date().isoformat() == "2026-10-20"
    assert kwargs["diagnosis_notes"] is None


@pytest.mark.asyncio
async def test_confirm_stores_unverified_paper_record_without_qr_or_safety(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    paper_dir = tmp_path / "paper_prescriptions"
    paper_dir.mkdir(parents=True)
    temp_path = paper_dir / "tmp_1.txt"
    temp_path.write_bytes(b"paper")

    service.temp_repo = AsyncMock()
    service.temp_repo.get_by_id.return_value = {
        "id": "temp-1",
        "patient_id": "user-1",
        "file_path": str(temp_path),
        "original_filename": "scan.txt",
    }
    service.temp_repo.delete.return_value = True
    service.patient_repo = AsyncMock()
    service.patient_repo.get_by_patient_id.return_value = None
    service.rx_repo = AsyncMock()
    service.rx_repo.create_prescription.return_value = _paper_record()

    record = await service.confirm("user-1", _payload())

    assert record.id == "rx-paper"
    kwargs = service.rx_repo.create_prescription.await_args.kwargs
    assert kwargs["patient_id"] == "user-1"
    assert kwargs["doctor_id"] == ""
    assert kwargs["status"] == "issued"
    assert kwargs["source"] == "patient_uploaded"
    assert kwargs["verified"] is False
    assert kwargs["confirmed_by_patient"] is True
    assert kwargs["prescriber_name"] == "Dr. Smith"
    assert kwargs["original_file_name"] == "scan.txt"
    assert kwargs["safety_warnings"] == []
    assert "verification_token" not in kwargs
    assert not temp_path.exists()
    assert len(list(paper_dir.glob("paper_*.txt"))) == 1
    service.temp_repo.delete.assert_awaited_once_with("temp-1")


@pytest.mark.asyncio
async def test_confirm_rejects_another_patients_temp_upload(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    paper_dir = tmp_path / "paper_prescriptions"
    paper_dir.mkdir(parents=True)
    temp_path = paper_dir / "tmp_1.txt"
    temp_path.write_bytes(b"paper")
    service.temp_repo = AsyncMock()
    service.temp_repo.get_by_id.return_value = {
        "id": "temp-1",
        "patient_id": "other-user",
        "file_path": str(temp_path),
        "original_filename": "scan.txt",
    }
    service.rx_repo = AsyncMock()

    with pytest.raises(PaperPrescriptionError, match="Upload not found"):
        await service.confirm("user-1", _payload())

    service.rx_repo.create_prescription.assert_not_awaited()
    assert temp_path.exists()


@pytest.mark.asyncio
async def test_create_stores_file_and_record_without_extraction(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    service.patient_repo = AsyncMock()
    service.patient_repo.get_by_patient_id.return_value = None
    service.rx_repo = AsyncMock()
    service.rx_repo.create_prescription.return_value = _paper_record()

    scan_mock = AsyncMock(side_effect=AssertionError("OCR must not run"))
    with patch(
        "app.prescriptions.services.paper_prescription_service.parse_prescription_scan",
        new=scan_mock,
    ):
        record = await service.create(
            "user-1",
            UploadFile(file=io.BytesIO(b"jpeg-data"), filename="paper.jpg"),
            prescriber_name="Dr. Smith",
            prescription_date=date(2026, 10, 20),
            note="After a clinic visit",
        )

    assert record.id == "rx-paper"
    scan_mock.assert_not_awaited()
    kwargs = service.rx_repo.create_prescription.await_args.kwargs
    assert kwargs["patient_id"] == "user-1"
    assert kwargs["doctor_id"] == ""
    assert kwargs["prescription_date"].date().isoformat() == "2026-10-20"
    assert kwargs["diagnosis_notes"] == "After a clinic visit"
    assert kwargs["prescriber_name"] == "Dr. Smith"
    assert kwargs["items"] == []
    assert kwargs["status"] == "issued"
    assert kwargs["source"] == "patient_uploaded"
    assert kwargs["verified"] is False
    assert kwargs["file_type"] == "jpg"
    assert kwargs["original_file_name"] == "paper.jpg"
    stored = list((tmp_path / "paper_prescriptions").glob("paper_*.jpg"))
    assert len(stored) == 1
    assert stored[0].read_bytes() == b"jpeg-data"
    assert kwargs["file_path"] == str(stored[0])


@pytest.mark.asyncio
async def test_create_blank_optional_fields_uses_today_and_empty_medicine_list(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    service.patient_repo = AsyncMock()
    service.patient_repo.get_by_patient_id.return_value = None
    service.rx_repo = AsyncMock()
    service.rx_repo.create_prescription.return_value = _paper_record()

    await service.create(
        "user-1",
        UploadFile(file=io.BytesIO(b"png-data"), filename="paper.png"),
    )

    kwargs = service.rx_repo.create_prescription.await_args.kwargs
    assert kwargs["prescription_date"].date() == datetime.now(timezone.utc).date()
    assert kwargs["prescriber_name"] is None
    assert kwargs["diagnosis_notes"] is None
    assert kwargs["items"] == []


@pytest.mark.asyncio
async def test_create_rejects_future_date(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    service.patient_repo = AsyncMock()
    service.rx_repo = AsyncMock()

    future = datetime.now(timezone.utc).date() + timedelta(days=1)
    with pytest.raises(PaperPrescriptionError, match="must be in the past"):
        await service.create(
            "user-1",
            UploadFile(file=io.BytesIO(b"jpeg-data"), filename="paper.jpg"),
            prescription_date=future,
        )

    service.rx_repo.create_prescription.assert_not_awaited()
    paper_dir = tmp_path / "paper_prescriptions"
    assert not paper_dir.exists() or list(paper_dir.iterdir()) == []


@pytest.mark.asyncio
async def test_create_rejects_wrong_file_type_and_oversize(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    service.patient_repo = AsyncMock()
    service.rx_repo = AsyncMock()

    with pytest.raises(PaperPrescriptionError, match="Unsupported file type"):
        await service.create(
            "user-1",
            UploadFile(file=io.BytesIO(b"text"), filename="paper.txt"),
        )

    with patch(
        "app.prescriptions.services.paper_prescription_service.PAPER_MAX_SIZE_MB",
        1,
    ):
        with pytest.raises(PaperPrescriptionError, match="too large"):
            await service.create(
                "user-1",
                UploadFile(
                    file=io.BytesIO(b"x" * (1024 * 1024 + 1)),
                    filename="paper.jpg",
                ),
            )

    service.rx_repo.create_prescription.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_file_is_owner_only(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    paper_dir = tmp_path / "paper_prescriptions"
    paper_dir.mkdir(parents=True)
    paper_path = paper_dir / "paper_1.jpg"
    paper_path.write_bytes(b"jpeg-data")

    service.rx_repo = AsyncMock()
    service.rx_repo.get_by_id.return_value = SimpleNamespace(
        id="rx-paper",
        patient_id="patient-1",
        source="patient_uploaded",
        file_path=str(paper_path),
        file_type="jpg",
    )
    service.patient_repo = AsyncMock()
    service.patient_repo.get_by_user_id.return_value = SimpleNamespace(
        id="profile-1",
        patient_id="patient-1",
        user_id="user-1",
    )

    owned = await service.get_file("rx-paper", "user-1")
    assert owned["path"] == str(paper_path)
    assert owned["media_type"] == "image/jpeg"

    service.patient_repo.get_by_user_id.return_value = None
    denied = await service.get_file("rx-paper", "other-user")
    assert denied is None


def test_paper_model_allows_empty_and_existing_items():
    now = datetime.now(timezone.utc)
    base = dict(
        id="rx-paper",
        patient_id="patient-1",
        doctor_id="",
        prescription_date=now,
        status="issued",
        source="patient_uploaded",
        verified=False,
        created_at=now,
        updated_at=now,
    )
    assert PrescriptionInDB(items=[], **base).items == []

    old = PrescriptionInDB(
        items=[
            {
                "medicine_name": "PanD",
                "dosage": "40mg",
                "frequency": "1-0-0",
                "duration": "5 days",
            }
        ],
        **base,
    )
    assert old.items[0].medicine_name == "PanD"


@pytest.mark.asyncio
async def test_delete_removes_owned_paper_record_and_file(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    paper_dir = tmp_path / "paper_prescriptions"
    paper_dir.mkdir(parents=True)
    paper_path = paper_dir / "paper_1.txt"
    paper_path.write_bytes(b"paper")
    service.rx_repo = AsyncMock()
    service.rx_repo.get_by_id.return_value = SimpleNamespace(
        id="rx-paper",
        patient_id="patient-1",
        source="patient_uploaded",
        file_path=str(paper_path),
    )
    service.rx_repo.delete.return_value = True
    service.patient_repo = AsyncMock()
    service.patient_repo.get_by_user_id.return_value = SimpleNamespace(
        id="profile-1",
        patient_id="patient-1",
        user_id="user-1",
    )

    deleted = await service.delete("rx-paper", "user-1")

    assert deleted is True
    assert not paper_path.exists()
    service.rx_repo.delete.assert_awaited_once_with("rx-paper")


@pytest.mark.asyncio
async def test_delete_refuses_doctor_issued_record(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    service.rx_repo = AsyncMock()
    service.rx_repo.get_by_id.return_value = SimpleNamespace(
        id="rx-digital",
        patient_id="patient-1",
        source="doctor_issued",
        file_path=None,
    )
    service.patient_repo = AsyncMock()

    deleted = await service.delete("rx-digital", "user-1")

    assert deleted is False
    service.rx_repo.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_history_marks_paper_prescription_as_unverified():
    service = HistoryService()
    service.report_repo = AsyncMock()
    service.report_repo.list_by_patient.return_value = []
    service.prescription_repo = AsyncMock()
    service.prescription_repo.list_by_patient.return_value = [
        SimpleNamespace(
            id="rx-paper",
            patient_id="patient-1",
            prescription_date=datetime(2026, 10, 28, tzinfo=timezone.utc),
            created_at=datetime.now(timezone.utc),
            items=[{"medicine_name": "Aspirin"}],
            source="patient_uploaded",
            verified=False,
            prescriber_name="Dr. Smith",
            doctor_id="",
        )
    ]
    service.patient_repo = AsyncMock()
    service.patient_repo.get_by_patient_id.return_value = SimpleNamespace(
        id="profile-1",
        patient_id="patient-1",
        user_id="user-1",
    )
    service.doctor_repo = AsyncMock()

    events = await service.get_patient_history("user-1")

    assert len(events) == 1
    assert events[0].title == "Paper Prescription"
    assert events[0].source == "patient_uploaded"
    assert events[0].verified is False
    assert "not verified by a doctor" in events[0].summary
    assert "Dr. Smith" in events[0].summary
    service.doctor_repo.get_by_doctor_id.assert_not_awaited()


def test_doctor_without_grant_cannot_read_paper_prescription():
    service = MagicMock()
    service.get_prescription = AsyncMock(return_value=None)
    service.repo.get_by_id = AsyncMock(return_value=_paper_record())
    deny = AsyncMock(side_effect=HTTPException(status_code=404, detail="Access denied"))

    app.dependency_overrides[get_current_user] = lambda: _user("doctor", "doctor-user-123")
    try:
        with patch("app.prescriptions.router.PrescriptionService", return_value=service), \
             patch("app.prescriptions.router.grant_checks.require_active_grant", new=deny):
            response = client.get("/api/v1/prescriptions/rx-paper")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404
    deny.assert_awaited_once_with("patient-1", "doctor-user-123", "prescriptions")


def test_doctor_with_grant_reads_paper_prescription():
    service = MagicMock()
    service.get_prescription = AsyncMock(return_value=None)
    service.repo.get_by_id = AsyncMock(return_value=_paper_record())
    allow = AsyncMock(return_value=SimpleNamespace(id="grant-1"))

    app.dependency_overrides[get_current_user] = lambda: _user("doctor", "doctor-user-123")
    try:
        with patch("app.prescriptions.router.PrescriptionService", return_value=service), \
             patch("app.prescriptions.router.grant_checks.require_active_grant", new=allow), \
             patch("app.prescriptions.router.log_access", new=AsyncMock()):
            response = client.get("/api/v1/prescriptions/rx-paper")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "patient_uploaded"
    assert data["verified"] is False
    assert data["confirmed_by_patient"] is True
    allow.assert_awaited_once_with("patient-1", "doctor-user-123", "prescriptions")


@pytest.mark.asyncio
async def test_pdf_scan_uses_embedded_text_without_ocr():
    pdf_service = MagicMock()
    pdf_service.has_embedded_text.return_value = True
    pdf_service.extract_text.return_value = "Aspirin 100mg OD for 3 days"

    with patch("app.reports.services.pdf_extraction.PDFExtractionService", return_value=pdf_service):
        result = await parse_prescription_scan(
            UploadFile(file=io.BytesIO(b"%PDF-1.4"), filename="scan.pdf")
        )

    assert result["extraction_method"] == "text+rule-based"
    assert result["items"][0]["medicine_name"] == "Aspirin"
    assert result["items"][0]["confidence"] > 0
