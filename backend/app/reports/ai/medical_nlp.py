import logging
from typing import Optional, Any
from app.reports.ai.rule_based_extractor import RuleBasedExtractor

logger = logging.getLogger("healthcare_system")


class MedicalNLPError(Exception):
    pass


class MedicalNLPService:
    def __init__(self):
        self._extractor = RuleBasedExtractor()

    async def extract_entities(self, text: str) -> list[dict[str, Any]]:
        if not text or not text.strip():
            return []
        try:
            entities = self._extractor.extract(text)
            return entities
        except Exception as exc:
            logger.error(f"Medical NLP extraction failed: {exc}")
            raise MedicalNLPError("Medical entity extraction failed") from exc
