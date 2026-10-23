"""Phase 0 security tests: verification, access control, regex, OCR, config."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.dependencies import (
    get_current_admin,
    get_current_user,
    get_current_verified_doctor,
)

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


def _user(user_id, email, role, full_name="Test User"):
    u = AsyncMock()
    u.id = user_id
    u.email = email
    u.role = role
    u.full_name = full_name
    u.is_active = True
    u.created_at = datetime.now(timezone.utc)
    u.updated_at = datetime.now(timezone.utc)
    return u


def _doctor_profile(verified=True, status="approved", user_id="doctor-user-123"):
    p = AsyncMock()
    p.id = "doctor-profile-123"
    p.user_id = user_id
    p.doctor_id = user_id
    p.full_name = "Dr. Test"
    p.specialization = "General"
    p.contact_phone = None
    p.contact_email = None
    p.license_number = "LIC-1"
    p.is_verified = verified
    p.verification_status = status
    p.is_active = True
    p.created_at = datetime.now(timezone.utc)
    p.updated_at = datetime.now(timezone.utc)
    return p


def _patient_profile(pid="patient-1", user_id="patient-user-123"):
    p = AsyncMock()
    p.id = pid
    p.user_id = user_id
    p.patient_id = pid
    p.full_name = "Test Patient"
    p.date_of_birth = None
    p.gender = None
    p.contact_phone = None
    p.contact_email = None
    p.address = None
    p.emergency_contact_name = None
    p.emergency_contact_phone = None
    p.blood_group = None
    p.allergies = []
    p.is_active = True
    p.created_at = datetime.now(timezone.utc)
    p.updated_at = datetime.now(timezone.utc)
    return p


def _token(sub, email, role):
    from app.core.security import create_access_token

    return create_access_token(data={"sub": sub, "email": email, "role": role})


class TestAdminRouter:
    def test_non_admin_cannot_list_pending(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor")
        try:
            token = _token("d1", "d@t.com", "doctor")
            r = client.get("/api/v1/admin/pending-doctors", headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_admin_can_list_pending(self):
        app.dependency_overrides[get_current_admin] = lambda: _user("a1", "a@t.com", "admin", "Admin")
        try:
            with patch("app.admin.router.DoctorRepository") as repo_cls:
                inst = AsyncMock()
                inst.list_pending.return_value = []
                repo_cls.return_value = inst
                token = _token("a1", "a@t.com", "admin")
                r = client.get("/api/v1/admin/pending-doctors", headers={"Authorization": f"Bearer {token}"})
                assert r.status_code == 200
                assert r.json() == []
        finally:
            app.dependency_overrides.pop(get_current_admin, None)

    def test_admin_approve_and_reject(self):
        app.dependency_overrides[get_current_admin] = lambda: _user("a1", "a@t.com", "admin", "Admin")
        try:
            with patch("app.admin.router.DoctorRepository") as repo_cls:
                inst = AsyncMock()
                inst.set_verification.return_value = _doctor_profile()
                repo_cls.return_value = inst
                token = _token("a1", "a@t.com", "admin")
                assert client.post("/api/v1/admin/doctors/x/approve", headers={"Authorization": f"Bearer {token}"}).status_code == 200
                assert client.post("/api/v1/admin/doctors/x/reject", headers={"Authorization": f"Bearer {token}"}).status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_admin, None)

    def test_admin_approve_missing_returns_404(self):
        app.dependency_overrides[get_current_admin] = lambda: _user("a1", "a@t.com", "admin", "Admin")
        try:
            with patch("app.admin.router.DoctorRepository") as repo_cls:
                inst = AsyncMock()
                inst.set_verification.return_value = None
                repo_cls.return_value = inst
                token = _token("a1", "a@t.com", "admin")
                r = client.post("/api/v1/admin/doctors/missing/approve", headers={"Authorization": f"Bearer {token}"})
                assert r.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_admin, None)


class TestVerifiedDoctorGate:
    def test_unverified_doctor_blocked_from_patients_list(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr. X")
        try:
            with patch(
                "app.database.repositories.doctor_repository.DoctorRepository.get_by_user_id",
                new=AsyncMock(return_value=_doctor_profile(verified=False, status="pending", user_id="d1")),
            ):
                token = _token("d1", "d@t.com", "doctor")
                r = client.get("/api/v1/patients/", headers={"Authorization": f"Bearer {token}"})
                assert r.status_code == 403
                assert "pending approval" in r.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_unverified_doctor_blocked_from_prescription_create(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr. X")
        try:
            with patch(
                "app.database.repositories.doctor_repository.DoctorRepository.get_by_user_id",
                new=AsyncMock(return_value=_doctor_profile(verified=False, status="pending", user_id="d1")),
            ):
                token = _token("d1", "d@t.com", "doctor")
                r = client.post(
                    "/api/v1/prescriptions",
                    json={"patient_id": "p1", "items": [{"medicine_name": "A", "dosage": "1", "frequency": "OD", "duration": "3 days"}]},
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert r.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_unverified_doctor_blocked_from_doctor_history(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr. X")
        try:
            with patch(
                "app.database.repositories.doctor_repository.DoctorRepository.get_by_user_id",
                new=AsyncMock(return_value=_doctor_profile(verified=False, status="rejected", user_id="d1")),
            ):
                token = _token("d1", "d@t.com", "doctor")
                r = client.get("/api/v1/history/patient/p1", headers={"Authorization": f"Bearer {token}"})
                assert r.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_verified_doctor_dependency_allows_verified(self):
        import asyncio

        async def run():
            from app.auth.dependencies import get_current_verified_doctor

            user = _user("doctor-user-123", "doctor@test.com", "doctor", "Dr. Test")
            with patch(
                "app.auth.dependencies.DoctorRepository.get_by_user_id",
                new=AsyncMock(return_value=_doctor_profile()),
            ):
                result = await get_current_verified_doctor(user)
                assert result.role == "doctor"

        asyncio.run(run())


class TestPatientAccess:
    def test_patient_cannot_read_other_patient(self):
        app.dependency_overrides[get_current_user] = lambda: _user("patient-user-123", "p@t.com", "patient")
        try:
            with patch("app.patients.router.PatientRepository") as repo_cls:
                inst = AsyncMock()
                inst.get_by_patient_id.return_value = _patient_profile(pid="other-1", user_id="other-user")
                inst.get_by_user_id.return_value = _patient_profile(pid="mine-1", user_id="patient-user-123")
                repo_cls.return_value = inst
                token = _token("patient-user-123", "p@t.com", "patient")
                r = client.get("/api/v1/patients/other-1", headers={"Authorization": f"Bearer {token}"})
                assert r.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_patient_can_read_own_profile(self):
        app.dependency_overrides[get_current_user] = lambda: _user("patient-user-123", "p@t.com", "patient")
        try:
            with patch("app.patients.router.PatientRepository") as repo_cls:
                own = _patient_profile(pid="patient-user-123", user_id="patient-user-123")
                inst = AsyncMock()
                inst.get_by_patient_id.return_value = own
                inst.get_by_user_id.return_value = own
                repo_cls.return_value = inst
                token = _token("patient-user-123", "p@t.com", "patient")
                r = client.get("/api/v1/patients/patient-user-123", headers={"Authorization": f"Bearer {token}"})
                assert r.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_search_with_regex_chars_does_not_crash(self):
        app.dependency_overrides[get_current_user] = lambda: _user("doctor-user-123", "d@t.com", "doctor", "Dr. T")
        try:
            with patch("app.patients.router.PatientRepository") as repo_cls:
                cursor = MagicMock()
                cursor.skip.return_value = cursor
                cursor.limit.return_value = cursor
                cursor.to_list = AsyncMock(return_value=[])
                inst = MagicMock()
                inst.collection.find.return_value = cursor
                repo_cls.return_value = inst
                token = _token("doctor-user-123", "d@t.com", "doctor")
                r = client.get("/api/v1/patients/", params={"search": ".*(a+b)[0-9]?"}, headers={"Authorization": f"Bearer {token}"})
                assert r.status_code == 200
                # Verify the regex was escaped (literal), not passed raw.
                find_filter = inst.collection.find.call_args[0][0]
                and_clauses = find_filter.get("$and", [find_filter])
                regex_clause = next(c for c in and_clauses if "full_name" in c)
                assert regex_clause["full_name"]["$regex"] == r"\.\*\(a\+b\)\[0\-9\]\?"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_search_escaping_unit(self):
        import re

        raw = ".*(test)+?"
        assert re.escape(raw[:50]) == r"\.\*\(test\)\+\?"


class TestConfigAndOCR:
    def test_allowed_extensions_excludes_dcm(self):
        from app.core.config import settings

        assert "dcm" not in settings.allowed_extensions_list
        assert "pdf" in settings.allowed_extensions_list

    def test_ocr_get_reader_no_attribute_error(self):
        from app.reports.ai.ocr import OCRService

        svc = OCRService()
        readers = svc._get_reader()
        assert isinstance(readers, dict)
        assert "paddle" in readers and "easy" in readers

    def test_rate_limiter_attached(self):
        assert getattr(app.state, "limiter", None) is not None

    def test_doctor_response_has_verification_fields(self):
        from app.schemas.doctor import DoctorResponse

        assert "is_verified" in DoctorResponse.model_fields
        assert "verification_status" in DoctorResponse.model_fields
