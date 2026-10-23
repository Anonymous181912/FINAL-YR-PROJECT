import os
import uuid
import logging
from fastapi import UploadFile
from app.core.config import settings

logger = logging.getLogger("healthcare_system")


class FileValidationError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class FileValidator:
    def __init__(self):
        self.allowed_extensions = settings.allowed_extensions_list
        self.max_size = settings.max_upload_size
        self.upload_dir = settings.upload_dir

    def validate(self, file: UploadFile) -> None:
        if not file:
            raise FileValidationError("No file provided")

        filename = file.filename or ""
        if not filename.strip():
            raise FileValidationError("Filename is empty")

        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if ext not in self.allowed_extensions:
            raise FileValidationError(
                f"File extension '{ext}' is not allowed. Allowed: {', '.join(self.allowed_extensions)}"
            )

        if file.size is not None and file.size > self.max_size:
            max_mb = self.max_size / (1024 * 1024)
            raise FileValidationError(f"File size exceeds maximum allowed size of {max_mb:.1f} MB")

    def generate_safe_filename(self, original_filename: str) -> str:
        ext = os.path.splitext(original_filename)[1].lower().lstrip(".")
        return f"{uuid.uuid4().hex}.{ext}"

    def ensure_upload_dir(self) -> str:
        os.makedirs(self.upload_dir, exist_ok=True)
        return self.upload_dir

    def get_full_path(self, safe_filename: str) -> str:
        return os.path.join(self.ensure_upload_dir(), safe_filename)
