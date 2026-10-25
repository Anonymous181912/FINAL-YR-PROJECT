import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.auth.dependencies import get_current_user, get_current_doctor, get_current_patient

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


def _create_mock_user(user_id, email, role, full_name="Test User"):
    from datetime import datetime, timezone
    mock_user = AsyncMock()
    mock_user.id = user_id
    mock_user.email = email
    mock_user.role = role
    mock_user.full_name = full_name
    mock_user.is_active = True
    mock_user.created_at = datetime.now(timezone.utc)
    mock_user.updated_at = datetime.now(timezone.utc)
    return mock_user


def _create_mock_patient(patient_id, user_id, full_name="Test Patient"):
    from datetime import datetime, timezone
    mock_patient = AsyncMock()
    mock_patient.id = patient_id
    mock_patient.user_id = user_id
    mock_patient.patient_id = patient_id
    mock_patient.full_name = full_name
    mock_patient.date_of_birth = None
    mock_patient.gender = None
    mock_patient.contact_phone = None
    mock_patient.contact_email = None
    mock_patient.address = None
    mock_patient.emergency_contact_name = None
    mock_patient.emergency_contact_phone = None
    mock_patient.blood_group = None
    mock_patient.allergies = []
    mock_patient.is_active = True
    mock_patient.created_at = datetime.now(timezone.utc)
    mock_patient.updated_at = datetime.now(timezone.utc)
    return mock_patient


def _create_mock_doctor(doctor_id, user_id, full_name="Dr. Test"):
    from datetime import datetime, timezone
    mock_doctor = AsyncMock()
    mock_doctor.id = doctor_id
    mock_doctor.user_id = user_id
    mock_doctor.doctor_id = doctor_id
    mock_doctor.full_name = full_name
    mock_doctor.specialization = "General"
    mock_doctor.contact_phone = None
    mock_doctor.contact_email = None
    mock_doctor.license_number = None
    mock_doctor.is_active = True
    mock_doctor.created_at = datetime.now(timezone.utc)
    mock_doctor.updated_at = datetime.now(timezone.utc)
    return mock_doctor


def _create_patient_token():
    from app.core.security import create_access_token
    return create_access_token(data={"sub": "patient-user-123", "email": "patient@test.com", "role": "patient"})


def _create_doctor_token():
    from app.core.security import create_access_token
    return create_access_token(data={"sub": "doctor-user-123", "email": "doctor@test.com", "role": "doctor"})


def _override_patient_user():
    return _create_mock_user("patient-user-123", "patient@test.com", "patient", "Test Patient")


def _override_doctor_user():
    return _create_mock_user("doctor-user-123", "doctor@test.com", "doctor", "Dr. Test")


def _create_mock_report(report_id, patient_id, title="Test Report", status="completed", created_at=None):
    from datetime import datetime, timezone
    if created_at is None:
        created_at = datetime.now(timezone.utc)
    mock_report = AsyncMock()
    mock_report.id = report_id
    mock_report.patient_id = patient_id
    mock_report.title = title
    mock_report.status = status
    mock_report.created_at = created_at
    mock_report.updated_at = created_at
    mock_report.category = "Blood Test"
    mock_report.doctor_id = None
    return mock_report


def _create_mock_prescription(prescription_id, patient_id, doctor_id, created_at=None, prescription_date=None):
    from datetime import datetime, timezone
    if created_at is None:
        created_at = datetime.now(timezone.utc)
    mock_rx = AsyncMock()
    mock_rx.id = prescription_id
    mock_rx.patient_id = patient_id
    mock_rx.doctor_id = doctor_id
    mock_rx.created_at = created_at
    mock_rx.updated_at = created_at
    mock_rx.prescription_date = prescription_date
    mock_rx.items = [{"medicine_name": "Aspirin", "dosage": "100mg", "frequency": "OD", "duration": "3 days"}]
    mock_rx.status = "draft"
    mock_rx.safety_warnings = []
    mock_rx.acknowledged_warnings = False
    mock_rx.verification_token = None
    mock_rx.verification_status = "valid"
    mock_rx.file_path = None
    return mock_rx


class TestPatientHistory:
    def test_unauthenticated_cannot_access_history(self):
        response = client.get("/api/v1/history/")
        assert response.status_code == 401

    def test_patient_gets_empty_history(self):
        app.dependency_overrides[get_current_user] = _override_patient_user
        try:
            with patch("app.history.services.history_service.ReportRepository") as mock_report_repo_cls, \
                 patch("app.history.services.history_service.PrescriptionRepository") as mock_rx_repo_cls, \
                 patch("app.history.services.history_service.PatientRepository") as mock_patient_repo_cls:
                mock_report_repo = AsyncMock()
                mock_report_repo.list_by_patient.return_value = []
                mock_report_repo_cls.return_value = mock_report_repo

                mock_rx_repo = AsyncMock()
                mock_rx_repo.list_by_patient.return_value = []
                mock_rx_repo_cls.return_value = mock_rx_repo

                mock_patient_repo = AsyncMock()
                mock_patient_repo.get_by_patient_id.return_value = _create_mock_patient("patient-1", "patient-user-123")
                mock_patient_repo_cls.return_value = mock_patient_repo

                token = _create_patient_token()
                response = client.get("/api/v1/history/", headers={"Authorization": f"Bearer {token}"})
                assert response.status_code == 200
                assert response.json() == []
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_patient_history_includes_reports(self):
        app.dependency_overrides[get_current_user] = _override_patient_user
        try:
            with patch("app.history.services.history_service.ReportRepository") as mock_report_repo_cls, \
                 patch("app.history.services.history_service.PrescriptionRepository") as mock_rx_repo_cls, \
                 patch("app.history.services.history_service.PatientRepository") as mock_patient_repo_cls, \
                 patch("app.history.services.history_service.DoctorRepository") as mock_doctor_repo_cls:
                report = _create_mock_report("report-1", "patient-user-123", "MRI Report")
                mock_report_repo = AsyncMock()
                mock_report_repo.list_by_patient.return_value = [report]
                mock_report_repo_cls.return_value = mock_report_repo

                mock_rx_repo = AsyncMock()
                mock_rx_repo.list_by_patient.return_value = []
                mock_rx_repo_cls.return_value = mock_rx_repo

                mock_patient_repo = AsyncMock()
                mock_patient_repo.get_by_patient_id.return_value = _create_mock_patient("patient-1", "patient-user-123")
                mock_patient_repo_cls.return_value = mock_patient_repo

                mock_doctor_repo = AsyncMock()
                mock_doctor_repo_cls.return_value = mock_doctor_repo

                token = _create_patient_token()
                response = client.get("/api/v1/history/", headers={"Authorization": f"Bearer {token}"})
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["event_type"] == "REPORT"
                assert data[0]["source_id"] == "report-1"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_patient_history_includes_prescriptions(self):
        app.dependency_overrides[get_current_user] = _override_patient_user
        try:
            with patch("app.history.services.history_service.ReportRepository") as mock_report_repo_cls, \
                 patch("app.history.services.history_service.PrescriptionRepository") as mock_rx_repo_cls, \
                 patch("app.history.services.history_service.PatientRepository") as mock_patient_repo_cls, \
                 patch("app.history.services.history_service.DoctorRepository") as mock_doctor_repo_cls:
                mock_report_repo = AsyncMock()
                mock_report_repo.list_by_patient.return_value = []
                mock_report_repo_cls.return_value = mock_report_repo

                prescription = _create_mock_prescription("rx-1", "patient-user-123", "doctor-user-123")
                mock_rx_repo = AsyncMock()
                mock_rx_repo.list_by_patient.return_value = [prescription]
                mock_rx_repo_cls.return_value = mock_rx_repo

                mock_patient_repo = AsyncMock()
                mock_patient_repo.get_by_patient_id.return_value = _create_mock_patient("patient-1", "patient-user-123")
                mock_patient_repo_cls.return_value = mock_patient_repo

                mock_doctor_repo = AsyncMock()
                mock_doctor = _create_mock_doctor("doctor-1", "doctor-user-123", "Dr. Smith")
                mock_doctor_repo.get_by_doctor_id.return_value = mock_doctor
                mock_doctor_repo_cls.return_value = mock_doctor_repo

                token = _create_patient_token()
                response = client.get("/api/v1/history/", headers={"Authorization": f"Bearer {token}"})
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["event_type"] == "PRESCRIPTION"
                assert data[0]["source_id"] == "rx-1"
                assert "Dr. Smith" in data[0]["summary"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_patient_history_sorted_newest_first(self):
        app.dependency_overrides[get_current_user] = _override_patient_user
        try:
            with patch("app.history.services.history_service.ReportRepository") as mock_report_repo_cls, \
                 patch("app.history.services.history_service.PrescriptionRepository") as mock_rx_repo_cls, \
                 patch("app.history.services.history_service.PatientRepository") as mock_patient_repo_cls, \
                 patch("app.history.services.history_service.DoctorRepository") as mock_doctor_repo_cls:
                from datetime import datetime, timezone, timedelta
                older = datetime.now(timezone.utc) - timedelta(days=2)
                newer = datetime.now(timezone.utc) - timedelta(days=1)

                report_old = _create_mock_report("report-old", "patient-user-123", "Old Report", created_at=older)
                report_new = _create_mock_report("report-new", "patient-user-123", "New Report", created_at=newer)

                mock_report_repo = AsyncMock()
                mock_report_repo.list_by_patient.return_value = [report_old, report_new]
                mock_report_repo_cls.return_value = mock_report_repo

                mock_rx_repo = AsyncMock()
                mock_rx_repo.list_by_patient.return_value = []
                mock_rx_repo_cls.return_value = mock_rx_repo

                mock_patient_repo = AsyncMock()
                mock_patient_repo.get_by_patient_id.return_value = _create_mock_patient("patient-1", "patient-user-123")
                mock_patient_repo_cls.return_value = mock_patient_repo

                mock_doctor_repo = AsyncMock()
                mock_doctor_repo_cls.return_value = mock_doctor_repo

                token = _create_patient_token()
                response = client.get("/api/v1/history/", headers={"Authorization": f"Bearer {token}"})
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
                assert data[0]["source_id"] == "report-new"
                assert data[1]["source_id"] == "report-old"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_patient_cannot_access_other_patient_history_via_doctor_endpoint(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        try:
            with patch("app.history.services.history_service.PatientRepository") as mock_patient_repo_cls:
                mock_patient_repo = AsyncMock()
                mock_patient_repo.get_by_patient_id.return_value = None
                mock_patient_repo_cls.return_value = mock_patient_repo

                token = _create_doctor_token()
                response = client.get("/api/v1/history/patient/other-patient", headers={"Authorization": f"Bearer {token}"})
                assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestHistoryConsentGate:
    def test_doctor_without_grant_is_blocked(self):
        from fastapi import HTTPException

        async def _deny(*args, **kwargs):
            raise HTTPException(status_code=404, detail="Access denied")

        app.dependency_overrides[get_current_user] = _override_doctor_user
        try:
            with patch(
                "app.history.router.grant_checks.require_active_grant",
                new=_deny,
            ):
                token = _create_doctor_token()
                response = client.get(
                    "/api/v1/history/patient/patient-1",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)
