import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.auth.dependencies import get_current_user, get_current_patient, get_current_doctor

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


def _create_mock_profile(profile_id, user_id, full_name, **kwargs):
    from datetime import datetime, timezone
    defaults = {
        "id": profile_id,
        "user_id": user_id,
        "patient_id": None,
        "doctor_id": None,
        "full_name": full_name,
        "date_of_birth": None,
        "gender": None,
        "specialization": None,
        "contact_phone": None,
        "contact_email": None,
        "address": None,
        "emergency_contact_name": None,
        "emergency_contact_phone": None,
        "blood_group": None,
        "allergies": [],
        "license_number": None,
        "is_verified": False,
        "verification_status": "pending",
        "is_active": True,
        "patient_code": "PAT-ABC12",
        "allow_prescriptions": True,
        "emergency_token": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    mock_profile = AsyncMock()
    for key, value in defaults.items():
        setattr(mock_profile, key, value)
    return mock_profile


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


class TestPatientProfile:
    def test_get_patient_profile_success(self):
        app.dependency_overrides[get_current_user] = _override_patient_user
        with patch("app.patients.router.PatientRepository") as mock_patient_repo:
            mock_profile = _create_mock_profile(
                "profile-123", "patient-user-123", "Test Patient",
                gender="male", contact_phone="+1234567890", contact_email="patient@test.com"
            )

            mock_patient_instance = AsyncMock()
            mock_patient_instance.get_by_user_id.return_value = mock_profile
            mock_patient_repo.return_value = mock_patient_instance

            token = _create_patient_token()
            response = client.get("/api/v1/patients/me", headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 200
            data = response.json()
            assert data["full_name"] == "Test Patient"
        app.dependency_overrides.pop(get_current_user, None)

    def test_get_patient_profile_not_found(self):
        app.dependency_overrides[get_current_user] = _override_patient_user
        with patch("app.patients.router.PatientRepository") as mock_patient_repo:
            mock_patient_instance = AsyncMock()
            mock_patient_instance.get_by_user_id.return_value = None
            mock_patient_repo.return_value = mock_patient_instance

            token = _create_patient_token()
            response = client.get("/api/v1/patients/me", headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 404
        app.dependency_overrides.pop(get_current_user, None)

    def test_update_patient_profile_success(self):
        app.dependency_overrides[get_current_user] = _override_patient_user
        with patch("app.patients.router.PatientRepository") as mock_patient_repo:
            mock_profile = _create_mock_profile("profile-123", "patient-user-123", "Test Patient")

            mock_patient_instance = AsyncMock()
            mock_patient_instance.get_by_user_id.return_value = mock_profile

            updated_profile = _create_mock_profile(
                "profile-123", "patient-user-123", "Updated Patient",
                gender="male", contact_phone="+1234567890", contact_email="patient@test.com"
            )
            mock_patient_instance.update_profile.return_value = updated_profile
            mock_patient_repo.return_value = mock_patient_instance

            token = _create_patient_token()
            response = client.put(
                "/api/v1/patients/me",
                json={"full_name": "Updated Patient", "gender": "male", "contact_phone": "+1234567890"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["full_name"] == "Updated Patient"
        app.dependency_overrides.pop(get_current_user, None)

    def test_doctor_cannot_access_patient_profile(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        token = _create_doctor_token()
        response = client.get("/api/v1/patients/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
        app.dependency_overrides.pop(get_current_user, None)


class TestDoctorProfile:
    def test_get_doctor_profile_success(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        with patch("app.doctors.router.DoctorRepository") as mock_doctor_repo:
            mock_profile = _create_mock_profile(
                "profile-123", "doctor-user-123", "Dr. Test",
                doctor_id="DR-123", specialization="Cardiology", contact_phone="+1234567890",
                contact_email="doctor@test.com", license_number="LIC-123"
            )

            mock_doctor_instance = AsyncMock()
            mock_doctor_instance.get_by_user_id.return_value = mock_profile
            mock_doctor_repo.return_value = mock_doctor_instance

            token = _create_doctor_token()
            response = client.get("/api/v1/doctors/me", headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 200
            data = response.json()
            assert data["full_name"] == "Dr. Test"
        app.dependency_overrides.pop(get_current_user, None)

    def test_get_doctor_profile_not_found(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        with patch("app.doctors.router.DoctorRepository") as mock_doctor_repo:
            mock_doctor_instance = AsyncMock()
            mock_doctor_instance.get_by_user_id.return_value = None
            mock_doctor_repo.return_value = mock_doctor_instance

            token = _create_doctor_token()
            response = client.get("/api/v1/doctors/me", headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 404
        app.dependency_overrides.pop(get_current_user, None)

    def test_update_doctor_profile_success(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        with patch("app.doctors.router.DoctorRepository") as mock_doctor_repo:
            mock_profile = _create_mock_profile(
                "profile-123", "doctor-user-123", "Dr. Test",
                doctor_id="DR-123", specialization=None, contact_phone=None,
                contact_email=None, license_number=None
            )

            mock_doctor_instance = AsyncMock()
            mock_doctor_instance.get_by_user_id.return_value = mock_profile

            updated_profile = _create_mock_profile(
                "profile-123", "doctor-user-123", "Dr. Test",
                doctor_id="DR-123", specialization="Neurology", contact_phone="+1234567890",
                contact_email="doctor@test.com", license_number="LIC-456"
            )
            mock_doctor_instance.update_profile.return_value = updated_profile
            mock_doctor_repo.return_value = mock_doctor_instance

            token = _create_doctor_token()
            response = client.put(
                "/api/v1/doctors/me",
                json={"specialization": "Neurology", "license_number": "LIC-456"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["specialization"] == "Neurology"
        app.dependency_overrides.pop(get_current_user, None)

    def test_patient_cannot_access_doctor_profile(self):
        app.dependency_overrides[get_current_user] = _override_patient_user
        token = _create_patient_token()
        response = client.get("/api/v1/doctors/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
        app.dependency_overrides.pop(get_current_user, None)


class TestPatientSearch:
    def test_search_returns_canonical_patient_id_and_code(self):
        app.dependency_overrides[get_current_user] = _override_doctor_user
        try:
            with patch("app.patients.router.PatientRepository") as mock_patient_repo:
                profile = _create_mock_profile(
                    "profile-1", "user-1", "Jane Doe",
                    patient_id=None, patient_code="PAT-XYZ12",
                )
                mock_patient_instance = AsyncMock()
                mock_patient_instance.search_patients.return_value = [profile]
                mock_patient_repo.return_value = mock_patient_instance

                token = _create_doctor_token()
                response = client.get(
                    "/api/v1/patients/search",
                    params={"q": "jane"},
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 200
                data = response.json()
                assert data[0]["full_name"] == "Jane Doe"
                assert data[0]["patient_id"] == "user-1"
                assert data[0]["patient_code"] == "PAT-XYZ12"
                mock_patient_instance.search_patients.assert_awaited_once_with("jane", limit=20)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_patient_cannot_search_patients(self):
        app.dependency_overrides[get_current_user] = _override_patient_user
        try:
            token = _create_patient_token()
            response = client.get(
                "/api/v1/patients/search",
                params={"q": "jane"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestPrescriptionPermissionSetting:
    def test_patient_can_disable_prescriptions(self):
        app.dependency_overrides[get_current_user] = _override_patient_user
        try:
            with patch("app.patients.router.PatientRepository") as mock_patient_repo:
                existing = _create_mock_profile("profile-1", "patient-user-123", "Test Patient")
                updated = _create_mock_profile(
                    "profile-1", "patient-user-123", "Test Patient",
                    allow_prescriptions=False,
                )
                mock_patient_instance = AsyncMock()
                mock_patient_instance.get_by_user_id.return_value = existing
                mock_patient_instance.update_profile.return_value = updated
                mock_patient_repo.return_value = mock_patient_instance

                token = _create_patient_token()
                response = client.put(
                    "/api/v1/patients/me",
                    json={"allow_prescriptions": False},
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 200
                assert response.json()["allow_prescriptions"] is False
                assert mock_patient_instance.update_profile.await_args.kwargs["allow_prescriptions"] is False
        finally:
            app.dependency_overrides.pop(get_current_user, None)
