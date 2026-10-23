import re
import logging

logger = logging.getLogger("healthcare_system")


class TextNormalizationError(Exception):
    pass


class TextNormalizationService:
    def normalize(self, text: str) -> str:
        if not text:
            return ""

        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        lines = text.split("\n")
        lines = [line.strip() for line in lines]
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
