import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("healthcare_system")


class PDFExtractionError(Exception):
    pass


class PDFExtractionService:
    def extract_text(self, file_path: str) -> str:
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise PDFExtractionError("PyMuPDF is not installed") from exc

        try:
            doc = fitz.open(file_path)
            texts = []
            for page in doc:
                texts.append(page.get_text())
            doc.close()
            return "\n".join(texts)
        except Exception as exc:
            logger.error(f"PDF text extraction failed: {exc}")
            raise PDFExtractionError("Failed to extract text from PDF") from exc

    def has_embedded_text(self, file_path: str) -> bool:
        try:
            import fitz
            doc = fitz.open(file_path)
            for page in doc:
                text = page.get_text().strip()
                if text:
                    doc.close()
                    return True
            doc.close()
            return False
        except Exception:
            return False
