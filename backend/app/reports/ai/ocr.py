import io
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("healthcare_system")


class OCRServiceError(Exception):
    pass


class OCRService:
    def __init__(self):
        self._paddle_reader = None
        self._easy_reader = None
        self._paddle_ok = False
        self._easy_ok = False

    def _init_paddle(self):
        try:
            from paddleocr import PaddleOCR
            import inspect
            params = inspect.signature(PaddleOCR.__init__).parameters
            kwargs = {"lang": "en"}
            if "use_textline_orientation" in params:
                kwargs["use_textline_orientation"] = True
            self._paddle_reader = PaddleOCR(**kwargs)
            self._paddle_ok = True
            logger.info("PaddleOCR initialized")
            return True
        except Exception as exc:
            logger.warning(f"PaddleOCR init failed: {exc}")
            return False

    def _init_easy(self):
        try:
            import easyocr
            self._easy_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            self._easy_ok = True
            logger.info("easyocr initialized")
            return True
        except Exception as exc:
            logger.warning(f"easyocr init failed: {exc}")
            return False

    def _get_reader(self):
        """Lazily initialise OCR engines and report their readiness.

        Previously referenced a non-existent ``self._reader`` (AttributeError
        if ever called). Returns a dict describing which engines are ready.
        """
        if not self._paddle_ok:
            self._init_paddle()
        if not self._easy_ok:
            self._init_easy()
        return {"paddle": self._paddle_reader, "easy": self._easy_reader}

    def requires_ocr(self, file_path: str, file_extension: str) -> bool:
        text_extensions = {"txt", "csv", "json"}
        if file_extension.lower() in text_extensions:
            return False
        return True

    def _extract_paddle(self, file_path: str) -> str:
        result = self._paddle_reader.ocr(file_path)
        texts = []
        for line in result:
            if line:
                for word_info in line:
                    if word_info and len(word_info) >= 2 and word_info[1]:
                        texts.append(word_info[1][0])
        return "\n".join(texts)

    def _extract_easy(self, file_path: str) -> str:
        result = self._easy_reader.readtext(file_path)
        texts = []
        for line in result:
            if line and len(line) >= 2 and line[1]:
                texts.append(line[1])
        return "\n".join(texts)

    async def extract_text(self, file_path: str) -> str:
        # Try PaddleOCR first
        if self._paddle_ok and self._paddle_reader is not None:
            try:
                text = self._extract_paddle(file_path)
                if text.strip():
                    return text
            except Exception as exc:
                logger.warning(f"PaddleOCR extraction failed, trying easyocr: {exc}")

        # Try easyocr
        if not self._easy_ok:
            self._init_easy()

        if self._easy_ok and self._easy_reader is not None:
            try:
                text = self._extract_easy(file_path)
                if text.strip():
                    return text
            except Exception as exc:
                logger.error(f"easyocr extraction failed: {exc}")

        raise OCRServiceError("Failed to extract text from image")