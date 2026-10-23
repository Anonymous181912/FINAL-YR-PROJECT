import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("healthcare_system")


class NLPServiceError(Exception):
    pass


class NLPService:
    def __init__(self):
        self._nlp = None

    def _get_model(self):
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spacy model 'en_core_web_sm' not found. Install with: python -m spacy download en_core_web_sm")
                raise NLPServiceError("spacy model missing")
        return self._nlp

    def normalize_text(self, text: str) -> str:
        if not text:
            return ""
        doc = self._get_model()(text)
        tokens = [token.text for token in doc if not token.is_space and not token.is_stop]
        return " ".join(tokens)

    def extract_entities(self, text: str) -> list[dict]:
        if not text:
            return []
        doc = self._get_model()(text)
        entities = []
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
            })
        return entities

    def identify_measurements(self, text: str) -> list[dict]:
        if not text:
            return []
        doc = self._get_model()(text)
        measurements = []
        for token in doc:
            if token.like_num and token.n_lefts + token.n_rights > 0:
                context = token.doc[max(0, token.i - 3): token.i + 3].text
                measurements.append({"value": token.text, "context": context})
        return measurements
