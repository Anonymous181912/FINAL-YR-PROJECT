"""Handwritten prescription scan -> DRAFT items (Phase 2e, lowest priority).

Pipeline: image -> existing OCR (text files read directly) -> deterministic
rule-based line parsing -> LLM fallback ONLY when rules find nothing AND an
LLM is configured (response validated against the item schema). The result is
a DRAFT the doctor must review and edit; nothing is ever saved here.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import UploadFile

logger = logging.getLogger("healthcare_system")

_DOSAGE_RE = r"(?P<dosage>\d+(?:\.\d+)?\s*(?:mg|g|mcg|µg|μg|ml|iu|units?|tablets?|tabs?|capsules?|caps?|drops?|puffs?|%)\b)"
_FREQ_WORDS = [
    "od", "bd", "tds", "qds", "qid", "tid", "qd", "hs", "sos", "stat",
    "daily", "twice", "thrice", "morning", "night", "evening",
    "once", "weekly", "monthly", "before food", "after food",
    "1-0-0", "1-0-1", "1-1-1", "0-1-0", "0-0-1", "1--0--0",
]
_DURATION_RE = r"(?:for\s+)?(?P<duration>\d+\s*(?:days?|weeks?|months?))\b"


def _rule_based_parse(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw_line in text.splitlines():
        line = re.sub(r"^[\s\-\*\d\.\)\]]+", "", raw_line).strip()
        if len(line) < 3:
            continue
        dose = re.search(_DOSAGE_RE, line, re.IGNORECASE)
        if not dose:
            continue
        name = line[: dose.start()].strip(" :-–—")
        name = re.sub(r"^(tab|cap|syp|inj|rx)[\s\.]+", "", name, flags=re.IGNORECASE).strip()
        if len(name) < 2:
            continue
        tail = line[dose.end():]
        freq = ""
        for fw in _FREQ_WORDS:
            if re.search(rf"(?<![a-z]){re.escape(fw)}(?![a-z])", tail, re.IGNORECASE):
                freq = fw.upper() if len(fw) <= 4 else fw.title()
                break
        dur = re.search(_DURATION_RE, tail, re.IGNORECASE)
        items.append({
            "medicine_name": name[:200],
            "dosage": dose.group("dosage")[:100],
            "frequency": freq or "OD",
            "duration": (dur.group("duration") if dur else "7 days")[:100],
            "route": "Oral",
            "instructions": "",
            "needs_review": True,
        })
    # Deduplicate by (name, dosage).
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (item["medicine_name"].lower(), item["dosage"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


async def _llm_fallback(text: str) -> list[dict[str, Any]]:
    """Ask the LLM for structured items; validate strictly, else []."""
    from app.core.config import settings
    from app.models.prescription import PrescriptionItem

    if not settings.omni_route_api_key:
        return []
    prompt = (
        "Extract prescribed medicines from the following prescription text. "
        "Reply with ONLY a JSON array; each element must have keys "
        "medicine_name, dosage, frequency, duration (strings). "
        "If unsure about a field use an empty string. No diagnosis, no advice.\n\n"
        f"TEXT:\n{text[:3000]}"
    )
    try:
        from app.reports.ai.llm import LLMService

        service = LLMService()
        payload = {
            "messages": service._build_messages(
                "You extract medicine lists. Output valid JSON only.", prompt
            ),
            "max_tokens": service.max_tokens,
            "temperature": 0.1,
        }
        data = await service._chat_completion(payload)
        raw = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            return []
        import json as _json

        parsed = _json.loads(match.group(0))
        items = []
        for entry in parsed:
            if not isinstance(entry, dict) or not (entry.get("medicine_name") or "").strip():
                continue
            item = PrescriptionItem(
                medicine_name=str(entry.get("medicine_name", ""))[:200],
                dosage=str(entry.get("dosage") or "")[:100] or "—",
                frequency=str(entry.get("frequency") or "OD")[:100],
                duration=str(entry.get("duration") or "7 days")[:100],
            )
            items.append({**item.model_dump(), "needs_review": True})
        return items
    except Exception as exc:
        logger.warning(f"LLM scan fallback failed (non-fatal): {exc}")
        return []


async def parse_prescription_scan(file: UploadFile) -> dict[str, Any]:
    filename = (file.filename or "").lower()
    if filename.endswith(".txt"):
        content = await file.read()
        text = content.decode("utf-8", errors="replace")
        ocr_used = False
    else:
        import os
        import tempfile

        from app.reports.ai.ocr import OCRService, OCRServiceError

        suffix = os.path.splitext(filename)[1] or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        try:
            try:
                text = await OCRService().extract_text(tmp_path)
            except OCRServiceError as exc:
                raise ValueError(f"OCR failed: {exc}") from exc
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        ocr_used = True

    from app.reports.services.normalization import TextNormalizationService

    text = TextNormalizationService().normalize(text or "")
    if not text.strip():
        raise ValueError("No text could be extracted from the scan")

    items = _rule_based_parse(text)
    method = "rule-based"
    if not items:
        items = await _llm_fallback(text)
        method = "llm-fallback" if items else "none"

    return {
        "draft": True,
        "review_required": True,
        "extraction_method": ("ocr+" if ocr_used else "text+") + method,
        "raw_text": text[:4000],
        "items": items,
        "note": "DRAFT only — a doctor must review, edit and save this before it becomes a prescription. AI output is an explanation aid, not a diagnosis.",
    }
