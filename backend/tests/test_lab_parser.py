"""Phase 1 tests: deterministic lab parser over synthetic fixtures.

Fixture file ``fixtures/lab_snippets.jsonl`` is shared with Phase 5
(evaluation chapter), so keep its schema stable:
{id, text, gender, age_years, expected: [{canonical_name, value, flag,
range_source}]}.
"""

import json
import os

import pytest

from app.reports.services.lab_parser import (
    canonicalize_test_name,
    extract_report_date,
    parse_lab_results,
)

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


def test_sex_specific_and_adult_fallback_are_both_table_source():
    male = parse_lab_results("Hemoglobin 14.0 g/dL", gender="male")
    assert male[0]["range_source"] == "table"
    unknown = parse_lab_results("Hemoglobin 14.0 g/dL", gender=None)
    assert unknown[0]["range_source"] == "table"
    # Non-sex-split test uses the table directly even without gender.
    wbc = parse_lab_results("WBC 7.0 x10^3/uL", gender=None)
    assert wbc[0]["range_source"] == "table"


STACKED_CBC_OCR = """Hello@flabs in
rlabs
+91 7253928905
https: |lwww flabs inl
Name
Mr Dummy
Patient ID
PN2
Age/Gender
20/Male
Report ID
REI
Referred By
Self
Collection Date
24/06/2023 08.49 PM
Phone No:
Report Date
24/06/2023 09.02 PM
HAEMATOLOGY
COMPLETE BLOOD COUNT (CBC)
TEST DESCRIPTION
RESULT
REF RANGE
UNIT
Haemoglobin
13- 17
Total Leucocyte Count
5000
4000
10000
Icumm
Differential Leucocyte Count
Neutrophils
Lymphocytes
Eosinophils
1 - 6
Monocytes
2 - 10
Basophils
0.00
0 - 1
Absolute
eucocyte Count
Absolute Neutrophils
2500.00
2000 - 7000
(cumm
Absolute
Lymphocytes
2000.00
b
1000 - 3000
(cumm
Absolute Eosinophils
50.00
500
icumm
Absolute Monocytes
450.00
200 .
1000
icumm
RBC Indices
Mil:
RBC Count
4.5 - 5.5
lion/cumm
MCV
80.00
81 - 101
MCH
30.00
27 - 32
MCHC
37.50
31.5 - 34.5
gldL
Hct
RDW CV
11.6 - 14.,0
RDW-SD
Platelets Indices
Platelet Count
300000
150000
410000
(cumm
PCT
MPV
7.5-11.5
PDW
Interpretation:
g/aL
"""


def test_stacked_ocr_cbc_layout():
    results = parse_lab_results(STACKED_CBC_OCR, gender="male")
    by_canon = {r["canonical_name"]: r for r in results}

    assert set(by_canon) == {
        "wbc", "basophil_percent",
        "absolute_neutrophils", "absolute_lymphocytes",
        "absolute_eosinophils", "absolute_monocytes",
        "mcv", "mch", "mchc", "platelets",
    }

    # Three separate single-number lines = result, low, high. Both the result
    # and the printed bounds are converted to the standard count unit now.
    assert by_canon["wbc"]["value"] == 5.0
    assert (by_canon["wbc"]["ref_low"], by_canon["wbc"]["ref_high"]) == (4.0, 10.0)
    assert by_canon["wbc"]["flag"] == "normal"
    assert by_canon["wbc"]["range_source"] == "report"
    assert by_canon["wbc"]["original_value"] == 5000
    assert by_canon["wbc"]["original_unit"] == "/cumm"

    assert by_canon["platelets"]["value"] == 300.0
    assert (by_canon["platelets"]["ref_low"], by_canon["platelets"]["ref_high"]) == (150.0, 410.0)
    assert by_canon["platelets"]["unit"] == "x10^3/uL"

    # Absolute counts: raw /cumm values are converted to x10^3/uL.
    assert by_canon["absolute_neutrophils"]["value"] == 2.5
    assert by_canon["absolute_neutrophils"]["range_source"] == "report"
    assert by_canon["absolute_lymphocytes"]["value"] == 2.0
    assert by_canon["absolute_monocytes"]["value"] == 0.45
    assert (by_canon["absolute_monocytes"]["ref_low"],
            by_canon["absolute_monocytes"]["ref_high"]) == (0.2, 1.0)

    # Eosinophils had only one range number (OCR lost the low bound), so the
    # table is used instead of inventing a report range.
    assert by_canon["absolute_eosinophils"]["value"] == pytest.approx(0.05)
    assert by_canon["absolute_eosinophils"]["range_source"] == "table"
    assert by_canon["absolute_eosinophils"]["flag"] == "normal"

    assert by_canon["basophil_percent"]["value"] == 0.0
    assert by_canon["basophil_percent"]["range_source"] == "report"
    assert by_canon["mcv"]["value"] == 80
    assert by_canon["mcv"]["flag"] == "low"
    assert by_canon["mch"]["flag"] == "normal"
    assert by_canon["mchc"]["value"] == 37.5
    assert by_canon["mchc"]["flag"] == "high"
    assert by_canon["mchc"]["unit"] == "g/dL"

    # Rows that only had a range and no result must not be invented.
    assert "hemoglobin" not in by_canon
    assert "rbc" not in by_canon
    assert "rdw_cv" not in by_canon


def test_ocr_unit_aliases_are_accepted():
    out = parse_lab_results("WBC 5000 Icumm")
    assert len(out) == 1
    assert out[0]["value"] == 5.0
    assert out[0]["unit"] == "x10^3/uL"

    mchc = parse_lab_results("MCHC 37.5 gldL 31.5 - 34.5")
    assert len(mchc) == 1
    assert mchc[0]["unit"] == "g/dL"
    assert mchc[0]["flag"] == "high"


def test_name_with_only_range_does_not_produce_value():
    out = parse_lab_results("Haemoglobin\n13- 17\nTotal Leucocyte Count\n5000\n4000\n10000\nIcumm")
    assert [r["canonical_name"] for r in out] == ["wbc"]
    assert out[0]["value"] == 5.0


def test_lab_values_become_measurement_entities():
    from app.reports.services.report_service import ReportService

    labs = parse_lab_results("Hemoglobin 11.2 g/dL (13.0 - 17.0)")
    entities = ReportService._lab_measurement_entities(labs)
    assert len(entities) == 1
    assert entities[0]["type"] == "measurement"
    assert entities[0]["text"] == "Hemoglobin"
    assert entities[0]["value"] == "11.2"
    assert entities[0]["unit"] == "g/dL"
    assert entities[0]["severity"] == "low"


def test_vertical_table_name_value_unit_range():
    text = (
        "Haemoglobin\n"
        "15.2\n"
        "g/dL\n"
        "13.5 - 17.5\n"
        "Neutrophils\n"
        "58\n"
        "%\n"
        "40 - 80\n"
    )
    by_canon = {r["canonical_name"]: r for r in parse_lab_results(text, gender="male")}
    assert by_canon["hemoglobin"]["value"] == pytest.approx(15.2)
    assert by_canon["hemoglobin"]["unit"] == "g/dL"
    assert by_canon["hemoglobin"]["flag"] == "normal"
    assert by_canon["neutrophil_percent"]["value"] == pytest.approx(58)
    assert by_canon["neutrophil_percent"]["flag"] == "normal"


def test_pipe_separated_table_row():
    text = "Haemoglobin | 15.2 | g/dL | 13.5 - 17.5\nESR | 28 | mm/hr | 0 - 20"
    by_canon = {r["canonical_name"]: r for r in parse_lab_results(text, gender="female")}
    assert by_canon["hemoglobin"]["value"] == pytest.approx(15.2)
    assert by_canon["esr"]["value"] == pytest.approx(28)
    assert by_canon["esr"]["flag"] == "high"
    assert by_canon["esr"]["unit"] == "mm/hr"


def test_one_sided_reference_ranges():
    low = parse_lab_results("Hemoglobin 18 g/dL <200")
    assert low[0]["ref_low"] is None
    assert low[0]["ref_high"] == 200
    assert low[0]["flag"] == "normal"

    high = parse_lab_results("ESR 30 mm/hr > 5")
    assert high[0]["ref_low"] == 5
    assert high[0]["ref_high"] is None
    assert high[0]["flag"] == "normal"

    below = parse_lab_results("ESR 3 mm/hr > 5")
    assert below[0]["flag"] == "low"


def test_ocr_numeric_noise_and_literal_newlines():
    # "l5.2" -> 15.2 and "1O.O" -> 10.0 only inside numeric tokens; literal
    # "\n" and "|n" are newline separators, not words.
    text = "Haemoglobin|nl5.2|ng/dL|n13.5 - 17.5\\nMCV | 1O.O | fL | 80 - 100"
    by_canon = {r["canonical_name"]: r for r in parse_lab_results(text)}
    assert by_canon["hemoglobin"]["value"] == pytest.approx(15.2)
    assert by_canon["mcv"]["value"] == pytest.approx(10.0)


def test_collection_date_extracted_when_present():
    from app.reports.services.lab_parser import extract_collection_date

    text = "Collection Date\n24/06/2023 08.49 PM\nReport Date\n24/06/2023 09.02 PM"
    assert extract_collection_date(text) == "2023-06-24"
    assert extract_collection_date("Collection Date : 24-10-2026 10:45 AM") == "2026-10-24"
    assert extract_collection_date("No dates here") is None

LABSMART_OCR = """Labsmart Software
Collected on
:17/10/2024
Reported on
:17/10/2024 04:55 PM
HEMOGLOBIN
15
g/dl
13 - 17
TOTAL LEUKOCYTE COUNT
5,100
cumm
4,800 - 10,800
LYMPHOCYTE
L
18
%
20-40
EOSINOPHILS
%
1-6
MONOCYTES
L
1
%
2-10
PLATELET COUNT
3.5
lakhs/cumm
1.5 - 4.1
TOTAL RBC COUNT
5
million/cumm
4.5 - 5.5
HEMATOCRIT VALUE, HCT
42
%
40 - 50
MEAN CORPUSCULAR VOLUME, MCV
84.0
fL
83 - 101
MEAN CELL HAEMOGLOBIN, MCH
30.0
Pg
27-32
MEAN CELL HAEMOGLOBIN CON, MCHC H
35.7
%
31.5 - 34.5
"""


def test_labsmart_stacked_layout_flags_missing_values_and_units():
    labs = parse_lab_results(LABSMART_OCR, gender="male")
    by_canon = {r["canonical_name"]: r for r in labs}

    assert by_canon["hemoglobin"]["value"] == 15.0
    assert by_canon["wbc"]["value"] == 5.1
    assert by_canon["wbc"]["original_unit"] == "/cumm"
    assert by_canon["lymphocyte_percent"]["value"] == 18.0
    assert by_canon["lymphocyte_percent"]["flag"] == "low"
    assert by_canon["platelets"]["value"] == 350.0
    assert by_canon["rbc"]["value"] == 5.0
    assert by_canon["mcv"]["value"] == 84.0
    assert by_canon["mchc"]["value"] == pytest.approx(35.7)
    assert by_canon["mchc"]["unit"] == "g/dL"
    assert by_canon["mchc"]["original_unit"] == "%"
    assert by_canon["mchc"]["flag"] == "high"
    assert "eosinophil_percent" not in by_canon
    assert extract_report_date(LABSMART_OCR)[0] == "2024-10-17"


def test_sahara_inline_result_with_next_line_unit_and_range():
    text = """SAHARA PATHOLOGY LAB
DATE-06/08/24
HAEMOGLOBIN
14.0
Gm%
13-18
TOTALLEUCOCYTE COUNT (TLC) 7500
/cmm
4000-10,000
NEUTROPHILES
50
% % % % %
40-75
LYMPHOCYTES
55
20-75
PLATELETS COUNTS
3.70
LACS/CMM
1.50-4.50
RBCs COUNT
2.37
MIL/CMM
4.5-5.5
M.C.V.
80
PG
80-96
M.C.H.
30
FL
28-32
M.C.H.C.
24.4
32-36
P.C.V.
39.0
%
40-54
"""

    by_canon = {
        r["canonical_name"]: r for r in parse_lab_results(text, gender="male")
    }
    assert by_canon["wbc"]["value"] == 7.5
    assert by_canon["wbc"]["unit"] == "x10^3/uL"
    assert by_canon["wbc"]["ref_low"] == 4.0
    assert by_canon["neutrophil_percent"]["value"] == 50.0
    assert by_canon["neutrophil_percent"]["unit_status"] == "assumed"
    assert by_canon["platelets"]["value"] == 370.0
    assert by_canon["rbc"]["value"] == pytest.approx(2.37)
    assert by_canon["rbc"]["flag"] == "low"
    assert by_canon["mcv"]["value"] == 80.0
    assert by_canon["mcv"]["unit"] == "fL"
    assert by_canon["mcv"]["unit_status"] == "inconsistent"
    assert by_canon["mch"]["unit"] == "pg"
    assert by_canon["mchc"]["value"] == pytest.approx(24.4)
    assert by_canon["mchc"]["unit"] == "g/dL"
    assert by_canon["mchc"]["unit_status"] == "assumed"
    assert by_canon["hematocrit"]["value"] == 39.0
    assert extract_report_date(text) == ("2024-08-06", "reported")


def test_decimal_comma_and_percent_mchc_are_normalised():
    by_canon = {
        r["canonical_name"]: r
        for r in parse_lab_results("M.C.V. 84,0 fL 80-96\nMCHC 35,7 % 31.5-34.5")
    }
    assert by_canon["mcv"]["value"] == 84.0
    assert by_canon["mchc"]["value"] == pytest.approx(35.7)
    assert by_canon["mchc"]["unit"] == "g/dL"
