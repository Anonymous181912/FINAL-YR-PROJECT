import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app

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
    mock_user.failed_login_attempts = 0
    mock_user.locked_until = None
    mock_user.created_at = datetime.now(timezone.utc)
    mock_user.updated_at = datetime.now(timezone.utc)
    return mock_user


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Healthcare System API" in response.json()["message"]


class TestAuth:
    def test_register_success(self):
        with patch("app.auth.router.UserRepository") as mock_user_repo, \
             patch("app.auth.router.PatientRepository") as mock_patient_repo:
            mock_user = _create_mock_user("user-123", "patient@test.com", "patient", "Test Patient")

            mock_user_instance = AsyncMock()
            mock_user_instance.exists_email.return_value = False
            mock_user_instance.create_user.return_value = mock_user
            mock_user_repo.return_value = mock_user_instance

            mock_patient_instance = AsyncMock()
            mock_patient_repo.return_value = mock_patient_instance

            response = client.post(
                "/api/v1/auth/register",
                json={"email": "patient@test.com", "password": "pass1234", "role": "patient", "full_name": "Test Patient"},
            )
            assert response.status_code == 201
            data = response.json()
            assert "access_token" in data
            assert data["role"] == "patient"

    def test_register_doctor_creates_pending_profile(self):
        with patch("app.auth.router.UserRepository") as mock_user_repo, \
             patch("app.auth.router.DoctorRepository") as mock_doctor_repo:
            mock_user = _create_mock_user("doc-123", "doc@test.com", "doctor", "Dr. Test")

            mock_user_instance = AsyncMock()
            mock_user_instance.exists_email.return_value = False
            mock_user_instance.create_user.return_value = mock_user
            mock_user_repo.return_value = mock_user_instance

            mock_doctor_instance = AsyncMock()
            mock_doctor_repo.return_value = mock_doctor_instance

            response = client.post(
                "/api/v1/auth/register",
                json={"email": "doc@test.com", "password": "Docpass123", "role": "doctor", "full_name": "Dr. Test", "license_number": "LIC-1"},
            )
            assert response.status_code == 201
            # Doctor profile must be created unverified/pending.
            _, kwargs = mock_doctor_instance.create_profile.call_args
            assert kwargs.get("is_verified") is False
            assert kwargs.get("verification_status") == "pending"

    def test_register_duplicate_email(self):
        with patch("app.auth.router.UserRepository") as mock_user_repo:
            mock_user_instance = AsyncMock()
            mock_user_instance.exists_email.return_value = True
            mock_user_repo.return_value = mock_user_instance

            response = client.post(
                "/api/v1/auth/register",
                json={"email": "exists@test.com", "password": "pass1234", "role": "patient", "full_name": "Test Patient"},
            )
            assert response.status_code == 409

    def test_register_invalid_role(self):
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "test@test.com", "password": "pass1234", "role": "admin", "full_name": "Test User"},
        )
        assert response.status_code == 422

    def test_register_short_password(self):
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "test@test.com", "password": "short", "role": "patient", "full_name": "Test Patient"},
        )
        assert response.status_code == 422

    def test_register_password_requires_letter_and_digit(self):
        # No digit.
        r1 = client.post(
            "/api/v1/auth/register",
            json={"email": "a@test.com", "password": "passwordonly", "role": "patient", "full_name": "Test Patient"},
        )
        assert r1.status_code == 422
        # No letter.
        r2 = client.post(
            "/api/v1/auth/register",
            json={"email": "b@test.com", "password": "12345678", "role": "patient", "full_name": "Test Patient"},
        )
        assert r2.status_code == 422

    def test_login_success(self):
        with patch("app.auth.router.UserRepository") as mock_user_repo:
            from app.core.security import get_password_hash
            mock_user = _create_mock_user("user-123", "doctor@test.com", "doctor", "Dr. Test")
            mock_user.hashed_password = get_password_hash("password123")

            mock_user_instance = AsyncMock()
            mock_user_instance.get_by_email.return_value = mock_user
            mock_user_repo.return_value = mock_user_instance

            response = client.post("/api/v1/auth/login", data={"username": "doctor@test.com", "password": "password123"})
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["role"] == "doctor"

    def test_login_wrong_password(self):
        with patch("app.auth.router.UserRepository") as mock_user_repo:
            mock_user_instance = AsyncMock()
            mock_user_instance.get_by_email.return_value = None
            mock_user_repo.return_value = mock_user_instance

            response = client.post("/api/v1/auth/login", data={"username": "nobody@test.com", "password": "wrong"})
            assert response.status_code == 401

    def test_login_inactive_user(self):
        with patch("app.auth.router.UserRepository") as mock_user_repo:
            from app.core.security import get_password_hash
            mock_user = _create_mock_user("user-123", "inactive@test.com", "patient", "Inactive User")
            mock_user.hashed_password = get_password_hash("password123")
            mock_user.is_active = False

            mock_user_instance = AsyncMock()
            mock_user_instance.get_by_email.return_value = mock_user
            mock_user_repo.return_value = mock_user_instance

            response = client.post("/api/v1/auth/login", data={"username": "inactive@test.com", "password": "password123"})
            assert response.status_code == 403

    def test_auth_me_without_token(self):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_auth_me_with_invalid_token(self):
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"})
        assert response.status_code == 401

    def test_auth_me_with_valid_token(self):
        with patch("app.auth.dependencies.UserRepository") as mock_user_repo:
            from app.core.security import create_access_token
            mock_user = _create_mock_user("user-123", "test@test.com", "patient", "Test User")

            mock_user_instance = AsyncMock()
            mock_user_instance.get_by_id.return_value = mock_user
            mock_user_repo.return_value = mock_user_instance

            token = create_access_token(data={"sub": "user-123", "email": "test@test.com", "role": "patient"})
            response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "user-123"
            assert data["role"] == "patient"
