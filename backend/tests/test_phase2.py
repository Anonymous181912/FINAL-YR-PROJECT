"""Phase 2 tests: safety checks, QR verification, notifications, emergency."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.dependencies import get_current_user

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_mongo():
    mock_db = MagicMock()

    def get_mock_collection(name):
        return AsyncMock()

    mock_db.__getitem__ = MagicMock(side_effect=get_mock_collection)

    with patch("app.database.connection.db", mock_db), \
         patch("app.database.connection.connect_to_mongo"), \
         patch("app.database.connection.close_mongo_connection"), \
         patch("app.database.indexes.create_indexes"):
        yield


def _user(uid, email, role, name="Test"):
    u = AsyncMock()
    u.id = uid
    u.email = email
    u.role = role
    u.full_name = name
    u.is_active = True
    u.created_at = datetime.now(timezone.utc)
    u.updated_at = datetime.now(timezone.utc)
    return u


def _token(sub, email, role):
    from app.core.security import create_access_token

    return create_access_token(data={"sub": sub, "email": email, "role": role})


def _rx(rid="rx1", pid="p1", did="d1", items=None, status="draft", token="tok123",
        vhash="h", vstatus="valid"):
    from app.models.prescription import PrescriptionInDB

    now = datetime.now(timezone.utc)
    return PrescriptionInDB(
        id=rid, patient_id=pid, doctor_id=did, prescription_date=now,
        items=items or [{"medicine_name": "Paracetamol", "dosage": "500mg",
                         "frequency": "TDS", "duration": "3 days"}],
        status=status, safety_warnings=[], acknowledged_warnings=False,
        verification_token=token, verification_hash=vhash,
        verification_status=vstatus, created_at=now, updated_at=now,
    )


class TestSafetyService:
    def test_interaction_detected(self):
        from app.prescriptions.services.safety_service import SafetyService

        out = SafetyService().check(
            [{"medicine_name": "Warfarin", "dosage": "5mg", "frequency": "OD", "duration": "30 days"},
             {"medicine_name": "Aspirin", "dosage": "75mg", "frequency": "OD", "duration": "30 days"}], [])
        assert any(w["type"] == "interaction" and w["severity"] == "severe" for w in out)

    def test_no_interaction_clean(self):
        from app.prescriptions.services.safety_service import SafetyService

        out = SafetyService().check(
            [{"medicine_name": "Paracetamol", "dosage": "500mg", "frequency": "TDS", "duration": "3 days"}], [])
        assert out == []

    def test_allergy_clash_severe(self):
        from app.prescriptions.services.safety_service import SafetyService

        out = SafetyService().check(
            [{"medicine_name": "Amoxicillin", "dosage": "500mg", "frequency": "TDS", "duration": "5 days"}],
            ["penicillin allergy"])
        assert any(w["type"] == "allergy" and w["severity"] == "severe" for w in out)

    def test_duplicate_moderate(self):
        from app.prescriptions.services.safety_service import SafetyService

        items = [{"medicine_name": "Paracetamol", "dosage": "500mg", "frequency": "TDS", "duration": "3 days"}] * 2
        out = SafetyService().check(items, [])
        assert any(w["type"] == "duplicate" for w in out)

    def test_dataset_size(self):
        import json

        data = json.load(open("app/data/drug_interactions.json", encoding="utf-8"))
        assert len(data["pairs"]) >= 60
        assert set(data["allergy_map"]) >= {"penicillin", "sulfa"}

    def test_severe_blocks_create_without_ack(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr")
        try:
            with patch("app.prescriptions.router.PatientRepository.get_by_patient_id", new_callable=AsyncMock) as mock_get_patient, \
                 patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as rx_cls, \
                 patch("app.prescriptions.services.prescription_service.DoctorRepository") as doc_cls:
                from unittest.mock import MagicMock
                from datetime import datetime, timezone
                mock_patient = MagicMock()
                mock_patient.allergies = []
                mock_patient.patient_code = "PAT-ABC12"
                mock_patient.allow_prescriptions = True
                mock_patient.emergency_token = None
                mock_patient.id = "p1"
                mock_patient.user_id = "p1"
                mock_patient.patient_id = "p1"
                mock_patient.created_at = datetime.now(timezone.utc)
                mock_patient.updated_at = datetime.now(timezone.utc)
                mock_get_patient.return_value = mock_patient
                
                doc = AsyncMock()
                doc.get_by_doctor_id.return_value = AsyncMock()
                doc_cls.return_value = doc
                r = client.post(
                    "/api/v1/prescriptions",
                    json={"patient_id": "p1", "items": [
                        {"medicine_name": "Warfarin", "dosage": "5mg", "frequency": "OD", "duration": "30 days"},
                        {"medicine_name": "Aspirin", "dosage": "75mg", "frequency": "OD", "duration": "30 days"}]},
                    headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"},
                )
                assert r.status_code == 400
                assert "acknowledged" in r.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_severe_passes_with_ack_and_reason(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr")
        try:
            with patch("app.prescriptions.router.PatientRepository.get_by_patient_id", new_callable=AsyncMock) as mock_get_patient, \
                 patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as rx_cls, \
                 patch("app.prescriptions.services.prescription_service.DoctorRepository") as doc_cls:
                from unittest.mock import MagicMock
                from datetime import datetime, timezone
                mock_patient = MagicMock()
                mock_patient.allergies = []
                mock_patient.patient_code = "PAT-ABC12"
                mock_patient.allow_prescriptions = True
                mock_patient.emergency_token = None
                mock_patient.id = "p1"
                mock_patient.user_id = "p1"
                mock_patient.patient_id = "p1"
                mock_patient.created_at = datetime.now(timezone.utc)
                mock_patient.updated_at = datetime.now(timezone.utc)
                mock_get_patient.return_value = mock_patient
                
                doc = AsyncMock()
                doc.get_by_doctor_id.return_value = AsyncMock()
                doc_cls.return_value = doc
                rx = AsyncMock()
                created_rx = _rx()
                created_rx.safety_warnings = [
                    {"type": "interaction", "severity": "severe",
                     "drugs": ["warfarin", "aspirin"], "note": "Bleeding risk."}]
                rx.create_prescription.return_value = created_rx
                rx_cls.return_value = rx
                r = client.post(
                    "/api/v1/prescriptions",
                    json={"patient_id": "p1", "acknowledge_warnings": True, "ack_reason": "Specialist advised dual therapy",
                          "items": [
                              {"medicine_name": "Warfarin", "dosage": "5mg", "frequency": "OD", "duration": "30 days"},
                              {"medicine_name": "Aspirin", "dosage": "75mg", "frequency": "OD", "duration": "30 days"}]},
                    headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"},
                )
                assert r.status_code == 201, r.text
                assert any(w["severity"] == "severe" for w in r.json()["safety_warnings"])
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_issue_blocked_without_ack(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr")
        try:
            with patch("app.prescriptions.router.PatientRepository.get_by_patient_id", new_callable=AsyncMock) as mock_get_patient, \
                 patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as rx_cls:
                from unittest.mock import MagicMock
                from datetime import datetime, timezone
                mock_patient = MagicMock()
                mock_patient.allergies = []
                mock_patient.patient_code = "PAT-ABC12"
                mock_patient.allow_prescriptions = True
                mock_patient.emergency_token = None
                mock_patient.id = "p1"
                mock_patient.user_id = "p1"
                mock_patient.patient_id = "p1"
                mock_patient.created_at = datetime.now(timezone.utc)
                mock_patient.updated_at = datetime.now(timezone.utc)
                mock_get_patient.return_value = mock_patient
                
                rx = AsyncMock()
                rx.get_by_id.return_value = _rx(items=[
                    {"medicine_name": "Warfarin", "dosage": "5mg", "frequency": "OD", "duration": "30 days"},
                    {"medicine_name": "Aspirin", "dosage": "75mg", "frequency": "OD", "duration": "30 days"}])
                rx_cls.return_value = rx
                r = client.put("/api/v1/prescriptions/rx1", json={"status": "issued"},
                               headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"})
                assert r.status_code == 400
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestVerifyEndpoints:
    def test_valid_token_public(self):
        with patch("app.verify.router.PrescriptionService") as svc_cls, \
             patch("app.verify.router.DoctorRepository") as doc_cls:
            from app.prescriptions.services.prescription_service import PrescriptionService

            svc = AsyncMock()
            rx = _rx()
            svc.get_by_token.return_value = rx
            from unittest.mock import MagicMock as _MM

            svc.verify_token = _MM(return_value="valid")
            svc_cls.return_value = svc
            doc = AsyncMock()
            doc.get_by_doctor_id.return_value = AsyncMock(full_name="Dr Who")
            doc_cls.return_value = doc
            r = client.get("/api/v1/verify/prescription/tok123")  # no auth header
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["status"] == "valid"
            assert body["doctor_name"] == "Dr Who"
            assert "prescription_ref" in body
            assert "items" not in body and "patient_id" not in body

    def test_unknown_token_404(self):
        with patch("app.verify.router.PrescriptionService") as svc_cls:
            svc = AsyncMock()
            svc.get_by_token.return_value = None
            svc_cls.return_value = svc
            assert client.get("/api/v1/verify/prescription/nope").status_code == 404

    def test_revoke_flow(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr")
        try:
            with patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as rx_cls:
                rx = AsyncMock()
                rx.get_by_id.return_value = _rx()
                rx.update_prescription.return_value = _rx(vstatus="revoked")
                rx_cls.return_value = rx
                r = client.post("/api/v1/prescriptions/rx1/revoke",
                                headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"})
                assert r.status_code == 200
                assert r.json()["verification_status"] == "revoked"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_hash_detects_modification(self):
        from app.prescriptions.services.prescription_service import (
            PrescriptionService, _content_hash, verification_payload)

        rx = _rx()
        rx.verification_hash = _content_hash(verification_payload(rx))
        assert PrescriptionService().verify_token(rx) == "valid"
        rx.items = [{"medicine_name": "Changed", "dosage": "1", "frequency": "OD", "duration": "1 day"}]
        assert PrescriptionService().verify_token(rx) == "modified"


class TestNotifications:
    def test_list_and_read(self):
        app.dependency_overrides[get_current_user] = lambda: _user("p1", "p@t.com", "patient", "P")
        try:
            from app.models.notification import NotificationInDB

            now = datetime.now(timezone.utc)
            n = NotificationInDB(id="n1", user_id="p1", kind="general", title="Hi", created_at=now, updated_at=now)
            with patch("app.notifications.router.NotificationRepository") as repo_cls:
                repo = AsyncMock()
                repo.list_for_user.return_value = [n]
                repo.mark_read.return_value = NotificationInDB(id="n1", user_id="p1", kind="general",
                                                              title="Hi", is_read=True, created_at=now, updated_at=now)
                repo_cls.return_value = repo
                assert client.get("/api/v1/notifications",
                                  headers={"Authorization": f"Bearer {_token('p1', 'p@t.com', 'patient')}"}).status_code == 200
                r = client.patch("/api/v1/notifications/n1/read",
                                 headers={"Authorization": f"Bearer {_token('p1', 'p@t.com', 'patient')}"})
                assert r.status_code == 200 and r.json()["is_read"] is True
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_reminder_cycle_creates_followup(self):
        import asyncio

        async def run():
            from app.notifications import scheduler

            now = datetime.now(timezone.utc)
            doc = {"id": "rx1", "patient_id": "p1", "created_at": now - timedelta(days=1),
                   "follow_up_date": now + timedelta(days=2), "items": []}
            with patch("app.database.repositories.prescription_repository.PrescriptionRepository") as rx_cls, \
                 patch("app.database.repositories.notification_repository.NotificationRepository") as n_cls:
                rx = MagicMock()
                cur = AsyncMock()
                cur.to_list.return_value = [doc]
                rx.collection.find.return_value = cur
                rx_cls.return_value = rx
                n = AsyncMock()
                n.create_if_absent.return_value = AsyncMock(user_id="p1")
                n_cls.return_value = n
                out = await scheduler.run_reminder_cycle(now=now)
                assert out["created"] >= 1

        asyncio.run(run())

    def test_duration_parser(self):
        from app.notifications.scheduler import parse_duration_days

        assert parse_duration_days("7 days") == 7
        assert parse_duration_days("2 weeks") == 14
        assert parse_duration_days("1 month") == 30
        assert parse_duration_days("SOS") is None


class TestEmergencyCard:
    def test_card_pdf_and_rotate(self):
        app.dependency_overrides[get_current_user] = lambda: _user("p1", "p@t.com", "patient", "P")
        try:
            prof = AsyncMock()
            prof.id = "prof1"
            prof.emergency_token = "etok"
            prof.blood_group = "O+"
            prof.allergies = ["penicillin"]
            prof.emergency_contact_name = "Mom"
            prof.emergency_contact_phone = "+10000000001"
            with patch("app.patients.router.PatientRepository") as repo_cls:
                repo = AsyncMock()
                repo.get_by_user_id.return_value = prof
                repo.update_profile.return_value = prof
                repo_cls.return_value = repo
                r = client.get("/api/v1/patients/me/emergency-card",
                               headers={"Authorization": f"Bearer {_token('p1', 'p@t.com', 'patient')}"})
                assert r.status_code == 200
                assert r.headers["content-type"] == "application/pdf"
                assert r.content[:4] == b"%PDF"
                r2 = client.post("/api/v1/patients/me/emergency-token/rotate",
                                 headers={"Authorization": f"Bearer {_token('p1', 'p@t.com', 'patient')}"})
                assert r2.status_code == 200 and "emergency_token" in r2.json()
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_public_emergency_page_minimal(self):
        with patch("app.verify.router.PatientRepository") as repo_cls:
            repo = AsyncMock()
            repo.get_by_field.return_value = {"blood_group": "O+", "allergies": ["penicillin"],
                                              "emergency_contact_name": "Mom",
                                              "emergency_contact_phone": "+1",
                                              "full_name": "Secret Name"}
            repo_cls.return_value = repo
            r = client.get("/api/v1/verify/emergency/etok")
            assert r.status_code == 200
            body = r.json()
            assert body["blood_group"] == "O+"
            assert "full_name" not in body and "history" not in body


class TestScan:
    def test_txt_scan_draft_not_saved(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr")
        try:
            with patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as rx_cls:
                rx = AsyncMock()
                rx_cls.return_value = rx  # must NOT be called
                r = client.post(
                    "/api/v1/prescriptions/scan",
                    files={"file": ("rx.txt", b"Paracetamol 500mg TDS for 3 days\nAmoxicillin 250mg BD for 5 days", "text/plain")},
                    headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"},
                )
                assert r.status_code == 200, r.text
                body = r.json()
                assert body["draft"] is True and body["review_required"] is True
                assert len(body["items"]) == 2
                rx.create_prescription.assert_not_called()
        finally:
            app.dependency_overrides.pop(get_current_user, None)
