"""Deterministic lab-value parser (Phase 1).

Pure rule-based extraction + flagging. NO LLM calls. Given report text (and
optionally the patient's gender/age), returns a list of lab results::

    {name, canonical_name, value, unit, ref_low, ref_high, flag,
     range_source, source_text, start, end}

Rules:
- The report's own printed reference range ALWAYS wins (``range_source``
  ``"report"``). When the unit is known, both the value and the printed
  bounds are converted to the test's standard unit.
- Otherwise the reference table is used with the patient's gender when a
  sex-specific range exists (``range_source`` ``"table"``).
- Reported values are converted to the test's standard unit before table
  comparison. If the unit is missing, unknown, or not valid for that test,
  the result is still returned but with ``flag`` ``"unknown"`` (never guess).
- ``original_value`` / ``original_unit`` retain the printed measurement so an
  original result can always be audited after conversion or patient edits.
- A test is only stored when its numeric result actually appears in the text.

Layouts supported:
1. A test name and its value on one line (classic text/PDF reports).
2. Stacked/columnar OCR output where the test name, result, reference range
   and unit are on separate consecutive lines. This is common when a table
   is OCR'd column-by-column.
3. Pipe-separated rows (``Hemoglobin | 15.2 | g/dL | 13.5 - 17.5``); pipes
   are treated as line separators for parsing.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from app.reports.services.reference_ranges import (
    REFERENCE_RANGES,
    SYNONYM_TO_CANONICAL,
    UNIT_ALIASES,
    TEST_UNIT_FAMILIES,
    MMOL_PER_TEST_FACTOR,
    HBA1C_IFFC_ALIASES,
    convert_hba1c_ifcc_to_percent,
)

# A numeric token: 11.2 / 11,200 / 0.9 (commas allowed as thousand separators).
_NUM = r"(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
_VALUE_RE = r"(?P<value>" + _NUM + r")"
_NUMBER_TOKEN_RE = re.compile(_NUM)
# Printed range: (13.0 - 17.0), 13.0-17.0, 13.0 to 17.0, 13- 17,
# plus one-sided <200 / <=200 / >5 / >=5. Parentheses are optional because
# OCR often drops them.
_RANGE_RE = re.compile(
    r"\(\s*(?P<low_paren>" + _NUM + r")"
    r"\s*(?:[-–—]|to)\s*"
    r"(?P<high_paren>" + _NUM + r")\s*[^)]*\)"
    r"|"
    r"(?P<lt_sym><=|<)\s*(?P<lt_val>" + _NUM + r")"
    r"|"
    r"(?P<gt_sym>>=|>)\s*(?P<gt_val>" + _NUM + r")"
    r"|"
    r"(?P<low_bare>" + _NUM + r")"
    r"\s*(?:[-–—]|to)\s*"
    r"(?P<high_bare>" + _NUM + r")",
    re.IGNORECASE,
)
# separator between test name and value: colon, dash, or whitespace.
_SEP_RE = r"\s*[:\-–—]?\s*"

# Build one alternation of ALL synonyms, longest first so that e.g.
# "hdl cholesterol" wins over "cholesterol" on the same line.
_SORTED_SYNONYMS = sorted(SYNONYM_TO_CANONICAL.keys(), key=len, reverse=True)
_NAME_RE = re.compile(
    r"(?P<name>" + r"|".join(re.escape(s) for s in _SORTED_SYNONYMS) + r")",
    re.IGNORECASE,
)

# Sorted unit aliases for longest-prefix matching (normalised form).
_SORTED_UNIT_ALIASES = sorted(UNIT_ALIASES.keys(), key=len, reverse=True)

# Raw-count divisor per test for "count_raw" family (plain cell counts).
_COUNT_RAW_DIVISOR = {
    "wbc": 1_000.0,
    "platelets": 1_000.0,
    "rbc": 1_000_000.0,
    "absolute_neutrophils": 1_000.0,
    "absolute_lymphocytes": 1_000.0,
    "absolute_eosinophils": 1_000.0,
    "absolute_monocytes": 1_000.0,
    "absolute_basophils": 1_000.0,
}

# Heuristic: a "count_raw" value below this is already in standard units
# (e.g. "WBC 7.5 /uL" written loosely); at/above it we treat it as a raw
# count and divide. Absolute counts have much smaller standard values, so
# they use a lower threshold (50 /cumm is a raw count, 0.05 is standard).
_COUNT_RAW_THRESHOLD = 100.0
_COUNT_RAW_THRESHOLD_BY_TEST = {
    "absolute_neutrophils": 10.0,
    "absolute_lymphocytes": 10.0,
    "absolute_eosinophils": 10.0,
    "absolute_monocytes": 10.0,
    "absolute_basophils": 10.0,
}

# OCR often loses the slash or capitalisation in common units.
_UNIT_DISPLAY = {
    "icumm": "/cumm",
    "icmm": "/cmm",
    "cumm": "/cumm",
    "cmm": "/cmm",
    "gldl": "g/dL",
    "gmie": "Gm%",
    "gmle": "Gm%",
    "fl": "fL",
    "pg": "pg",
    "lacsicmm": "LACS/CMM",
    "lathscumm": "lakhs/cumm",
    "millcmm": "million/cmm",
    "milcmm": "million/cmm",
}

# OCR sometimes splits a row label onto two lines: "Absolute" /
# "Lymphocytes". Rejoin those as absolute counts, not percentages.
_ABSOLUTE_PERCENT_MAP = {
    "neutrophil_percent": "absolute_neutrophils",
    "lymphocyte_percent": "absolute_lymphocytes",
    "eosinophil_percent": "absolute_eosinophils",
    "monocyte_percent": "absolute_monocytes",
    "basophil_percent": "absolute_basophils",
}

# Characters OCR commonly confuses inside numbers. Only tokens that already
# contain at least one digit are repaired, so words are never rewritten.
_NUMERIC_OCR_MAP = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1"})


def _fix_numeric_tokens(line: str) -> str:
    def _repair(match: re.Match) -> str:
        token = match.group(0)
        if not any(ch.isdigit() for ch in token):
            return token
        repaired = token.translate(_NUMERIC_OCR_MAP)
        if re.fullmatch(r"\d+,\d{1,2}", repaired):
            repaired = repaired.replace(",", ".")
        return repaired

    return re.sub(
        r"(?<![\w])(?=[0-9OoIl|.,]*[0-9])([0-9OoIl|.,]+)(?![\w])",
        _repair,
        line,
    )


def _normalize_ocr_parts(raw_line: str) -> list[str]:
    """Turn one stored line into clean parseable parts.

    Handles literal ``\\n`` / ``|n`` noise, pipe-separated table rows, tabs and
    numeric OCR confusions. The original line is kept separately by callers
    for ``source_text`` so this never rewrites the stored report text.
    """
    line = raw_line.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")
    # "|n" is a very common OCR rendering of a newline.
    line = re.sub(r"\|\s*n", "\n", line, flags=re.IGNORECASE)
    line = line.replace("|", "\n")

    parts: list[str] = []
    for part in line.split("\n"):
        fixed = _fix_numeric_tokens(part)
        collapsed = re.sub(r"[ \t\u00a0]+", " ", fixed).strip()
        if collapsed:
            parts.append(collapsed)
    return parts


def _line_entries(text: str) -> list[dict]:
    """Split text into parseable line entries with original source spans."""
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    entries: list[dict] = []
    position = 0
    for raw_line in normalised.split("\n"):
        raw_start = position
        position += len(raw_line) + 1
        stripped = raw_line.strip()
        if not stripped:
            continue
        content_start = raw_start + (len(raw_line) - len(raw_line.lstrip()))
        end = raw_start + len(raw_line)
        for part in _normalize_ocr_parts(raw_line):
            entries.append(
                {
                    "text": part,
                    "source": stripped,
                    "start": content_start,
                    "end": end,
                }
            )
    return entries


def _range_values(match: re.Match) -> Optional[tuple[Optional[float], Optional[float]]]:
    if match.group("lt_val") is not None:
        return (None, _to_float(match.group("lt_val")))
    if match.group("gt_val") is not None:
        return (_to_float(match.group("gt_val")), None)
    low = match.group("low_paren") or match.group("low_bare")
    high = match.group("high_paren") or match.group("high_bare")
    if low is None or high is None:
        return None
    low_value = _to_float(low)
    high_value = _to_float(high)
    if low_value is None or high_value is None:
        return None
    return (low_value, high_value)


def _to_float(raw: str) -> Optional[float]:
    try:
        return float(raw.replace(",", ""))
    except (TypeError, ValueError):
        return None


def normalize_unit(raw: str) -> str:
    """Lowercase, remove spaces/dots/brackets, unify micro signs."""
    u = raw.strip().lower().replace(" ", "").replace(".", "")
    u = u.replace("µ", "u").replace("μ", "u").replace("³", "3")
    return u.strip("():,;")


def _display_unit(raw: str) -> str:
    norm = normalize_unit(raw)
    return _UNIT_DISPLAY.get(norm, raw.strip())


def _unit_alias(raw_unit: str) -> Optional[tuple[str, float]]:
    """Return the global (family, factor) for a unit spelling, if known."""
    norm = normalize_unit(raw_unit)
    if not norm:
        return None
    hit = UNIT_ALIASES.get(norm)
    if hit is None:
        # Tolerate a trailing '.' or plural 's' OCR artefact.
        hit = UNIT_ALIASES.get(norm.rstrip(".")) or UNIT_ALIASES.get(norm.rstrip("s"))
    return hit


def lookup_unit(canonical: str, raw_unit: str) -> Optional[tuple[str, float]]:
    """Resolve ``raw_unit`` for ``canonical`` -> (family, factor) or None.

    Returns None when the unit is unknown or not valid for this test.
    """
    norm = normalize_unit(raw_unit)
    if not norm:
        return None
    # HbA1c IFCC special case (affine conversion handled by caller).
    if canonical == "hba1c" and norm in HBA1C_IFFC_ALIASES:
        return ("hba1c_ifcc", 0.0)
    hit = _unit_alias(raw_unit)
    if hit is None:
        return None
    family, factor = hit
    if canonical == "mchc" and family == "percent":
        return ("hb", 1.0)
    if family not in TEST_UNIT_FAMILIES.get(canonical, set()):
        return None
    if family == "mmol":
        factor = MMOL_PER_TEST_FACTOR.get(canonical)
        if factor is None:
            return None
    return (family, factor)


def _fits_printed_scale(
    value: float, printed: Optional[tuple[Optional[float], Optional[float]]]
) -> bool:
    """True when a value is on the same scale as its printed reference range.

    This is deliberately an order-of-magnitude check, not a clinical flag: an
    MCHC of 24.4 belongs with a 32-36 g/dL range even though it is low, while
    a haemoglobin of 140 does not belong with a 13-18 g/dL range.
    """
    if printed is None:
        return False
    low, high = printed
    if low is None and high is None:
        return False
    if (low or 0) == 0 and (high or 0) == 0:
        return value == 0
    if low is not None and low > 0 and value < low * 0.2:
        return False
    if high is not None and high > 0 and value > high * 5:
        return False
    return True


def _fits_table_scale(
    canonical: str, low: Optional[float], high: Optional[float]
) -> bool:
    """True when converted printed bounds look like the test's normal scale."""
    if low is None and high is None:
        return False
    table_low, table_high, _ = _table_range(canonical, None)
    if low is not None and low > 0 and low < table_low * 0.2:
        return False
    if low is not None and table_low > 0 and low > table_low * 5:
        return False
    if high is not None and high > 0 and high < table_high * 0.2:
        return False
    if high is not None and table_high > 0 and high > table_high * 5:
        return False
    return True


def _convert_to_standard(canonical: str, value: float, family: str, factor: float) -> float:
    if family == "count_raw":
        divisor = _COUNT_RAW_DIVISOR.get(canonical, 1.0)
        threshold = _COUNT_RAW_THRESHOLD_BY_TEST.get(canonical, _COUNT_RAW_THRESHOLD)
        if value >= threshold:
            return value / divisor
        return value
    return value * factor


def _standard_measurement(
    canonical: str, value: float, family: str, factor: float
) -> tuple[float, str]:
    """Convert one source measurement to the canonical standard unit."""
    if family == "hba1c_ifcc":
        return (round(convert_hba1c_ifcc_to_percent(value), 3), "%")
    return (
        round(_convert_to_standard(canonical, value, family, factor), 3),
        REFERENCE_RANGES[canonical]["standard_unit"],
    )


def convert_measurement_to_standard(
    canonical: str, value: float, raw_unit: str
) -> Optional[tuple[float, str]]:
    """Public unit conversion helper -> ``(value, standard_unit)`` or ``None``.

    Use this for values stored before the trend data model existed, where the
    printed unit/range were kept raw.
    """
    resolved = lookup_unit(canonical, raw_unit)
    if resolved is None:
        return None
    family, factor = resolved
    return _standard_measurement(canonical, value, family, factor)


def _table_range(canonical: str, gender: Optional[str]) -> tuple[float, float, str]:
    ranges = REFERENCE_RANGES[canonical]["ranges"]
    g = (gender or "").strip().lower()
    if g in ("male", "female") and g in ranges:
        low, high = ranges[g]
        return low, high, "table"
    low, high = ranges["adult"]
    return low, high, "table"


def _flag(value: float, low: Optional[float], high: Optional[float]) -> str:
    if low is not None and value < low:
        return "low"
    if high is not None and value > high:
        return "high"
    return "normal"


def _skip_result_flag(text: str) -> str:
    """Drop annotations printed between a test name and its result.

    Handles a short parenthetical abbreviation (``Total Leucocyte Count
    (TLC) 7500``) and the L/H abnormality marker some labs print beside the
    name (``Lymphocyte L 18``).
    """
    text = text or ""
    for _ in range(3):
        before = text
        text = re.sub(r"^\s*\([A-Za-z0-9./ -]{1,15}\)\s*", "", text)
        text = re.sub(r"^\s*\(\s*", "", text)
        text = re.sub(r"^\s*[LH]\b[\s:.\-]*", "", text, flags=re.IGNORECASE)
        if text == before:
            break
    return text


def _extract_unit_text(after_value: str) -> str:
    """Take up to 3 whitespace-separated tokens as the unit candidate."""
    tokens = after_value.strip().split()
    if not tokens:
        return ""
    if all(tok.strip(" ,;") == "%" for tok in tokens):
        return "%"
    # Stop at anything that starts a new clause (e.g. "is", "was", "and").
    stop_words = {"is", "was", "are", "and", "with", "of", "at"}
    picked: list[str] = []
    for tok in tokens[:3]:
        if tok.lower().strip(",.;") in stop_words:
            break
        # A bare number here means the "unit" capture ran into another value.
        if re.fullmatch(r"\d+(?:\.\d+)?", tok.strip(",.;")):
            break
        picked.append(tok)
        # Units rarely exceed 2 tokens; a token ending in ',' or containing
        # '/' usually terminates the unit ("mg/dL," / "x10^3/uL").
        if "/" in tok or tok.endswith(","):
            break
    unit = " ".join(picked).strip(" ,;")
    return unit


def _standard_family(canonical: str) -> tuple[str, float]:
    """Best default family/factor for a test when the unit is not printed."""
    standard_unit = REFERENCE_RANGES[canonical]["standard_unit"]
    hit = _unit_alias(standard_unit)
    if hit is not None:
        return hit
    family = next(iter(TEST_UNIT_FAMILIES.get(canonical, {"percent"})), "percent")
    return (family, 1.0)


def _families_for(canonical: str) -> list[tuple[str, float]]:
    """All plausible units for a test, standard family first, deduplicated."""
    families: list[tuple[str, float]] = [_standard_family(canonical)]
    for family in TEST_UNIT_FAMILIES.get(canonical, set()):
        if family == families[0][0]:
            continue
        factor = 1.0
        if family == "count_lakh":
            factor = 100.0
        elif family == "mmol":
            factor = MMOL_PER_TEST_FACTOR.get(canonical, 1.0)
        elif family == "hb_gl":
            factor = 0.1
        families.append((family, factor))
    return families


def _convert_bounds(
    canonical: str,
    printed: tuple[Optional[float], Optional[float]],
    family: str,
    factor: float,
) -> tuple[Optional[float], Optional[float]]:
    low, high = printed
    std_low = (
        _standard_measurement(canonical, low, family, factor)[0]
        if low is not None
        else None
    )
    std_high = (
        _standard_measurement(canonical, high, family, factor)[0]
        if high is not None
        else None
    )
    return (std_low, std_high)


def _build_result(
    canonical: str,
    value: float,
    unit_raw: str,
    printed: Optional[tuple[Optional[float], Optional[float]]],
    start: int,
    end: int,
    source_text: str,
    gender: Optional[str],
    original_name: Optional[str] = None,
) -> dict:
    """Apply the printed-range-first / table-conversion rules to one value."""
    display_name = REFERENCE_RANGES[canonical]["display_name"]
    unit = _display_unit(unit_raw) if unit_raw else ""
    base = {
        "name": display_name,
        "original_name": (original_name or display_name).strip(),
        "canonical_name": canonical,
        "original_value": value,
        "original_unit": unit,
        "source_text": source_text,
        "start": start,
        "end": end,
        "unit_status": "missing" if not unit_raw else "unsupported",
        "unit_note": "",
    }
    resolved = lookup_unit(canonical, unit_raw) if unit_raw else None

    if printed is not None:
        ref_low, ref_high = printed
        candidates: list[tuple[str, float, str]] = []
        if resolved is not None:
            candidates.append((resolved[0], resolved[1], "known"))
        for family, factor in _families_for(canonical):
            if resolved is not None and family == resolved[0]:
                continue
            candidates.append((family, factor, "inconsistent" if unit_raw else "assumed"))

        chosen: Optional[tuple[str, float, str, float, float, Optional[float], Optional[float]]] = None
        for family, factor, status in candidates:
            std_value, std_unit = _standard_measurement(canonical, value, family, factor)
            std_low, std_high = _convert_bounds(canonical, printed, family, factor)
            scale_ok = status == "known" or _fits_table_scale(
                canonical, std_low, std_high
            )
            if _fits_printed_scale(std_value, (std_low, std_high)) and scale_ok:
                chosen = (family, factor, status, std_value, std_unit, std_low, std_high)
                break

        if chosen is not None:
            family, factor, status, std_value, std_unit, std_low, std_high = chosen
            note = ""
            if status == "assumed":
                note = "Unit not printed; standard unit assumed from the printed reference range."
            elif status == "inconsistent":
                note = (
                    f"Unit '{unit}' is inconsistent with the printed reference range; "
                    f"value shown as {std_unit}."
                )
            return {
                **base,
                "value": std_value,
                "unit": std_unit,
                "ref_low": std_low,
                "ref_high": std_high,
                "flag": _flag(std_value, std_low, std_high),
                "range_source": "report",
                "unit_status": status,
                "unit_note": note,
            }

        return {
            **base,
            "value": value,
            "unit": unit,
            "ref_low": ref_low,
            "ref_high": ref_high,
            "flag": "unknown",
            "range_source": "report",
            "unit_note": (
                "No unit could be matched to the printed reference range."
                if not unit_raw
                else f"Unit '{unit}' cannot be matched to the printed reference range."
            ),
        }

    table_low, table_high, source = _table_range(canonical, gender)
    if not unit_raw:
        # Missing unit and no printed range: show table range but do
        # not flag (unit cannot be verified).
        return {
            **base,
            "value": value,
            "unit": "",
            "ref_low": table_low,
            "ref_high": table_high,
            "flag": "unknown",
            "range_source": source,
        }

    if resolved is None:
        return {
            **base,
            "value": value,
            "unit": unit,
            "ref_low": table_low,
            "ref_high": table_high,
            "flag": "unknown",
            "range_source": source,
        }

    family, factor = resolved
    std_value, std_unit = _standard_measurement(canonical, value, family, factor)
    return {
        **base,
        "value": std_value,
        "unit": std_unit,
        "ref_low": table_low,
        "ref_high": table_high,
        "flag": _flag(std_value, table_low, table_high),
        "range_source": source,
    }


def _lookahead_annotations(
    entries: list[dict],
    index: int,
    canonical: str,
    printed: Optional[tuple[Optional[float], Optional[float]]],
    unit_raw: str,
) -> tuple[Optional[tuple[Optional[float], Optional[float]]], str]:
    """Pick up a unit/range printed on following lines of the same row.

    Some OCR engines keep the label and result together but put the unit and
    reference range underneath (e.g. ``TOTALLEUCOCYTE COUNT (TLC) 7500`` then
    ``/cmm`` then ``4000-10,000``).
    """
    for next_index in range(index + 1, min(index + 6, len(entries))):
        nxt = entries[next_index]["text"]
        if not nxt:
            continue
        if _next_known_name(nxt):
            break
        if printed is None:
            range_match = _RANGE_RE.search(nxt)
            if range_match:
                printed = _range_values(range_match)
                if unit_raw and printed is not None:
                    return (printed, unit_raw)
                continue
        if not unit_raw and lookup_unit(canonical, nxt) is not None:
            unit_raw = nxt
            if printed is not None:
                return (printed, unit_raw)
    return (printed, unit_raw)


def _parse_inline_lines(entries: list[dict], gender: Optional[str]) -> list[dict]:
    """Classic layout: test name and result on the same line."""
    results: list[dict] = []
    for index, entry in enumerate(entries):
        stripped = entry["text"]
        if not stripped:
            continue

        # Printed ranges on this line (usually one).
        range_match = _RANGE_RE.search(stripped)
        printed = _range_values(range_match) if range_match else None

        # Remove range text so range numbers can't be parsed as values.
        clean = _RANGE_RE.sub(" ", stripped)
        # Hyphenated names ("LDL-Cholesterol") -> spaced so multi-word
        # synonyms match; digit-hyphen cases ("25-OH") are left alone.
        clean = re.sub(r"(?<=[A-Za-z])-(?=[A-Za-z])", " ", clean)

        line_seen: set[str] = set()
        for name_match in _NAME_RE.finditer(clean):
            synonym = name_match.group("name")
            canonical = SYNONYM_TO_CANONICAL[synonym.lower()]
            # Avoid double-counting the same test on one line (e.g. "HbA1c ...
            # glycosylated hemoglobin ..." would match twice).
            if canonical in line_seen:
                continue
            rest = clean[name_match.end():]
            sep = re.match(_SEP_RE, rest)
            rest_after_sep = rest[sep.end():] if sep else rest
            rest_after_sep = _skip_result_flag(rest_after_sep)
            val_match = re.match(_VALUE_RE, rest_after_sep)
            if not val_match:
                continue
            value = _to_float(val_match.group("value"))
            if value is None:
                continue
            after_value = rest_after_sep[val_match.end():]
            unit_raw = _extract_unit_text(after_value)
            row_printed, row_unit = _lookahead_annotations(
                entries, index, canonical, printed, unit_raw
            )

            line_seen.add(canonical)
            results.append(
                _build_result(
                    canonical,
                    value,
                    row_unit,
                    row_printed,
                    entry["start"],
                    entry["end"],
                    entry["source"],
                    gender,
                    original_name=synonym,
                )
            )

    return results


def _next_known_name(line: str) -> bool:
    """True when a line starts with a known test name (stacked-table boundary)."""
    return _NAME_RE.match(line.strip()) is not None


def _source_span(entries: list[dict], first: int, last: int) -> str:
    sources: list[str] = []
    for entry in entries[first:last + 1]:
        if not sources or sources[-1] != entry["source"]:
            sources.append(entry["source"])
    return "\n".join(sources)


def _parse_stacked_blocks(
    entries: list[dict], gender: Optional[str], seen: set[str]
) -> list[dict]:
    """Columnar OCR layout: name, result, range and unit on separate lines."""
    results: list[dict] = []
    consumed: set[int] = set()
    for line_index, entry in enumerate(entries):
        if line_index in consumed:
            continue
        stripped = entry["text"]
        if not stripped:
            continue

        header_index = line_index
        name_match = _NAME_RE.match(stripped)
        if not name_match and stripped.lower() == "absolute":
            # OCR may split "Absolute Lymphocytes" into "Absolute" on one
            # line and "Lymphocytes" on the next. Rejoin them so the result
            # is not mistaken for the differential percentage.
            for lookahead in range(line_index + 1, len(entries)):
                candidate = entries[lookahead]["text"]
                if not candidate:
                    continue
                candidate_match = _NAME_RE.match(candidate)
                if not candidate_match:
                    break
                candidate_canonical = SYNONYM_TO_CANONICAL[
                    candidate_match.group("name").lower()
                ]
                absolute_canonical = _ABSOLUTE_PERCENT_MAP.get(candidate_canonical)
                if not absolute_canonical:
                    break
                header_index = lookahead
                consumed.add(lookahead)
                name_match = candidate_match
                canonical = absolute_canonical
                break
            if not name_match:
                continue
        else:
            if not name_match:
                continue
            canonical = SYNONYM_TO_CANONICAL[name_match.group("name").lower()]

        if canonical in seen:
            continue

        header_entry = entries[header_index]
        rest = header_entry["text"][name_match.end():]
        sep = re.match(_SEP_RE, rest)
        after_name = rest[sep.end():] if sep else rest
        after_name = _skip_result_flag(after_name)
        # Inline layout is handled by _parse_inline_lines, including lines
        # that only contain a reference range after the name.
        if re.match(_VALUE_RE, after_name):
            continue

        numbers: list[float] = []
        printed: Optional[tuple[Optional[float], Optional[float]]] = None
        unit_raw = ""
        last_index = header_index

        for next_index in range(header_index + 1, len(entries)):
            nxt = entries[next_index]["text"]
            if not nxt:
                continue
            if _next_known_name(nxt):
                break

            range_match = _RANGE_RE.search(nxt)
            if range_match:
                values = _range_values(range_match)
                if printed is None and values is not None:
                    printed = values
                last_index = next_index
                continue

            # Check units before numbers because some units contain digits
            # (e.g. "x10^3/uL"). Continue scanning so a range printed AFTER
            # the unit (name / value / unit / range) is still picked up.
            if lookup_unit(canonical, nxt) is not None:
                if not unit_raw:
                    unit_raw = nxt
                last_index = next_index
                continue
            if _unit_alias(nxt) is not None:
                if not unit_raw:
                    unit_raw = nxt
                last_index = next_index
                continue

            if re.search(r"\d\s*[-–—]\s*\d", nxt):
                # Range-like but unparseable (OCR noise such as "14.,0").
                # Never treat those digits as a result value.
                last_index = next_index
                continue

            numeric_tokens = _NUMBER_TOKEN_RE.findall(nxt)
            if numeric_tokens:
                numbers.extend(
                    value
                    for value in (_to_float(tok) for tok in numeric_tokens)
                    if value is not None
                )
                last_index = next_index
                continue

            # Unknown uppercase labels (e.g. PCT, MPV, PDW) end this block.
            if numbers and re.fullmatch(r"[A-Z][A-Z0-9+\-]{1,7}:?", nxt):
                break

        if not numbers:
            continue

        value = numbers[0]
        # OCR sometimes splits "4000 - 10000" into three separate lines:
        # result, low, high. Only infer with exactly three numbers.
        if printed is None and len(numbers) >= 3:
            inferred = (numbers[1], numbers[2])
            if 0 <= inferred[0] < inferred[1]:
                printed = inferred

        start = entries[line_index]["start"]
        end = entries[last_index]["end"]
        source_text = _source_span(entries, line_index, last_index)
        results.append(
            _build_result(
                canonical,
                value,
                unit_raw,
                printed,
                start,
                end,
                source_text,
                gender,
                original_name=name_match.group("name"),
            )
        )
        seen.add(canonical)

    return results


# ---- Collection / report date ------------------------------------------------

_DATE_RE = re.compile(
    r"\b(?P<dmy1>\d{1,2})[/.-](?P<dmy2>\d{1,2})[/.-](?P<dmy3>\d{2,4})\b"
    r"|"
    r"\b(?P<iso_year>\d{4})-(?P<iso_month>\d{1,2})-(?P<iso_day>\d{1,2})\b"
)

_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
_MONTH_DATE_RE = re.compile(
    r"\b(?P<day>\d{1,2})[\s./-]+(?P<month>[A-Za-z]{3,9})[\s,./-]+(?P<year>\d{2,4})\b"
    r"|"
    r"\b(?P<month2>[A-Za-z]{3,9})[\s./-]+(?P<day2>\d{1,2})[\s,./-]+(?P<year2>\d{2,4})\b",
    re.IGNORECASE,
)


def _coerce_date(first: int, second: int, year: int) -> Optional[str]:
    if year < 100:
        year += 2000 if year < 70 else 1900
    candidates: list[tuple[int, int]] = []
    if first > 12:
        candidates.append((second, first))  # day-first (dd/mm/yyyy)
    elif second > 12:
        candidates.append((first, second))  # month-first (mm/dd/yyyy)
    else:
        candidates.append((second, first))  # default: day-first
        candidates.append((first, second))
    for month, day in candidates:
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            continue
    return None


def _date_in_text(text: str) -> Optional[str]:
    match = _DATE_RE.search(text or "")
    if match:
        if match.group("iso_year"):
            return _coerce_date(
                int(match.group("iso_day")),
                int(match.group("iso_month")),
                int(match.group("iso_year")),
            )
        return _coerce_date(
            int(match.group("dmy1")),
            int(match.group("dmy2")),
            int(match.group("dmy3")),
        )

    month_match = _MONTH_DATE_RE.search(text or "")
    if not month_match:
        return None
    if month_match.group("day"):
        day = int(month_match.group("day"))
        month_name = month_match.group("month")
        year = int(month_match.group("year"))
    else:
        day = int(month_match.group("day2"))
        month_name = month_match.group("month2")
        year = int(month_match.group("year2"))
    month = _MONTHS.get(month_name.lower())
    if not month:
        return None
    if year < 100:
        year += 2000 if year < 70 else 1900
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _date_label_source(line: str) -> Optional[str]:
    lower = (line or "").lower()
    if any(
        token in lower
        for token in ("collection", "collected", "sample", "specimen")
    ):
        return "collected"
    if any(
        token in lower
        for token in ("report", "reported", "registered", "registration")
    ):
        return "reported"
    if re.search(r"\bdate\b", lower) and not re.search(
        r"\b(dob|birth|age)\b", lower
    ):
        return "reported"
    return None


def extract_report_date(text: str) -> tuple[Optional[str], Optional[str]]:
    """Return ``(YYYY-MM-DD, source)`` where source is collected/reported.

    Collection/sample/specimen dates are preferred over report/registration
    dates regardless of where they appear. A date with no recognisable label is
    treated as a report date. The caller falls back to the upload date when
    this returns ``(None, None)``.
    """
    if not text or not text.strip():
        return (None, None)
    lines = [
        line.strip()
        for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ]

    for wanted in ("collected", "reported"):
        for index, line in enumerate(lines):
            if _date_label_source(line) != wanted:
                continue
            # Handle "Collection Date : 24/06/2023", "Collected on", "DATE-".
            found = _date_in_text(line)
            if found:
                return (found, wanted)
            # ...or on the next non-empty line ("Collection Date" then date).
            for lookahead in range(index + 1, min(index + 4, len(lines))):
                if not lines[lookahead]:
                    continue
                found = _date_in_text(lines[lookahead])
                if found:
                    return (found, wanted)
                break

    # Unknown label but a date is present: prefer it over the upload date.
    for line in lines:
        found = _date_in_text(line)
        if found:
            return (found, "reported")
    return (None, None)


def extract_collection_date(text: str) -> Optional[str]:
    """Backward-compatible date helper: ISO date if any report date is printed.

    Prefer :func:`extract_report_date` when the date source matters. The caller
    falls back to the upload date when this returns ``None``.
    """
    return extract_report_date(text)[0]


def parse_lab_results(
    text: str,
    gender: Optional[str] = None,
    age_years: Optional[float] = None,
) -> list[dict]:
    """Parse lab values from report text. Deterministic; no LLM calls.

    ``age_years`` is accepted for forward compatibility (reference table is
    adult-only; documented in reference_ranges.py) and currently unused.
    """
    _ = age_years  # reserved for future paediatric tables
    if not text or not text.strip():
        return []

    entries = _line_entries(text)
    results = _parse_inline_lines(entries, gender)
    seen = {r["canonical_name"] for r in results}
    results.extend(_parse_stacked_blocks(entries, gender, seen))

    # Deterministic order: by position in text.
    results.sort(key=lambda r: (r["start"], r["canonical_name"]))
    return results


def canonicalize_test_name(name: str) -> Optional[str]:
    """Map a user-supplied test name/synonym to its canonical key."""
    key = (name or "").strip().lower()
    if key in REFERENCE_RANGES:
        return key
    return SYNONYM_TO_CANONICAL.get(key)
