import pytest
from unittest.mock import patch, AsyncMock, MagicMock
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


def _create_patient_token():
    from app.core.security import create_access_token
    return create_access_token(data={"sub": "patient-user-123", "email": "patient@test.com", "role": "patient"})


def _override_patient_user():
    from datetime import datetime, timezone
    mock_user = AsyncMock()
    mock_user.id = "patient-user-123"
    mock_user.email = "patient@test.com"
    mock_user.role = "patient"
    mock_user.full_name = "Test Patient"
    mock_user.is_active = True
    mock_user.created_at = datetime.now(timezone.utc)
    mock_user.updated_at = datetime.now(timezone.utc)
    return mock_user


class TestFileValidation:
    def test_valid_txt_file(self):
        from app.reports.services.file_validation import FileValidator
        from fastapi import UploadFile
        validator = FileValidator()
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "report.txt"
        mock_file.size = 1024
        validator.validate(mock_file)

    def test_invalid_extension(self):
        from app.reports.services.file_validation import FileValidator, FileValidationError
        from fastapi import UploadFile
        validator = FileValidator()
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "report.exe"
        mock_file.size = 1024
        with pytest.raises(FileValidationError):
            validator.validate(mock_file)

    def test_file_too_large(self):
        from app.reports.services.file_validation import FileValidator, FileValidationError
        from fastapi import UploadFile
        validator = FileValidator()
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "report.txt"
        mock_file.size = 100 * 1024 * 1024
        with pytest.raises(FileValidationError):
            validator.validate(mock_file)

    def test_empty_filename(self):
        from app.reports.services.file_validation import FileValidator, FileValidationError
        from fastapi import UploadFile
        validator = FileValidator()
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = ""
        mock_file.size = 0
        with pytest.raises(FileValidationError):
            validator.validate(mock_file)


class TestTextNormalization:
    def test_normalize_basic(self):
        from app.reports.services.normalization import TextNormalizationService
        service = TextNormalizationService()
        text = "Hello\r\nWorld\r\n\r\n\r\nThis   is   test"
        result = service.normalize(text)
        assert "\r" not in result
        assert "   " not in result

    def test_normalize_empty(self):
        from app.reports.services.normalization import TextNormalizationService
        service = TextNormalizationService()
        assert service.normalize("") == ""

    def test_normalize_preserves_units(self):
        from app.reports.services.normalization import TextNormalizationService
        service = TextNormalizationService()
        text = "Glucose: 120 mg/dL\nBlood Pressure: 120/80 mmHg"
        result = service.normalize(text)
        assert "120 mg/dL" in result
        assert "120/80 mmHg" in result


class TestUploadEndpoint:
    def test_upload_txt_success(self):
        app.dependency_overrides[get_current_user] = _override_patient_user
        try:
            with patch("app.reports.services.report_service.PDFExtractionService") as mock_pdf, \
                 patch("app.reports.services.report_service.OCRService") as mock_ocr:
                mock_pdf.return_value.has_embedded_text.return_value = False
                mock_ocr.return_value.extract_text.return_value = ""

                token = _create_patient_token()
                response = client.post(
                    "/api/v1/reports/upload",
                    data={"category": "Blood Test", "title": "Test"},
                    files={"file": ("test.txt", b"test content", "text/plain")},
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 201
                data = response.json()
                assert data["status"] == "completed"
                assert "id" in data
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_upload_unauthorized(self):
        response = client.post(
            "/api/v1/reports/upload",
            data={"category": "Blood Test", "title": "Test"},
            files={"file": ("test.txt", b"test content", "text/plain")},
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401
