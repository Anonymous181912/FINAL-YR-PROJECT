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
    mock_patient.patient_code = "PAT-ABC12"
    mock_patient.allow_prescriptions = True
    mock_patient.emergency_token = None
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
            from datetime import datetime, timezone
            from unittest.mock import MagicMock
            mock_patient = MagicMock()
            mock_patient.id = "patient-1"
            mock_patient.user_id = "patient-user-123"
            mock_patient.patient_id = "patient-1"
            mock_patient.full_name = "Test Patient"
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
            mock_patient.patient_code = "PAT-ABC12"
            mock_patient.allow_prescriptions = True
            mock_patient.emergency_token = None
            mock_patient.created_at = datetime.now(timezone.utc)
            mock_patient.updated_at = datetime.now(timezone.utc)
            
            mock_rx_repo = AsyncMock()
            mock_rx_repo.create_prescription.return_value = _create_mock_rx("rx-123", "patient-1", "doctor-user-123")
            
            mock_doctor_repo = AsyncMock()
            mock_doctor_repo.get_by_doctor_id.return_value = _create_mock_doctor("doctor-1", "doctor-user-123")
            
            # Patch the get_by_patient_id method on the PatientRepository class
            with patch("app.prescriptions.router.PatientRepository.get_by_patient_id", new_callable=AsyncMock, return_value=mock_patient), \
                 patch("app.prescriptions.services.prescription_service.PrescriptionRepository", return_value=mock_rx_repo), \
                 patch("app.prescriptions.services.prescription_service.DoctorRepository", return_value=mock_doctor_repo):
                
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
                mock_repo.list_by_patient_ids.return_value = []
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
            with patch("app.prescriptions.router.PatientRepository", autospec=True) as mock_patient_repo_cls, \
                 patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as mock_rx_repo_cls, \
                 patch("app.prescriptions.services.prescription_service.DoctorRepository") as mock_doctor_repo_cls:
                mock_rx_repo = AsyncMock()
                mock_rx_repo_cls.return_value = mock_rx_repo

                mock_patient_repo = AsyncMock()
                mock_patient_repo.get_by_patient_id = AsyncMock(return_value=None)
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
                assert response.status_code == 404
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

class TestPrescriptionIssueFlow:
    def _doctor_repo(self):
        repo = MagicMock()
        repo.get_by_doctor_id = AsyncMock(return_value=_create_mock_doctor("doctor-1", "doctor-user-123"))
        return MagicMock(return_value=repo)

    def test_doctor_issues_draft_and_notifies_patient(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        try:
            draft = _create_mock_rx("rx-123", "patient-1", "doctor-user-123", status="draft")
            issued = _create_mock_rx("rx-123", "patient-1", "doctor-user-123", status="issued")

            service = MagicMock()
            service.get_prescription = AsyncMock(return_value=draft)
            service.update_prescription = AsyncMock(return_value=issued)
            service.generate_pdf = AsyncMock(return_value="rx-123.pdf")
            notification_repo = AsyncMock()

            with patch("app.prescriptions.router.PrescriptionService", return_value=service), \
                 patch("app.prescriptions.router.NotificationRepository", return_value=notification_repo), \
                 patch("app.prescriptions.router.DoctorRepository", new=self._doctor_repo()):
                token = _create_doctor_token()
                response = client.post(
                    "/api/v1/prescriptions/rx-123/issue",
                    headers={"Authorization": f"Bearer {token}"},
                )

            assert response.status_code == 200
            assert response.json()["status"] == "issued"
            service.update_prescription.assert_awaited_once()
            assert service.update_prescription.await_args.kwargs["status"] == "issued"
            service.generate_pdf.assert_awaited_once()
            notification_repo.create_notification.assert_awaited_once()
            kwargs = notification_repo.create_notification.await_args.kwargs
            assert kwargs["user_id"] == "patient-1"
            assert kwargs["kind"] == "prescription_issued"
            assert kwargs["ref_id"] == "rx-123"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_other_doctor_cannot_issue(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        try:
            with patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_id.return_value = _create_mock_rx("rx-123", "patient-1", "other-doctor")
                mock_repo_cls.return_value = mock_repo

                token = _create_doctor_token()
                response = client.post(
                    "/api/v1/prescriptions/rx-123/issue",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_already_issued_cannot_be_reissued(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        try:
            issued = _create_mock_rx("rx-123", "patient-1", "doctor-user-123", status="issued")
            service = MagicMock()
            service.get_prescription = AsyncMock(return_value=issued)
            service.update_prescription = AsyncMock()
            service.generate_pdf = AsyncMock()

            with patch("app.prescriptions.router.PrescriptionService", return_value=service):
                token = _create_doctor_token()
                response = client.post(
                    "/api/v1/prescriptions/rx-123/issue",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 400
            service.update_prescription.assert_not_awaited()
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_unverified_doctor_cannot_issue(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        unverified = _create_mock_doctor("doctor-1", "doctor-user-123")
        unverified.is_verified = False
        unverified.verification_status = "pending"
        try:
            with patch(
                "app.database.repositories.doctor_repository.DoctorRepository.get_by_user_id",
                new=AsyncMock(return_value=unverified),
            ):
                token = _create_doctor_token()
                response = client.post(
                    "/api/v1/prescriptions/rx-123/issue",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestPrescriptionPatientVisibility:
    def test_patient_list_requests_only_issued(self):
        app.dependency_overrides[get_current_user] = _override_patient_user
        try:
            with patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.list_by_patient_ids.return_value = []
                mock_repo_cls.return_value = mock_repo

                token = _create_patient_token()
                response = client.get(
                    "/api/v1/prescriptions/patient",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 200
                assert mock_repo.list_by_patient_ids.await_args.kwargs["status"] == "issued"
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestPrescribingPermission:
    def test_disabled_prescriptions_blocks_doctor_create(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        try:
            blocked_patient = _create_mock_patient("patient-1", "patient-user-123")
            blocked_patient.allow_prescriptions = False

            with patch("app.prescriptions.router.PatientRepository") as mock_patient_repo_cls:
                mock_patient_repo = AsyncMock()
                mock_patient_repo.get_by_patient_id.return_value = blocked_patient
                mock_patient_repo_cls.return_value = mock_patient_repo

                token = _create_doctor_token()
                response = client.post(
                    "/api/v1/prescriptions",
                    json={
                        "patient_id": "patient-1",
                        "items": [{"medicine_name": "Aspirin", "dosage": "100mg", "frequency": "OD", "duration": "3 days"}],
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 403
                assert "disabled prescription writing" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_allow_prescriptions_defaults_to_true(self):
        from app.models.patient import PatientBase

        profile = PatientBase(full_name="Default Patient")
        assert profile.allow_prescriptions is True


class TestCanonicalPatientOwnership:
    def test_profile_id_differs_from_user_id_still_list_open_and_download(self):
        patient_user_id = "patient-user-123"
        profile_id = "profile-9"
        canonical_id = "PATIENT-9"

        profile = _create_mock_patient(profile_id, patient_user_id)
        profile.patient_id = canonical_id

        draft = _create_mock_rx("rx-123", canonical_id, "doctor-user-123", status="draft")
        issued = _create_mock_rx("rx-123", canonical_id, "doctor-user-123", status="issued")

        # 1) Doctor issues the draft (stores/returns the canonical patient id).
        app.dependency_overrides[get_current_user] = _override_doctor_user
        try:
            issue_service = MagicMock()
            issue_service.get_prescription = AsyncMock(return_value=draft)
            issue_service.update_prescription = AsyncMock(return_value=issued)
            issue_service.generate_pdf = AsyncMock(return_value="rx-123.pdf")

            doctor = _create_mock_doctor("doctor-1", "doctor-user-123")
            doctor_repo = MagicMock()
            doctor_repo.get_by_doctor_id = AsyncMock(return_value=doctor)
            doctor_repo_factory = MagicMock(return_value=doctor_repo)

            with patch("app.prescriptions.router.PrescriptionService", return_value=issue_service), \
                 patch("app.prescriptions.router.NotificationRepository", return_value=AsyncMock()), \
                 patch("app.prescriptions.router.DoctorRepository", new=doctor_repo_factory):
                token = _create_doctor_token()
                response = client.post(
                    "/api/v1/prescriptions/rx-123/issue",
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert response.status_code == 200
            assert response.json()["status"] == "issued"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        # 2-3) Patient lists and opens the issued prescription.
        app.dependency_overrides[get_current_user] = _override_patient_user
        try:
            with patch("app.prescriptions.services.prescription_service.PatientRepository") as patient_repo_cls, \
                 patch("app.prescriptions.services.prescription_service.PrescriptionRepository") as rx_repo_cls:
                patient_repo = AsyncMock()
                patient_repo.get_by_user_id.return_value = profile
                patient_repo_cls.return_value = patient_repo

                rx_repo = AsyncMock()
                rx_repo.list_by_patient_ids.return_value = [issued]
                rx_repo.get_by_id.return_value = issued
                rx_repo_cls.return_value = rx_repo

                token = _create_patient_token()
                listed = client.get(
                    "/api/v1/prescriptions/patient",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert listed.status_code == 200
                assert [p["id"] for p in listed.json()] == ["rx-123"]
                queried_ids = set(rx_repo.list_by_patient_ids.await_args.args[0])
                assert queried_ids == {canonical_id, profile_id, patient_user_id}

                opened = client.get(
                    "/api/v1/prescriptions/rx-123",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert opened.status_code == 200
                assert opened.json()["patient_id"] == canonical_id

            # 4) Patient downloads the PDF.
            pdf_service = MagicMock()
            pdf_service.get_prescription = AsyncMock(return_value=issued)
            pdf_service.generate_pdf = AsyncMock(return_value="rx-123.pdf")
            with patch("app.prescriptions.router.PrescriptionService", return_value=pdf_service), \
                 patch("app.prescriptions.router.FileResponse", return_value=Response(content=b"%PDF-1.4", media_type="application/pdf")):
                token = _create_patient_token()
                downloaded = client.post(
                    "/api/v1/prescriptions/rx-123/pdf",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert downloaded.status_code == 200
                assert downloaded.headers["content-type"] == "application/pdf"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
