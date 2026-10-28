"""Longitudinal health trend analysis tests (deterministic backend)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.main import app
from app.reports.services.lab_parser import (
    extract_collection_date,
    extract_report_date,
    parse_lab_results,
)
from app.reports.services.trend_service import (
    DISCLAIMER,
    apply_patient_point_update,
    build_test_series,
    build_trend_summary,
    enrich_lab_results,
)

client = TestClient(app)


def _report(rid, labs, text="", created=None, patient_id="p1"):
    return SimpleNamespace(
        id=rid,
        patient_id=patient_id,
        extracted_text=text,
        created_at=created or datetime(2026, 1, 1, tzinfo=timezone.utc),
        lab_results=labs,
    )


def _lab(value, low=70, high=100, canonical="fasting_glucose", unit="mg/dL", **extra):
    data = {
        "canonical_test": canonical,
        "canonical_name": canonical,
        "value": value,
        "unit": unit,
        "ref_low": low,
        "ref_high": high,
        "range_source": "report",
        "flag": "normal",
    }
    data.update(extra)
    return data


def _series(values, low=70, high=100, threshold=5.0):
    reports = []
    for index, value in enumerate(values):
        day = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index * 30)
        reports.append(
            _report(
                f"r{index + 1}",
                [_lab(value, low=low, high=high, collected_on=day.date().isoformat(),
                      date_source="collected")],
                created=day,
            )
        )
    return build_test_series(reports, "fasting_glucose", stable_threshold_pct=threshold)


def test_direction_uses_latest_vs_previous_and_explanation_uses_first_to_latest():
    series = _series([95, 112, 128])
    assert series["direction"] == "rising"
    assert series["change_pct"] == pytest.approx(14.29)
    assert series["change_abs"] == pytest.approx(16)
    assert "34.7%" in series["explanation"]
    assert "95 mg/dL" in series["explanation"]
    assert "128 mg/dL" in series["explanation"]
    assert "above the reference range" in series["explanation"]
    assert DISCLAIMER in series["explanation"]


def test_exactly_five_percent_is_not_stable():
    assert _series([100, 105])["direction"] == "rising"
    assert _series([100, 95])["direction"] == "falling"
    assert _series([100, 104.99])["direction"] == "stable"


def test_single_point_is_insufficient_data():
    series = _series([95])
    assert series["point_count"] == 1
    assert series["direction"] == "insufficient_data"
    assert "At least two comparable" in series["explanation"]


def test_events_detect_new_return_still_and_crossing():
    newly = _series([100, 120])
    assert "newly_out_of_range" in newly["events"]

    returned = _series([120, 90])
    assert "returned_to_range" in returned["events"]

    still = _series([120, 130])
    assert "still_out_of_range" in still["events"]

    crossed = _series([60, 120])
    assert "crossed_range_between_reports" in crossed["events"]


def test_old_mmol_unit_is_converted_for_value_and_printed_range():
    report = _report(
        "r1",
        [
            _lab(
                5.0,
                low=3.9,
                high=5.5,
                unit="mmol/L",
                collected_on="2026-01-01",
                date_source="collected",
            )
        ],
    )
    report2 = _report(
        "r2",
        [
            _lab(
                6.0,
                low=3.9,
                high=5.5,
                unit="mmol/L",
                collected_on="2026-02-01",
                date_source="collected",
            )
        ],
    )
    series = build_test_series([report, report2], "fasting_glucose")
    assert series["points"][0]["value"] == pytest.approx(90.0)
    assert series["points"][0]["ref_low"] == pytest.approx(70.2)
    assert series["points"][0]["ref_high"] == pytest.approx(99.0)
    assert series["points"][1]["value"] == pytest.approx(108.0)


def test_missing_unit_is_listed_not_comparable():
    report = _report(
        "r1",
        [_lab(95, unit="", collected_on="2026-01-01", date_source="collected")],
    )
    series = build_test_series([report], "fasting_glucose")
    assert series["points"] == []
    assert series["not_comparable"][0]["report_id"] == "r1"
    assert "cannot be compared" in series["not_comparable"][0]["reason"]


def test_duplicate_identical_value_same_date_is_shown_once():
    reports = [
        _report(
            "r1",
            [_lab(95, collected_on="2026-01-01", date_source="collected")],
        ),
        _report(
            "r2",
            [_lab(95, collected_on="2026-01-01", date_source="collected")],
        ),
    ]
    series = build_test_series(reports, "fasting_glucose")
    assert series["point_count"] == 1
    assert series["points"][0]["duplicate_count"] == 2
    assert "identical values" in series["duplicate_notes"][0]


def test_excluded_point_is_ignored_but_returned_for_restore():
    reports = [
        _report(
            "r1",
            [_lab(95, collected_on="2026-01-01", date_source="collected")],
        ),
        _report(
            "r2",
            [_lab(130, collected_on="2026-02-01", date_source="collected",
                  excluded_by_patient=True)],
        ),
    ]
    series = build_test_series(reports, "fasting_glucose")
    assert series["point_count"] == 1
    assert series["excluded_points"][0]["value"] == 130
    assert series["excluded_points"][0]["excluded_by_patient"] is True


def test_apply_patient_correction_sets_original_and_recomputes_flag():
    lab = _lab(12.0, low=12.0, high=16.0, canonical="hemoglobin", unit="g/dL")
    updated = apply_patient_point_update(lab, corrected_value=14.5)
    assert updated["value"] == 14.5
    assert updated["flag"] == "normal"
    assert updated["edited_by_patient"] is True
    assert updated["original_value"] == 12.0


def test_summary_sorts_and_includes_insufficient_tests():
    reports = [
        _report("r1", [
            _lab(95, collected_on="2026-01-01", date_source="collected"),
            _lab(7.0, low=4, high=11, canonical="wbc", unit="x10^3/uL",
                 collected_on="2026-01-01", date_source="collected"),
        ]),
        _report("r2", [
            _lab(130, collected_on="2026-02-01", date_source="collected"),
        ]),
    ]
    summary = build_trend_summary(reports, "p1")
    assert [t["canonical_test"] for t in summary["tests"]] == ["fasting_glucose"]
    assert [t["canonical_test"] for t in summary["insufficient_tests"]] == ["wbc"]
    assert summary["tests"][0]["range_status_latest"] == "above"


def test_date_parsing_sources_and_formats():
    assert extract_report_date("Collected on 24-Jun-2023") == ("2023-06-24", "collected")
    assert extract_report_date("Report Date : 24/06/23") == ("2023-06-24", "reported")
    assert extract_report_date("Registered on\n24 October 2026") == ("2026-10-24", "reported")
    assert extract_report_date("DATE- 24-10-2026") == ("2026-10-24", "reported")
    assert extract_report_date("no date here") == (None, None)
    assert extract_collection_date("Collection Date\n24/06/2023") == "2023-06-24"


def test_post_prandial_glucose_and_unit_aliases_parse():
    labs = parse_lab_results(
        "Post Prandial Glucose 160 mg/dL (70 - 140)\n"
        "Platelets 3.0 lakhs/cmm (1.5 - 4.0)\n"
        "RBC 4.5 million/cmm (4.5 - 5.5)"
    )
    by_canon = {lab["canonical_name"]: lab for lab in labs}
    assert by_canon["post_prandial_glucose"]["value"] == 160
    assert by_canon["platelets"]["value"] == 300
    assert by_canon["platelets"]["unit"] == "x10^3/uL"
    assert by_canon["rbc"]["value"] == 4.5
    assert by_canon["rbc"]["unit"] == "million/uL"


def test_enrich_keeps_patient_edits_across_reparse():
    existing = [
        _lab(130, edited_by_patient=True, excluded_by_patient=False,
             original_value=128, original_unit="mg/dL"),
    ]
    labs = parse_lab_results("Collection Date 10/07/2026\nFasting Glucose 128 mg/dL")
    enriched = enrich_lab_results(
        labs,
        report_id="r1",
        report_text="Collection Date 10/07/2026\nFasting Glucose 128 mg/dL",
        existing=existing,
    )
    assert enriched[0]["value"] == 130
    assert enriched[0]["edited_by_patient"] is True
    assert enriched[0]["original_value"] == 128
    assert enriched[0]["collected_on"] == "2026-07-10"
    assert enriched[0]["date_source"] == "collected"


def _user(uid, email, role, name="Test"):
    user = AsyncMock()
    user.id = uid
    user.email = email
    user.role = role
    user.full_name = name
    user.is_active = True
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = user.created_at
    return user


def _token(sub, email, role):
    from app.core.security import create_access_token

    return create_access_token(data={"sub": sub, "email": email, "role": role})


class TestTrendAccess:
    def test_doctor_requires_active_grant_and_audit_is_written(self):
        app.dependency_overrides[get_current_user] = lambda: _user(
            "d1", "d@t.com", "doctor", "Dr"
        )
        doctor = AsyncMock()
        doctor.is_verified = True
        doctor.verification_status = "approved"
        patient = AsyncMock()
        patient.id = "p1"
        patient.user_id = "p1"
        patient.patient_id = "p1"
        report = _report(
            "r1",
            [_lab(95, collected_on="2026-01-01", date_source="collected")],
        )
        try:
            with patch(
                "app.database.repositories.doctor_repository.DoctorRepository.get_by_user_id",
                new=AsyncMock(return_value=doctor),
            ), patch("app.reports.trends_router.PatientRepository") as pat_cls, \
               patch("app.reports.trends_router.ReportRepository") as rep_cls, \
               patch("app.reports.trends_router.grant_checks.canonical_patient_id",
                     new=AsyncMock(return_value="p1")), \
               patch("app.reports.trends_router.grant_checks.require_active_grant",
                     new=AsyncMock()) as grant, \
               patch("app.reports.trends_router.log_access", new=AsyncMock()) as audit:
                pat_cls.return_value.get_by_patient_id = AsyncMock(return_value=patient)
                rep_cls.return_value.list_all_for_patients = AsyncMock(return_value=[report])
                response = client.get(
                    "/api/v1/trends/fasting_glucose",
                    params={"patient_id": "p1"},
                    headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"},
                )
                assert response.status_code == 200, response.text
                grant.assert_awaited_once_with("p1", "d1", "reports")
                audit.assert_awaited_once()
                assert audit.call_args.args[3] == "health_trend"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_doctor_without_grant_gets_404(self):
        app.dependency_overrides[get_current_user] = lambda: _user(
            "d1", "d@t.com", "doctor", "Dr"
        )
        doctor = AsyncMock()
        doctor.is_verified = True
        doctor.verification_status = "approved"
        patient = AsyncMock()
        patient.id = "p1"
        patient.user_id = "p1"
        patient.patient_id = "p1"
        try:
            with patch(
                "app.database.repositories.doctor_repository.DoctorRepository.get_by_user_id",
                new=AsyncMock(return_value=doctor),
            ), patch("app.reports.trends_router.PatientRepository") as pat_cls, \
               patch("app.reports.trends_router.ReportRepository"), \
               patch("app.reports.trends_router.grant_checks.canonical_patient_id",
                     new=AsyncMock(return_value="p1")), \
               patch("app.reports.trends_router.grant_checks.require_active_grant",
                     new=AsyncMock(side_effect=HTTPException(status_code=404))), \
               patch("app.reports.trends_router.log_access", new=AsyncMock()):
                pat_cls.return_value.get_by_patient_id = AsyncMock(return_value=patient)
                response = client.get(
                    "/api/v1/trends/fasting_glucose",
                    params={"patient_id": "p1"},
                    headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"},
                )
                assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_patient_can_exclude_own_point(self):
        app.dependency_overrides[get_current_user] = lambda: _user(
            "p1", "p@t.com", "patient", "P"
        )
        patient = AsyncMock()
        patient.id = "p1"
        patient.user_id = "p1"
        patient.patient_id = "p1"
        report = _report(
            "r1",
            [_lab(95, collected_on="2026-01-01", date_source="collected")],
            patient_id="p1",
        )
        try:
            def update(_rid, fields):
                report.lab_results = fields["lab_results"]
                return report

            with patch("app.reports.trends_router.PatientRepository") as pat_cls, \
                 patch("app.reports.trends_router.ReportRepository") as rep_cls, \
                 patch("app.reports.trends_router.log_access", new=AsyncMock()) as audit:
                pat_cls.return_value.get_by_user_id = AsyncMock(return_value=patient)
                rep_cls.return_value.get_by_id = AsyncMock(return_value=report)
                rep_cls.return_value.update = AsyncMock(side_effect=update)
                rep_cls.return_value.list_all_for_patients = AsyncMock(return_value=[report])
                response = client.patch(
                    "/api/v1/trends/fasting_glucose/points/r1",
                    json={"corrected_value": 110},
                    headers={"Authorization": f"Bearer {_token('p1', 'p@t.com', 'patient')}"},
                )
                assert response.status_code == 200, response.text
                body = response.json()
                assert body["series"]["latest"]["value"] == 110
                assert body["series"]["latest"]["edited_by_patient"] is True
                audit.assert_awaited_once()
        finally:
            app.dependency_overrides.pop(get_current_user, None)
