"""Phase 0.5: prove Phase 0 hardening with automated tests.

Covers:
1. Unverified doctors get 403 on patient-data endpoints.
2. A REJECTED / de-verified doctor is blocked on the very next request with
   an old token (verification is DB-checked per request, never from the JWT).
3. Patient A cannot read patient B's profile, reports, prescriptions, history.
4. role=admin registration rejected; query-param registration returns 422.
5. 11th login attempt within a minute returns 429 (limiter enabled for test).
"""

from datetime import datetime, timezone
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


def _doctor_profile(verified, status, user_id="doctor-user-123"):
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


def _patient_profile(pid, user_id):
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


def _mock_report(rid, patient_id):
    r = AsyncMock()
    r.id = rid
    r.patient_id = patient_id
    r.title = "Report"
    r.status = "completed"
    r.created_at = datetime.now(timezone.utc)
    r.updated_at = datetime.now(timezone.utc)
    r.category = "Blood Test"
    r.doctor_id = None
    r.extracted_text = "Hemoglobin 14 g/dL"
    r.entities = []
    return r


def _mock_rx(rx_id, patient_id, doctor_id):
    from datetime import datetime as dt

    rx = AsyncMock()
    rx.id = rx_id
    rx.patient_id = patient_id
    rx.doctor_id = doctor_id
    rx.prescription_date = None
    rx.diagnosis_notes = None
    rx.advice = None
    rx.follow_up_date = None
    rx.items = [{"medicine_name": "Aspirin", "dosage": "100mg", "frequency": "OD", "duration": "3 days"}]
    rx.status = "draft"
    rx.safety_warnings = []
    rx.acknowledged_warnings = False
    rx.verification_token = None
    rx.verification_status = "valid"
    rx.file_path = None
    rx.created_at = datetime.now(timezone.utc)
    rx.updated_at = datetime.now(timezone.utc)
    rx.issued_at = None
    return rx


class TestUnverifiedDoctorBlocked:
    """Unverified (pending) doctors get 403 on every patient-data endpoint."""

    def _unverified(self):
        return patch(
            "app.database.repositories.doctor_repository.DoctorRepository.get_by_user_id",
            new=AsyncMock(return_value=_doctor_profile(False, "pending")),
        )

    def test_patients_list(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr. X")
        try:
            with self._unverified():
                r = client.get("/api/v1/patients/", headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"})
                assert r.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_patient_detail(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr. X")
        try:
            with self._unverified(), \
                 patch("app.patients.router.PatientRepository") as repo_cls:
                inst = AsyncMock()
                inst.get_by_patient_id.return_value = _patient_profile("p1", "u1")
                repo_cls.return_value = inst
                r = client.get("/api/v1/patients/p1", headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"})
                assert r.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_reports_list(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr. X")
        try:
            with self._unverified():
                r = client.get("/api/v1/reports/", headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"})
                assert r.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_doctor_history(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr. X")
        try:
            with self._unverified():
                r = client.get("/api/v1/history/patient/p1", headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"})
                assert r.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_prescription_create(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr. X")
        try:
            with self._unverified():
                r = client.post(
                    "/api/v1/prescriptions",
                    json={"patient_id": "p1", "items": [{"medicine_name": "A", "dosage": "1", "frequency": "OD", "duration": "3d"}]},
                    headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"},
                )
                assert r.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestDeverifiedOldToken:
    """A doctor rejected AFTER login is blocked on the next request with the
    old token — verification comes from the DB on every request, not the JWT."""

    def test_rejected_doctor_old_token_blocked(self):
        # Token minted while the doctor was approved...
        token = _token("doctor-user-123", "doctor@test.com", "doctor")
        # ...but the DB now says rejected. Full auth chain runs (no overrides):
        # JWT -> user lookup -> per-request verification lookup.
        with patch("app.auth.dependencies.UserRepository") as user_repo_cls, \
             patch(
                 "app.database.repositories.doctor_repository.DoctorRepository.get_by_user_id",
                 new=AsyncMock(return_value=_doctor_profile(False, "rejected")),
             ):
            inst = AsyncMock()
            inst.get_by_id.return_value = _user("doctor-user-123", "doctor@test.com", "doctor", "Dr. Test")
            user_repo_cls.return_value = inst
            r = client.get("/api/v1/patients/", headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 403
            assert "pending approval" in r.json()["detail"].lower()

    def test_jwt_carries_no_verification_claim(self):
        from app.core.security import decode_access_token

        token = _token("doctor-user-123", "doctor@test.com", "doctor")
        payload = decode_access_token(token)
        assert "is_verified" not in payload
        assert "verification_status" not in payload


class TestPatientIsolation:
    """Patient A gets 404/403 (never data) for patient B's resources."""

    def _as_patient_a(self):
        app.dependency_overrides[get_current_user] = lambda: _user(
            "patient-a", "a@test.com", "patient", "Patient A"
        )

    def test_profile(self):
        self._as_patient_a()
        try:
            with patch("app.patients.router.PatientRepository") as repo_cls:
                inst = AsyncMock()
                inst.get_by_patient_id.return_value = _patient_profile("patient-b", "patient-b")
                inst.get_by_user_id.return_value = _patient_profile("patient-a", "patient-a")
                repo_cls.return_value = inst
                r = client.get("/api/v1/patients/patient-b", headers={"Authorization": f"Bearer {_token('patient-a', 'a@test.com', 'patient')}"})
                assert r.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_report(self):
        self._as_patient_a()
        try:
            with patch("app.reports.services.report_service.ReportRepository") as repo_cls:
                inst = AsyncMock()
                inst.get_by_id.return_value = _mock_report("r1", "patient-b")
                repo_cls.return_value = inst
                r = client.get("/api/v1/reports/r1", headers={"Authorization": f"Bearer {_token('patient-a', 'a@test.com', 'patient')}"})
                assert r.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_prescription(self):
        self._as_patient_a()
        try:
            with patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as repo_cls:
                inst = AsyncMock()
                inst.get_by_id.return_value = _mock_rx("rx1", "patient-b", "doctor-1")
                repo_cls.return_value = inst
                r = client.get("/api/v1/prescriptions/rx1", headers={"Authorization": f"Bearer {_token('patient-a', 'a@test.com', 'patient')}"})
                assert r.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_history_via_doctor_endpoint_forbidden(self):
        # Patients are not doctors: the doctor history endpoint must 403.
        self._as_patient_a()
        try:
            r = client.get("/api/v1/history/patient/patient-b", headers={"Authorization": f"Bearer {_token('patient-a', 'a@test.com', 'patient')}"})
            assert r.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestRegisterShape:
    def test_admin_role_rejected(self):
        r = client.post(
            "/api/v1/auth/register",
            json={"email": "x@test.com", "password": "Pass1234", "role": "admin", "full_name": "X"},
        )
        assert r.status_code == 422

    def test_query_params_rejected_with_422(self):
        r = client.post(
            "/api/v1/auth/register?email=q@test.com&password=Pass1234&role=patient&full_name=Q",
        )
        # No JSON body -> FastAPI body validation fails with 422.
        assert r.status_code == 422


class TestLoginRateLimit:
    def test_11th_login_returns_429(self):
        limiter = app.state.limiter
        prev = limiter.enabled
        limiter.enabled = True
        try:
            limiter._storage.reset()
            with patch("app.auth.router.UserRepository") as repo_cls:
                inst = AsyncMock()
                inst.get_by_email.return_value = None
                repo_cls.return_value = inst
                statuses = []
                for _ in range(11):
                    r = client.post(
                        "/api/v1/auth/login",
                        data={"username": "nobody@test.com", "password": "wrong"},
                    )
                    statuses.append(r.status_code)
                assert statuses[-1] == 429, statuses
                assert 401 in statuses  # earlier attempts processed normally
        finally:
            limiter.enabled = prev
            try:
                limiter._storage.reset()
            except Exception:
                pass
