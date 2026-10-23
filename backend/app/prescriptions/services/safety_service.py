"""Prescription safety checks (Phase 2a).

EDUCATIONAL, NOT CLINICAL ADVICE. Curated teaching dataset
(``app/data/drug_interactions.json``). Never exhaustive; never a substitute
for a pharmacist/doctor review. The service only *flags* potential issues and
blocks issuing on severe flags until the doctor explicitly acknowledges them.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

logger = logging.getLogger("healthcare_system")

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "drug_interactions.json")
_DATA: Optional[dict] = None


def _load_data() -> dict:
    global _DATA
    if _DATA is None:
        try:
            with open(_DATA_PATH, encoding="utf-8") as fh:
                _DATA = json.load(fh)
        except Exception as exc:
            logger.error(f"Failed to load drug interaction dataset: {exc}")
            _DATA = {"pairs": [], "allergy_map": {}, "disclaimer": ""}
    return _DATA


def normalize_drug_name(name: str) -> str:
    """Lowercase, drop punctuation/dose artefacts, collapse spaces."""
    n = (name or "").lower()
    n = re.sub(r"[^a-z0-9+ ]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _whole_word_contains(haystack: str, needle: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack) is not None


class SafetyService:
    """Stateless checker: interactions, allergy clashes, duplicate therapy."""

    def check(
        self,
        items: list[Any],
        allergies: Optional[list[str]] = None,
    ) -> list[dict]:
        data = _load_data()
        warnings: list[dict] = []
        names = [normalize_drug_name(getattr(i, "medicine_name", None) or (i.get("medicine_name") if isinstance(i, dict) else "")) for i in items]
        names = [n for n in names if n]

        # 1. Pairwise interactions (whole-word match so "amoxicillin
        #    clavulanate" still triggers the amoxicillin pair entries).
        for idx_a in range(len(names)):
            for idx_b in range(idx_a + 1, len(names)):
                for pair in data.get("pairs", []):
                    a = normalize_drug_name(pair["drug_a"])
                    b = normalize_drug_name(pair["drug_b"])
                    hit_ab = _whole_word_contains(names[idx_a], a) and _whole_word_contains(names[idx_b], b)
                    hit_ba = _whole_word_contains(names[idx_a], b) and _whole_word_contains(names[idx_b], a)
                    if hit_ab or hit_ba:
                        warnings.append({
                            "type": "interaction",
                            "severity": pair.get("severity", "moderate"),
                            "drugs": [names[idx_a], names[idx_b]],
                            "note": pair.get("note", ""),
                        })

        # 2. Allergy clashes via the class map (penicillin allergy vs
        #    amoxicillin etc.). Allergy flags are always severe.
        allergy_map: dict = data.get("allergy_map", {})
        for allergy in allergies or []:
            norm_allergy = normalize_drug_name(allergy)
            if not norm_allergy:
                continue
            for item_name in names:
                matched_class = None
                # direct mention: allergy text inside item or vice versa
                if norm_allergy in item_name or item_name in norm_allergy:
                    matched_class = "direct match"
                else:
                    for cls, members in allergy_map.items():
                        cls_hit = norm_allergy == cls or norm_allergy in cls or cls in norm_allergy
                        if cls_hit and any(_whole_word_contains(item_name, normalize_drug_name(m)) for m in members):
                            matched_class = cls
                            break
                if matched_class:
                    warnings.append({
                        "type": "allergy",
                        "severity": "severe",
                        "drugs": [item_name],
                        "note": f"Patient allergy '{allergy}' may clash with '{item_name}' ({matched_class}). Verify before issuing.",
                    })

        # 3. Duplicate therapy: same agent prescribed twice.
        seen: dict[str, int] = {}
        for item_name in names:
            seen[item_name] = seen.get(item_name, 0) + 1
        for item_name, count in seen.items():
            if count > 1:
                warnings.append({
                    "type": "duplicate",
                    "severity": "moderate",
                    "drugs": [item_name],
                    "note": f"'{item_name}' appears {count} times. Check for duplicate therapy.",
                })

        # Deduplicate identical warnings, deterministic order.
        unique: list[dict] = []
        seen_keys: set[str] = set()
        for w in warnings:
            key = (w["type"], w["severity"], ",".join(sorted(w["drugs"])), w["note"])
            if key not in seen_keys:
                seen_keys.add(key)
                unique.append(w)
        severity_rank = {"severe": 0, "moderate": 1, "minor": 2}
        unique.sort(key=lambda w: (severity_rank.get(w["severity"], 3), w["type"], ",".join(w["drugs"])))
        return unique

    @staticmethod
    def blocks_issuing(warnings: list[dict]) -> bool:
        return any(w.get("severity") == "severe" for w in warnings)
