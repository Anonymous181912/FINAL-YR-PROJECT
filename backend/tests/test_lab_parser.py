"""Phase 1 tests: deterministic lab parser over synthetic fixtures.

Fixture file ``fixtures/lab_snippets.jsonl`` is shared with Phase 5
(evaluation chapter), so keep its schema stable:
{id, text, gender, age_years, expected: [{canonical_name, value, flag,
range_source}]}.
"""

import json
import os

import pytest

from app.reports.services.lab_parser import parse_lab_results, canonicalize_test_name

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "lab_snippets.jsonl")


def _load_cases():
    cases = []
    with open(_FIXTURE, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


_CASES = _load_cases()


def test_fixture_has_minimum_cases():
    assert len(_CASES) >= 25, f"need 25+ snippets, have {len(_CASES)}"


def test_fixture_ids_unique():
    ids = [c["id"] for c in _CASES]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("case", _CASES, ids=[c["id"] for c in _CASES])
def test_snippet_parses_as_expected(case):
    results = parse_lab_results(case["text"], gender=case.get("gender"), age_years=case.get("age_years"))
    by_canon = {r["canonical_name"]: r for r in results}
    assert len(results) == len(case["expected"]), (
        f"{case['id']}: got {[(r['canonical_name'], r['value'], r['flag']) for r in results]}"
    )
    for exp in case["expected"]:
        assert exp["canonical_name"] in by_canon, f"{case['id']}: missing {exp['canonical_name']}"
        got = by_canon[exp["canonical_name"]]
        assert got["value"] == pytest.approx(exp["value"], rel=1e-3), f"{case['id']}: value"
        assert got["flag"] == exp["flag"], f"{case['id']}: flag"
        assert got["range_source"] == exp["range_source"], f"{case['id']}: range_source"
        # contract fields always present
        for field in ("name", "canonical_name", "value", "unit", "ref_low", "ref_high",
                      "flag", "range_source", "source_text", "start", "end"):
            assert field in got, f"{case['id']}: missing field {field}"
        assert got["start"] < got["end"]
        assert got["source_text"] in case["text"]
        assert got["ref_low"] < got["ref_high"]
        assert got["flag"] in ("low", "normal", "high", "unknown")


def test_empty_text_returns_empty():
    assert parse_lab_results("") == []
    assert parse_lab_results("   ") == []


def test_no_labs_returns_empty():
    assert parse_lab_results("Patient complains of headache. No fever.") == []


def test_deterministic_repeated_calls():
    text = "Hemoglobin 11.2 g/dL (13.0 - 17.0)\nWBC 6.5 x10^3/uL"
    assert parse_lab_results(text, gender="male") == parse_lab_results(text, gender="male")


def test_canonicalize_test_name():
    assert canonicalize_test_name("Hb") == "hemoglobin"
    assert canonicalize_test_name("TLC") == "wbc"
    assert canonicalize_test_name("wbc") == "wbc"
    assert canonicalize_test_name("nonsense test") is None


def test_printed_range_always_wins_over_table():
    # Value normal by table but low by printed range -> printed wins.
    out = parse_lab_results("Hemoglobin 13.5 g/dL (14.0 - 18.0)", gender="male")
    assert len(out) == 1
    assert out[0]["flag"] == "low"
    assert out[0]["range_source"] == "report"
    assert (out[0]["ref_low"], out[0]["ref_high"]) == (14.0, 18.0)


def test_sex_specific_vs_default_adult_source():
    male = parse_lab_results("Hemoglobin 14.0 g/dL", gender="male")
    assert male[0]["range_source"] == "table"
    unknown = parse_lab_results("Hemoglobin 14.0 g/dL", gender=None)
    assert unknown[0]["range_source"] == "default_adult"
    # Non-sex-split test uses the table directly even without gender.
    wbc = parse_lab_results("WBC 7.0 x10^3/uL", gender=None)
    assert wbc[0]["range_source"] == "table"
