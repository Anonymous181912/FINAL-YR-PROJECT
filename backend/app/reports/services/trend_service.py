"""Deterministic longitudinal lab trend analysis.

This module contains no LLM calls. It normalises stored lab values, builds one
series per canonical test, computes direction/events, and renders a template
explanation from the computed facts only.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timezone
from typing import Any, Optional

from app.core.config import settings
from app.reports.services.lab_parser import (
    convert_measurement_to_standard,
    extract_report_date,
    normalize_unit,
)
from app.reports.services.reference_ranges import REFERENCE_RANGES

DISCLAIMER = "This is not a diagnosis. Please discuss these results with your doctor."

# Keep the clinically useful tests first; any other reference-table test with
# real data is still discovered dynamically.
_PREFERRED_ORDER = [
    "fasting_glucose",
    "post_prandial_glucose",
    "random_glucose",
    "hba1c",
    "total_cholesterol",
    "ldl",
    "hdl",
    "triglycerides",
    "hemoglobin",
    "rbc",
    "wbc",
    "platelets",
    "hematocrit",
    "mcv",
    "mch",
    "mchc",
    "rdw_cv",
    "rdw_sd",
    "creatinine",
    "urea_bun",
    "alt",
    "ast",
    "tsh",
    "sodium",
    "potassium",
    "vitamin_d",
    "esr",
]
SUPPORTED_CANONICAL_TESTS = _PREFERRED_ORDER + [
    key for key in REFERENCE_RANGES if key not in _PREFERRED_ORDER
]


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _as_date_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return date.fromisoformat(text[:10]).isoformat()
        except ValueError:
            return None
    return None


def _format_number(value: Optional[float]) -> str:
    if value is None:
        return "—"
    number = float(value)
    if abs(number - round(number)) < 1e-9:
        return f"{int(round(number)):,}"
    return f"{number:,.3f}".rstrip("0").rstrip(".")


def _format_date(value: Optional[str]) -> str:
    if not value:
        return "unknown date"
    try:
        parsed = date.fromisoformat(value[:10])
    except ValueError:
        return value
    return f"{parsed.day} {parsed.strftime('%b %Y')}"


def _format_percent(value: Optional[float], signed: bool = False) -> str:
    if value is None:
        return "—"
    prefix = "+" if signed and value > 0 else ""
    return f"{prefix}{value:.1f}%"


def _point_status(point: dict) -> str:
    value = point.get("value")
    low = point.get("ref_low")
    high = point.get("ref_high")
    if value is None:
        return "unknown"
    if low is None and high is None:
        return "unknown"
    if low is not None and value < low:
        return "below"
    if high is not None and value > high:
        return "above"
    return "within"


def _flag_from_range(value: Optional[float], low: Optional[float], high: Optional[float]) -> str:
    if value is None or (low is None and high is None):
        return "unknown"
    if low is not None and value < low:
        return "low"
    if high is not None and value > high:
        return "high"
    return "normal"


def _normalize_range_source(raw: Any) -> str:
    return "report" if str(raw or "").lower() == "report" else "table"


def _report_date_and_source(report: Any, lab: dict) -> tuple[Optional[str], str]:
    lab_date = _as_date_iso(
        lab.get("collected_on")
        or lab.get("report_date")
        or lab.get("date")
    )
    if lab_date:
        source = str(lab.get("date_source") or "reported").lower()
        if source not in ("collected", "reported", "upload"):
            source = "reported"
        return (lab_date, source)

    text = _get(report, "extracted_text", "") or ""
    parsed_date, parsed_source = extract_report_date(text)
    if parsed_date:
        return (parsed_date, parsed_source or "reported")

    uploaded = _as_date_iso(_get(report, "created_at"))
    if uploaded:
        return (uploaded, "upload")
    return (None, "upload")


def _normalize_lab_point(report: Any, canonical: str, lab: dict) -> tuple[Optional[dict], Optional[dict]]:
    """Return ``(point, not_comparable)`` for one stored lab value."""
    display_name = REFERENCE_RANGES[canonical]["display_name"]
    standard_unit = REFERENCE_RANGES[canonical]["standard_unit"]
    collected_on, date_source = _report_date_and_source(report, lab)
    report_id = _get(report, "id") or lab.get("report_id")

    raw_value = lab.get("value")
    try:
        numeric_value = float(raw_value)
    except (TypeError, ValueError):
        return (
            None,
            {
                "canonical_test": canonical,
                "display_name": display_name,
                "report_id": report_id,
                "collected_on": collected_on,
                "date_source": date_source,
                "value": raw_value,
                "unit": lab.get("unit") or "",
                "reason": "Value is not numeric",
            },
        )

    raw_unit = str(lab.get("unit") or "").strip()
    low = _safe_float(lab.get("ref_low"))
    high = _safe_float(lab.get("ref_high"))

    # Newer parser output is already in the standard unit. Older records kept
    # the printed unit and range raw, so convert value and bounds together.
    if raw_unit and normalize_unit(raw_unit) == normalize_unit(standard_unit):
        std_value = numeric_value
        std_low = low
        std_high = high
        unit = standard_unit
    else:
        converted = convert_measurement_to_standard(canonical, numeric_value, raw_unit)
        if converted is None:
            reason = (
                "Unit is missing, so the value cannot be compared"
                if not raw_unit
                else f"Unit '{raw_unit}' cannot be converted to {standard_unit}"
            )
            return (
                None,
                {
                    "canonical_test": canonical,
                    "display_name": display_name,
                    "report_id": report_id,
                    "collected_on": collected_on,
                    "date_source": date_source,
                    "value": numeric_value,
                    "unit": raw_unit,
                    "reason": reason,
                },
            )
        std_value, unit = converted
        std_low = _convert_bound(canonical, low, raw_unit)
        std_high = _convert_bound(canonical, high, raw_unit)

    range_source = _normalize_range_source(lab.get("range_source"))
    flag = _flag_from_range(std_value, std_low, std_high)
    if flag == "unknown":
        stored_flag = str(lab.get("flag") or "").lower()
        if stored_flag in ("low", "high", "normal"):
            flag = stored_flag

    point = {
        "canonical_test": canonical,
        "display_name": display_name,
        "report_id": report_id,
        "value": round(std_value, 6),
        "unit": unit,
        "ref_low": std_low,
        "ref_high": std_high,
        "range_source": range_source,
        "flag": flag,
        "collected_on": collected_on,
        "date_source": date_source,
        "original_value": _safe_float(lab.get("original_value")),
        "original_unit": lab.get("original_unit") or raw_unit,
        "excluded_by_patient": bool(lab.get("excluded_by_patient", False)),
        "edited_by_patient": bool(lab.get("edited_by_patient", False)),
    }
    if point["original_value"] is None:
        point["original_value"] = numeric_value
    return (point, None)


def _safe_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _convert_bound(canonical: str, value: Optional[float], unit: str) -> Optional[float]:
    if value is None:
        return None
    converted = convert_measurement_to_standard(canonical, value, unit)
    return converted[0] if converted else None


def _dedupe_points(points: list[dict]) -> tuple[list[dict], list[str]]:
    groups: dict[tuple[Any, float], list[dict]] = {}
    order: list[tuple[Any, float]] = []
    for point in points:
        key = (point.get("collected_on"), round(float(point.get("value") or 0), 6))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(point)

    kept: list[dict] = []
    notes: list[str] = []
    for key in order:
        group = groups[key]
        chosen = dict(group[0])
        chosen["duplicate_count"] = len(group)
        chosen["duplicate_report_ids"] = [p.get("report_id") for p in group[1:]]
        kept.append(chosen)
        if len(group) > 1:
            display = chosen.get("display_name") or chosen.get("canonical_test")
            notes.append(
                f"{display} has {len(group)} identical values on "
                f"{_format_date(chosen.get('collected_on'))}; shown once."
            )
    return (kept, notes)


def _range_text(point: dict) -> str:
    low = point.get("ref_low")
    high = point.get("ref_high")
    unit = point.get("unit") or ""
    if low is not None and high is not None:
        return f"{_format_number(low)}-{_format_number(high)} {unit}".strip()
    if low is not None:
        return f"> {_format_number(low)} {unit}".strip()
    if high is not None:
        return f"< {_format_number(high)} {unit}".strip()
    return ""


def _values_phrase(points: list[dict], unit: str) -> str:
    rendered = [
        f"{_format_number(p.get('value'))} {unit} ({_format_date(p.get('collected_on'))})"
        for p in points
    ]
    if len(rendered) == 2:
        return " and ".join(rendered)
    return ", ".join(rendered[:-1]) + ", and " + rendered[-1]


def _explanation(
    display_name: str,
    unit: str,
    points: list[dict],
    direction: str,
    change_pct: Optional[float],
    change_abs: Optional[float],
    latest: Optional[dict],
) -> str:
    if not points:
        return f"No comparable {display_name} values are available yet. {DISCLAIMER}"

    if len(points) == 1:
        point = points[0]
        return (
            f"Only one comparable {display_name} result is available: "
            f"{_format_number(point.get('value'))} {unit} "
            f"({_format_date(point.get('collected_on'))}). At least two comparable "
            f"reports are needed to describe a trend. {DISCLAIMER}"
        )

    # The summary/event direction uses latest vs previous. The explanation
    # deliberately describes the whole series from first to latest so its
    # percentage always matches the values it lists (e.g. 95 -> 128 = 34.7%).
    first_value = float(points[0]["value"])
    latest_value = float(points[-1]["value"])
    overall_abs = round(latest_value - first_value, 6)
    overall_pct = (
        round((latest_value - first_value) / abs(first_value) * 100.0, 2)
        if first_value != 0
        else None
    )
    values = _values_phrase(points, unit)
    if overall_pct is None:
        sentence = (
            f"{display_name} changed from {values}, "
            f"an absolute change of {_format_number(overall_abs)} {unit}."
        )
    elif overall_pct > 0:
        sentence = f"{display_name} rose from {values}, an increase of {_format_percent(overall_pct)}."
    elif overall_pct < 0:
        sentence = f"{display_name} fell from {values}, a decrease of {_format_percent(abs(overall_pct))}."
    else:
        sentence = f"{display_name} was unchanged across {values}."

    latest_status = _point_status(latest) if latest else "unknown"
    latest_range = _range_text(latest) if latest else ""
    if latest and latest_status == "above":
        source_phrase = (
            "stated in the report"
            if latest.get("range_source") == "report"
            else "used from the reference table"
        )
        range_sentence = (
            f"The latest value is above the reference range {source_phrase} "
            f"({latest_range})."
        )
    elif latest and latest_status == "below":
        source_phrase = (
            "stated in the report"
            if latest.get("range_source") == "report"
            else "used from the reference table"
        )
        range_sentence = (
            f"The latest value is below the reference range {source_phrase} "
            f"({latest_range})."
        )
    elif latest and latest_status == "within":
        source_phrase = (
            "stated in the report"
            if latest.get("range_source") == "report"
            else "used from the reference table"
        )
        range_sentence = (
            f"The latest value is within the reference range {source_phrase} "
            f"({latest_range})."
        )
    else:
        range_sentence = "No reference range was available for the latest value."

    return f"{sentence} {range_sentence} {DISCLAIMER}"


def build_test_series(
    reports: list[Any],
    canonical: str,
    stable_threshold_pct: Optional[float] = None,
    include_excluded: bool = True,
) -> dict:
    """Build one canonical-test series from reports (any order)."""
    if canonical not in REFERENCE_RANGES:
        raise KeyError(canonical)

    threshold = (
        settings.trend_stable_threshold_pct
        if stable_threshold_pct is None
        else float(stable_threshold_pct)
    )
    display_name = REFERENCE_RANGES[canonical]["display_name"]
    standard_unit = REFERENCE_RANGES[canonical]["standard_unit"]

    comparable: list[dict] = []
    excluded: list[dict] = []
    not_comparable: list[dict] = []

    for report in reports or []:
        for lab in (_get(report, "lab_results", None) or []):
            lab_canonical = (
                lab.get("canonical_test")
                or lab.get("canonical_name")
                or lab.get("test")
            )
            if lab_canonical != canonical:
                continue
            point, problem = _normalize_lab_point(report, canonical, lab)
            if problem is not None:
                if not bool(lab.get("excluded_by_patient", False)):
                    not_comparable.append(problem)
                continue
            if point.get("excluded_by_patient"):
                if include_excluded:
                    excluded.append(point)
                continue
            comparable.append(point)

    comparable.sort(
        key=lambda p: (
            p.get("collected_on") or "",
            str(p.get("report_id") or ""),
        )
    )
    points, duplicate_notes = _dedupe_points(comparable)
    excluded.sort(key=lambda p: (p.get("collected_on") or "", str(p.get("report_id") or "")))

    first = points[0] if points else None
    latest = points[-1] if points else None
    previous = points[-2] if len(points) >= 2 else None
    change_abs = None
    change_pct = None
    if previous is not None and latest is not None:
        change_abs = round(float(latest["value"]) - float(previous["value"]), 6)
        if float(previous["value"]) != 0:
            change_pct = round(
                (float(latest["value"]) - float(previous["value"]))
                / abs(float(previous["value"]))
                * 100.0,
                2,
            )

    if len(points) < 2:
        direction = "insufficient_data"
    elif change_pct is None:
        direction = "stable" if (change_abs or 0) == 0 else ("rising" if change_abs > 0 else "falling")
    elif abs(change_pct) < threshold:
        direction = "stable"
    elif change_pct > 0:
        direction = "rising"
    else:
        direction = "falling"

    events: list[str] = []
    for earlier, later in zip(points, points[1:]):
        earlier_status = _point_status(earlier)
        later_status = _point_status(later)
        if later_status in ("below", "above") and earlier_status == "within":
            event = "newly_out_of_range"
        elif later_status == "within" and earlier_status in ("below", "above"):
            event = "returned_to_range"
        elif later_status in ("below", "above") and earlier_status in ("below", "above"):
            if (
                (earlier_status == "below" and later_status == "above")
                or (earlier_status == "above" and later_status == "below")
            ):
                event = "crossed_range_between_reports"
            else:
                event = "still_out_of_range"
        else:
            event = None
        if event and event not in events:
            events.append(event)

    days_between = None
    if previous and latest and previous.get("collected_on") and latest.get("collected_on"):
        try:
            days_between = (
                date.fromisoformat(latest["collected_on"][:10])
                - date.fromisoformat(previous["collected_on"][:10])
            ).days
        except ValueError:
            days_between = None

    return {
        "canonical_test": canonical,
        "display_name": display_name,
        "unit": standard_unit,
        "points": points,
        "excluded_points": excluded,
        "not_comparable": not_comparable,
        "duplicate_notes": duplicate_notes,
        "point_count": len(points),
        "first": first,
        "previous": previous,
        "latest": latest,
        "change_abs": change_abs,
        "change_pct": change_pct,
        "days_between": days_between,
        "direction": direction,
        "ref_low": latest.get("ref_low") if latest else None,
        "ref_high": latest.get("ref_high") if latest else None,
        "range_source": latest.get("range_source") if latest else None,
        "range_status_latest": _point_status(latest) if latest else "unknown",
        "events": events,
        "explanation": _explanation(
            display_name, standard_unit, points, direction, change_pct, change_abs, latest
        ),
    }


def _summary_entry(series: dict) -> dict:
    latest = series.get("latest") or {}
    previous = series.get("previous") or {}
    first = series.get("first") or {}
    return {
        "canonical_test": series["canonical_test"],
        "display_name": series["display_name"],
        "unit": series["unit"],
        "point_count": series["point_count"],
        "first_value": first.get("value"),
        "first_date": first.get("collected_on"),
        "previous_value": previous.get("value"),
        "previous_date": previous.get("collected_on"),
        "latest_value": latest.get("value"),
        "latest_date": latest.get("collected_on"),
        "latest_report_id": latest.get("report_id"),
        "latest_flag": latest.get("flag"),
        "ref_low": latest.get("ref_low"),
        "ref_high": latest.get("ref_high"),
        "range_source": latest.get("range_source"),
        "range_status_latest": series["range_status_latest"],
        "direction": series["direction"],
        "change_abs": series["change_abs"],
        "change_pct": series["change_pct"],
        "events": series["events"],
    }


def build_trend_summary(
    reports: list[Any],
    patient_id: str,
    stable_threshold_pct: Optional[float] = None,
) -> dict:
    tests: list[dict] = []
    insufficient: list[dict] = []
    not_comparable: list[dict] = []
    duplicate_notes: list[str] = []

    for canonical in SUPPORTED_CANONICAL_TESTS:
        series = build_test_series(
            reports,
            canonical,
            stable_threshold_pct=stable_threshold_pct,
        )
        not_comparable.extend(series["not_comparable"])
        duplicate_notes.extend(series["duplicate_notes"])
        if series["point_count"] >= 2:
            tests.append(_summary_entry(series))
        elif series["point_count"] == 1:
            insufficient.append(_summary_entry(series))

    tests.sort(
        key=lambda item: (
            item.get("latest_date") or "",
            item.get("display_name") or "",
        ),
        reverse=True,
    )
    insufficient.sort(key=lambda item: item.get("display_name") or "")

    return {
        "patient_id": patient_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "test_count": len(tests),
        "tests": tests,
        "insufficient_tests": insufficient,
        "not_comparable": not_comparable,
        "duplicate_notes": duplicate_notes,
    }


def enrich_lab_results(
    labs: list[dict],
    report_id: str,
    report_text: str,
    created_at: Optional[datetime] = None,
    existing: Optional[list[dict]] = None,
) -> list[dict]:
    """Add trend storage fields, preserving patient exclusions/corrections."""
    stored_date, date_source = extract_report_date(report_text or "")
    if not stored_date:
        uploaded = _as_date_iso(created_at)
        if uploaded:
            stored_date = uploaded
            date_source = "upload"
        else:
            date_source = "upload"

    old_by_canonical: dict[str, list[dict]] = {}
    for old in existing or []:
        key = old.get("canonical_name") or old.get("canonical_test")
        if key:
            old_by_canonical.setdefault(key, []).append(dict(old))

    enriched: list[dict] = []
    for lab in labs or []:
        entry = dict(lab)
        canonical = entry.get("canonical_name") or entry.get("canonical_test")
        entry["canonical_test"] = canonical
        entry.setdefault("original_name", entry.get("name") or canonical)
        entry["report_id"] = report_id
        entry["collected_on"] = stored_date
        entry["date_source"] = date_source or "upload"
        entry.setdefault("excluded_by_patient", False)
        entry.setdefault("edited_by_patient", False)

        old_list = old_by_canonical.get(canonical or "", [])
        if old_list:
            old = old_list.pop(0)
            entry["excluded_by_patient"] = bool(old.get("excluded_by_patient", False))
            entry["edited_by_patient"] = bool(old.get("edited_by_patient", False))
            if entry["edited_by_patient"]:
                for field in (
                    "value",
                    "unit",
                    "ref_low",
                    "ref_high",
                    "flag",
                    "original_value",
                    "original_unit",
                ):
                    if field in old:
                        entry[field] = old[field]
        enriched.append(entry)
    return enriched


def apply_patient_point_update(
    lab: dict,
    excluded_by_patient: Optional[bool] = None,
    corrected_value: Optional[float] = None,
) -> dict:
    """Apply a patient exclusion/correction to one stored lab value."""
    updated = dict(lab)
    if excluded_by_patient is not None:
        updated["excluded_by_patient"] = bool(excluded_by_patient)

    if corrected_value is not None:
        canonical = updated.get("canonical_name") or updated.get("canonical_test")
        if canonical not in REFERENCE_RANGES:
            raise KeyError(canonical)
        value = float(corrected_value)
        if not math.isfinite(value):
            raise ValueError("Value must be a finite number")
        if not updated.get("edited_by_patient"):
            updated["original_value"] = updated.get("original_value", updated.get("value"))
            updated["original_unit"] = updated.get("original_unit", updated.get("unit"))

        raw_unit = str(updated.get("unit") or "")
        standard_unit = REFERENCE_RANGES[canonical]["standard_unit"]
        low = _safe_float(updated.get("ref_low"))
        high = _safe_float(updated.get("ref_high"))
        if raw_unit and normalize_unit(raw_unit) != normalize_unit(standard_unit):
            low = _convert_bound(canonical, low, raw_unit)
            high = _convert_bound(canonical, high, raw_unit)

        updated["value"] = round(value, 6)
        updated["unit"] = standard_unit
        updated["ref_low"] = low
        updated["ref_high"] = high
        updated["flag"] = _flag_from_range(value, low, high)
        updated["edited_by_patient"] = True
        updated["canonical_test"] = canonical
    return updated
