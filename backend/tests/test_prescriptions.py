import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from starlette.responses import Response
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


def _create_doctor_token():
    from app.core.security import create_access_token
    return create_access_token(data={"sub": "doctor-user-123", "email": "doctor@test.com", "role": "doctor"})


def _create_patient_token():
    from app.core.security import create_access_token
    return create_access_token(data={"sub": "patient-user-123", "email": "patient@test.com", "role": "patient"})


def _override_doctor_user():
    return _create_mock_user("doctor-user-123", "doctor@test.com", "doctor", "Dr. Test")


def _override_patient_user():
    return _create_mock_user("patient-user-123", "patient@test.com", "patient", "Test Patient")


def _mock_prescription_service(monkeypatch=None):
    mock_repo = AsyncMock()
    mock_patient_repo = AsyncMock()
    mock_doctor_repo = AsyncMock()
    mock_pdf_service = MagicMock()

    service = MagicMock()
    service.repo = mock_repo
    service.patient_repo = mock_patient_repo
    service.doctor_repo = mock_doctor_repo
    service.pdf_service = mock_pdf_service

    return service, mock_repo, mock_patient_repo, mock_doctor_repo, mock_pdf_service


class TestPrescriptionAuth:
    def test_patient_cannot_create_prescription(self):
        app.dependency_overrides[get_current_user] = _override_patient_user
        try:
            token = _create_patient_token()
            response = client.post(
                "/api/v1/prescriptions",
                json={"patient_id": "patient-1", "items": [{"medicine_name": "Aspirin", "dosage": "100mg", "frequency": "OD", "duration": "3 days"}]},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_unauthenticated_cannot_access_prescriptions(self):
        response = client.get("/api/v1/prescriptions/doctor")
        assert response.status_code == 401

    def test_doctor_can_create_prescription(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        try:
            with patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as mock_rx_repo_cls, \
                 patch("app.prescriptions.services.prescription_service.PatientRepository") as mock_patient_repo_cls, \
                 patch("app.prescriptions.services.prescription_service.DoctorRepository") as mock_doctor_repo_cls:
                mock_rx_repo = AsyncMock()
                mock_rx_repo.create_prescription.return_value = _create_mock_rx("rx-123", "patient-1", "doctor-user-123")
                mock_rx_repo_cls.return_value = mock_rx_repo

                mock_patient_repo = AsyncMock()
                mock_patient_repo.get_by_patient_id.return_value = _create_mock_patient("patient-1", "patient-user-123")
                mock_patient_repo_cls.return_value = mock_patient_repo

                mock_doctor_repo = AsyncMock()
                mock_doctor_repo.get_by_doctor_id.return_value = _create_mock_doctor("doctor-1", "doctor-user-123")
                mock_doctor_repo_cls.return_value = mock_doctor_repo

                token = _create_doctor_token()
                response = client.post(
                    "/api/v1/prescriptions",
                    json={
                        "patient_id": "patient-1",
                        "items": [{"medicine_name": "Aspirin", "dosage": "100mg", "frequency": "OD", "duration": "3 days"}],
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 201
                data = response.json()
                assert data["id"] == "rx-123"
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestPrescriptionCRUD:
    def test_doctor_lists_own_prescriptions(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        try:
            with patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.list_by_doctor.return_value = []
                mock_repo_cls.return_value = mock_repo

                token = _create_doctor_token()
                response = client.get("/api/v1/prescriptions/doctor", headers={"Authorization": f"Bearer {token}"})
                assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_patient_lists_own_prescriptions(self):
        app.dependency_overrides[get_current_user] = _override_patient_user
        try:
            with patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.list_by_patient.return_value = []
                mock_repo_cls.return_value = mock_repo

                token = _create_patient_token()
                response = client.get("/api/v1/prescriptions/patient", headers={"Authorization": f"Bearer {token}"})
                assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_get_prescription_owner_access(self):
        app.dependency_overrides[get_current_user] = _override_patient_user
        try:
            with patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = _create_mock_rx("rx-123", "patient-user-123", "doctor-user-123")
                mock_repo_cls.return_value = mock_repo

                token = _create_patient_token()
                response = client.get("/api/v1/prescriptions/rx-123", headers={"Authorization": f"Bearer {token}"})
                assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_patient_cannot_access_other_prescription(self):
        app.dependency_overrides[get_current_user] = _override_patient_user
        try:
            with patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = _create_mock_rx("rx-123", "other-patient", "doctor-user-123")
                mock_repo_cls.return_value = mock_repo

                token = _create_patient_token()
                response = client.get("/api/v1/prescriptions/rx-123", headers={"Authorization": f"Bearer {token}"})
                assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_doctor_updates_own_prescription(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        try:
            with patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = _create_mock_rx("rx-123", "patient-1", "doctor-user-123")
                mock_repo.update_prescription.return_value = _create_mock_rx("rx-123", "patient-1", "doctor-user-123", diagnosis_notes="Updated notes")
                mock_repo_cls.return_value = mock_repo

                token = _create_doctor_token()
                response = client.put(
                    "/api/v1/prescriptions/rx-123",
                    json={"diagnosis_notes": "Updated notes"},
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_other_doctor_cannot_update_prescription(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        try:
            with patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = _create_mock_rx("rx-123", "patient-1", "other-doctor")
                mock_repo_cls.return_value = mock_repo

                token = _create_doctor_token()
                response = client.put(
                    "/api/v1/prescriptions/rx-123",
                    json={"diagnosis_notes": "Hacked"},
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_doctor_deletes_own_prescription(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        try:
            with patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as mock_repo_cls, \
                 patch("app.prescriptions.services.prescription_service.os.path.exists", return_value=False), \
                 patch("app.prescriptions.services.prescription_service.os.remove"):
                mock_repo = AsyncMock()
                mock_rx = _create_mock_rx("rx-123", "patient-1", "doctor-user-123")
                mock_rx.file_path = None
                mock_repo.get_by_id.return_value = mock_rx
                mock_repo.delete.return_value = True
                mock_repo_cls.return_value = mock_repo

                token = _create_doctor_token()
                response = client.delete("/api/v1/prescriptions/rx-123", headers={"Authorization": f"Bearer {token}"})
                assert response.status_code == 204
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestPrescriptionValidation:
    def test_empty_medicine_name_rejected(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        try:
            token = _create_doctor_token()
            response = client.post(
                "/api/v1/prescriptions",
                json={
                    "patient_id": "patient-1",
                    "items": [{"medicine_name": "", "dosage": "100mg", "frequency": "OD", "duration": "3 days"}],
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_invalid_patient_returns_error(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        try:
            with patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as mock_rx_repo_cls, \
                 patch("app.prescriptions.services.prescription_service.PatientRepository") as mock_patient_repo_cls, \
                 patch("app.prescriptions.services.prescription_service.DoctorRepository") as mock_doctor_repo_cls:
                mock_rx_repo = AsyncMock()
                mock_rx_repo_cls.return_value = mock_rx_repo

                mock_patient_repo = AsyncMock()
                mock_patient_repo.get_by_patient_id.return_value = None
                mock_patient_repo_cls.return_value = mock_patient_repo

                mock_doctor_repo = AsyncMock()
                mock_doctor_repo.get_by_doctor_id.return_value = _create_mock_doctor("doctor-1", "doctor-user-123")
                mock_doctor_repo_cls.return_value = mock_doctor_repo

                token = _create_doctor_token()
                response = client.post(
                    "/api/v1/prescriptions",
                    json={
                        "patient_id": "non-existent",
                        "items": [{"medicine_name": "Aspirin", "dosage": "100mg", "frequency": "OD", "duration": "3 days"}],
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 400
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestPrescriptionPDF:
    def test_pdf_generation_succeeds(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        try:
            with patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as mock_repo_cls, \
                 patch("app.prescriptions.services.prescription_service.PatientRepository") as mock_patient_repo_cls, \
                 patch("app.prescriptions.services.prescription_service.DoctorRepository") as mock_doctor_repo_cls, \
                 patch("app.prescriptions.services.pdf_service.os.path.exists", return_value=True), \
                 patch("starlette.responses.FileResponse", return_value=Response(content=b"%PDF-1.4", media_type="application/pdf")):
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = _create_mock_rx("rx-123", "patient-1", "doctor-user-123")
                mock_repo.update_prescription.return_value = _create_mock_rx("rx-123", "patient-1", "doctor-user-123")
                mock_repo_cls.return_value = mock_repo

                mock_patient_repo = AsyncMock()
                mock_patient_repo.get_by_patient_id.return_value = _create_mock_patient("patient-1", "patient-user-123")
                mock_patient_repo_cls.return_value = mock_patient_repo

                mock_doctor_repo = AsyncMock()
                mock_doctor_repo.get_by_doctor_id.return_value = _create_mock_doctor("doctor-1", "doctor-user-123")
                mock_doctor_repo_cls.return_value = mock_doctor_repo

                token = _create_doctor_token()
                response = client.post("/api/v1/prescriptions/rx-123/pdf", headers={"Authorization": f"Bearer {token}"})
                assert response.status_code == 200
                assert response.headers["content-type"] == "application/pdf"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_unauthorized_cannot_download_pdf(self):
        app.dependency_overrides[get_current_user] = _override_patient_user
        try:
            with patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = _create_mock_rx("rx-123", "other-patient", "doctor-user-123")
                mock_repo_cls.return_value = mock_repo

                token = _create_patient_token()
                response = client.post("/api/v1/prescriptions/rx-123/pdf", headers={"Authorization": f"Bearer {token}"})
                assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)


def _create_mock_rx(rx_id, patient_id, doctor_id, **kwargs):
    from datetime import datetime, timezone
    defaults = {
        "id": rx_id,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "prescription_date": None,
        "diagnosis_notes": None,
        "advice": None,
        "follow_up_date": None,
        "items": [{"medicine_name": "Aspirin", "dosage": "100mg", "frequency": "OD", "duration": "3 days"}],
        "status": "draft",
        "file_path": None,
        "safety_warnings": [],
        "acknowledged_warnings": False,
        "verification_token": None,
        "verification_status": "valid",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "issued_at": None,
    }
    defaults.update(kwargs)
    mock_rx = AsyncMock()
    for key, value in defaults.items():
        setattr(mock_rx, key, value)
    return mock_rx
