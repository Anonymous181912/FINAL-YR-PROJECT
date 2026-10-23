import logging
import sys
from pythonjsonlogger import json
from app.core.config import settings

logger = logging.getLogger("healthcare_system")
logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = json.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"levelname": "level", "asctime": "timestamp"},
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
