import os
import pytest
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.auth.dependencies import get_current_user
from app.models.report import ReportInDB

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


def _create_token(sub, email, role):
    from app.core.security import create_access_token
    return create_access_token(data={"sub": sub, "email": email, "role": role})


def _override_user(user_id, email, role):
    def _override():
        mock_user = AsyncMock()
        mock_user.id = user_id
        mock_user.email = email
        mock_user.role = role
        mock_user.full_name = "Test User"
        mock_user.is_active = True
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        return mock_user
    return _override


def _make_report(report_id="report-123", patient_id="patient-user-123", file_path="uploads/report-123.txt"):
    now = datetime.now(timezone.utc)
    return ReportInDB(
        id=report_id,
        patient_id=patient_id,
        category="Blood Test",
        title="Test Report",
        file_path=file_path,
        created_at=now,
        updated_at=now,
    )


def _mock_repo(report=None, deleted=True):
    mock_instance = AsyncMock()
    mock_instance.get_by_id.return_value = report
    mock_instance.delete.return_value = deleted
    return mock_instance


class TestDeleteReportEndpoint:
    def test_delete_own_report_removes_file_and_returns_204(self):
        app.dependency_overrides[get_current_user] = _override_user(
            "patient-user-123", "patient@test.com", "patient")
        os.makedirs("uploads", exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", dir="uploads") as tmp:
            tmp.write(b"lab data")
            tmp_path = os.path.abspath(tmp.name)
        try:
            report = _make_report(file_path=tmp_path)
            with patch("app.reports.services.report_service.ReportRepository") as mock_repo_cls:
                mock_instance = _mock_repo(report=report, deleted=True)
                mock_repo_cls.return_value = mock_instance
                token = _create_token("patient-user-123", "patient@test.com", "patient")
                response = client.delete(
                    "/api/v1/reports/report-123",
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert response.status_code == 204
            assert not os.path.exists(tmp_path)
            mock_instance.delete.assert_called_once_with("report-123")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            app.dependency_overrides.pop(get_current_user, None)

    def test_delete_same_report_again_returns_404(self):
        app.dependency_overrides[get_current_user] = _override_user(
            "patient-user-123", "patient@test.com", "patient")
        try:
            with patch("app.reports.services.report_service.ReportRepository") as mock_repo_cls:
                mock_repo_cls.return_value = _mock_repo(report=None)
                token = _create_token("patient-user-123", "patient@test.com", "patient")
                response = client.delete(
                    "/api/v1/reports/report-123",
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_delete_other_patients_report_returns_404(self):
        app.dependency_overrides[get_current_user] = _override_user(
            "patient-user-123", "patient@test.com", "patient")
        try:
            report = _make_report(patient_id="other-patient-999")
            with patch("app.reports.services.report_service.ReportRepository") as mock_repo_cls:
                mock_instance = _mock_repo(report=report, deleted=True)
                mock_repo_cls.return_value = mock_instance
                token = _create_token("patient-user-123", "patient@test.com", "patient")
                response = client.delete(
                    "/api/v1/reports/report-123",
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert response.status_code == 404
            mock_instance.delete.assert_not_called()
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_doctor_delete_returns_403(self):
        app.dependency_overrides[get_current_user] = _override_user(
            "doctor-user-456", "doctor@test.com", "doctor")
        try:
            token = _create_token("doctor-user-456", "doctor@test.com", "doctor")
            response = client.delete(
                "/api/v1/reports/report-123",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_unauthenticated_delete_returns_401(self):
        app.dependency_overrides.pop(get_current_user, None)
        response = client.delete("/api/v1/reports/report-123")
        assert response.status_code == 401

    def test_cwd_relative_stored_path_is_removed(self):
        # Regression: stored file_path values look like "uploads/<uuid>.txt"
        # (relative to the server CWD). Deletion must resolve them correctly.
        app.dependency_overrides[get_current_user] = _override_user(
            "patient-user-123", "patient@test.com", "patient")
        os.makedirs("uploads", exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", dir="uploads") as tmp:
            tmp.write(b"lab data")
            rel_path = os.path.join("uploads", os.path.basename(tmp.name))
            abs_path = os.path.abspath(tmp.name)
        try:
            report = _make_report(file_path=rel_path)
            with patch("app.reports.services.report_service.ReportRepository") as mock_repo_cls:
                mock_repo_cls.return_value = _mock_repo(report=report, deleted=True)
                token = _create_token("patient-user-123", "patient@test.com", "patient")
                response = client.delete(
                    "/api/v1/reports/report-123",
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert response.status_code == 204
            assert not os.path.exists(abs_path)
        finally:
            if os.path.exists(abs_path):
                os.remove(abs_path)
            app.dependency_overrides.pop(get_current_user, None)

    def test_missing_file_still_deletes_record(self):
        app.dependency_overrides[get_current_user] = _override_user(
            "patient-user-123", "patient@test.com", "patient")
        try:
            report = _make_report(file_path="uploads/does-not-exist-xyz.txt")
            with patch("app.reports.services.report_service.ReportRepository") as mock_repo_cls:
                mock_instance = _mock_repo(report=report, deleted=True)
                mock_repo_cls.return_value = mock_instance
                token = _create_token("patient-user-123", "patient@test.com", "patient")
                response = client.delete(
                    "/api/v1/reports/report-123",
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert response.status_code == 204
            mock_instance.delete.assert_called_once_with("report-123")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_file_outside_upload_dir_is_never_removed(self):
        app.dependency_overrides[get_current_user] = _override_user(
            "patient-user-123", "patient@test.com", "patient")
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
                tmp.write(b"do not touch")
                outside_path = tmp.name
            assert os.path.dirname(outside_path) not in os.path.abspath("uploads")
            report = _make_report(file_path=outside_path)
            with patch("app.reports.services.report_service.ReportRepository") as mock_repo_cls:
                mock_repo_cls.return_value = _mock_repo(report=report, deleted=True)
                token = _create_token("patient-user-123", "patient@test.com", "patient")
                response = client.delete(
                    "/api/v1/reports/report-123",
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert response.status_code == 204
            assert os.path.exists(outside_path)
            os.remove(outside_path)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
