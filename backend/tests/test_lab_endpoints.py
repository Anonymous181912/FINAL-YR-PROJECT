"""Phase 1 endpoint tests: upload computes labs, /labs, /trends."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.dependencies import get_current_user

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_mongo():
    mock_db = MagicMock()

    def get_mock_collection(name):
        return AsyncMock()

    mock_db.__getitem__ = MagicMock(side_effect=get_mock_collection)

    with patch("app.database.connection.db", mock_db), \
         patch("app.database.connection.connect_to_mongo"), \
         patch("app.database.connection.close_mongo_connection"), \
         patch("app.database.indexes.create_indexes"):
        yield


def _user(uid, email, role, name="Test"):
    u = AsyncMock()
    u.id = uid
    u.email = email
    u.role = role
    u.full_name = name
    u.is_active = True
    u.created_at = datetime.now(timezone.utc)
    u.updated_at = datetime.now(timezone.utc)
    return u


def _token(sub, email, role):
    from app.core.security import create_access_token

    return create_access_token(data={"sub": sub, "email": email, "role": role})


def _report(rid, pid, labs, created=None):
    r = AsyncMock()
    r.id = rid
    r.patient_id = pid
    r.title = "Blood Test"
    r.category = "Blood Test"
    r.status = "completed"
    r.created_at = created or datetime.now(timezone.utc)
    r.updated_at = r.created_at
    r.extraction_method = "text"
    r.extracted_text = "Hemoglobin 14 g/dL"
    r.ocr_used = False
    r.entities = []
    r.lab_results = labs
    r.nlp_status = "completed"
    r.ai_status = "not_started"
    r.ai_interpretation = None
    r.important_findings = []
    r.simplified_explanation = None
    r.glossary = {}
    r.metadata = {}
    r.error_message = None
    r.file_path = None
    r.file_name = "t.txt"
    r.file_size = 10
    r.nlp_processed_at = None
    r.ai_processed_at = None
    r.processed_at = r.created_at
    r.doctor_id = None
    r.original_text = None
    return r


class TestUploadComputesLabs:
    def test_txt_upload_includes_lab_results(self):
        app.dependency_overrides[get_current_user] = lambda: _user("p1", "p@t.com", "patient", "P")
        try:
            with patch("app.reports.services.report_service.PDFExtractionService"), \
                 patch("app.reports.services.report_service.OCRService"):
                token = _token("p1", "p@t.com", "patient")
                r = client.post(
                    "/api/v1/reports/upload",
                    data={"category": "Blood Test", "title": "CBC"},
                    files={"file": ("cbc.txt", b"Hemoglobin 9.5 g/dL\nWBC 12,000 /cumm", "text/plain")},
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert r.status_code == 201, r.text
                labs = r.json()["lab_results"]
                by_canon = {lab["canonical_name"]: lab for lab in labs}
                assert by_canon["hemoglobin"]["flag"] == "low"  # printed? no -> table default_adult
                assert by_canon["wbc"]["value"] == pytest.approx(12.0)
                assert by_canon["wbc"]["flag"] == "high"
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestLabsEndpoint:
    def test_patient_gets_own_labs(self):
        app.dependency_overrides[get_current_user] = lambda: _user("p1", "p@t.com", "patient", "P")
        try:
            labs = [{"name": "Hemoglobin", "canonical_name": "hemoglobin", "value": 9.5,
                     "unit": "g/dL", "ref_low": 12.0, "ref_high": 16.0, "flag": "low",
                     "range_source": "default_adult", "source_text": "Hemoglobin 9.5 g/dL",
                     "start": 0, "end": 20}]
            with patch("app.reports.services.report_service.ReportRepository") as repo_cls:
                inst = AsyncMock()
                inst.get_by_id.return_value = _report("r1", "p1", labs)
                repo_cls.return_value = inst
                r = client.get("/api/v1/reports/r1/labs", headers={"Authorization": f"Bearer {_token('p1', 'p@t.com', 'patient')}"})
                assert r.status_code == 200
                assert r.json()["lab_results"][0]["flag"] == "low"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_other_patient_labs_404(self):
        app.dependency_overrides[get_current_user] = lambda: _user("pa", "a@t.com", "patient", "A")
        try:
            with patch("app.reports.services.report_service.ReportRepository") as repo_cls:
                inst = AsyncMock()
                inst.get_by_id.return_value = _report("r1", "pb", [])
                repo_cls.return_value = inst
                r = client.get("/api/v1/reports/r1/labs", headers={"Authorization": f"Bearer {_token('pa', 'a@t.com', 'patient')}"})
                assert r.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_unverified_doctor_labs_403(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr")
        try:
            prof = AsyncMock()
            prof.is_verified = False
            prof.verification_status = "pending"
            with patch(
                "app.database.repositories.doctor_repository.DoctorRepository.get_by_user_id",
                new=AsyncMock(return_value=prof),
            ):
                r = client.get("/api/v1/reports/r1/labs", headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"})
                assert r.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestTrendsEndpoint:
    def _patient(self, pid="p1", uid="p1"):
        p = AsyncMock()
        p.id = pid
        p.user_id = uid
        p.patient_id = pid
        return p

    def _patch_repos(self, reports, patient=None):
        pat_cls = patch("app.reports.trends_router.PatientRepository")
        rep_cls = patch("app.reports.trends_router.ReportRepository")
        audit = patch("app.reports.trends_router.log_access", new=AsyncMock())
        return pat_cls, rep_cls, audit

    def test_patient_trends_two_points(self):
        from datetime import timedelta

        app.dependency_overrides[get_current_user] = lambda: _user("p1", "p@t.com", "patient", "P")
        try:
            t0 = datetime.now(timezone.utc) - timedelta(days=30)
            r1 = _report("r1", "p1", [{"canonical_test": "hemoglobin", "canonical_name": "hemoglobin",
                                       "value": 11.0, "unit": "g/dL", "flag": "low",
                                       "ref_low": 12.0, "ref_high": 16.0,
                                       "range_source": "table"}], created=t0)
            r2 = _report("r2", "p1", [{"canonical_test": "hemoglobin", "canonical_name": "hemoglobin",
                                       "value": 13.0, "unit": "g/dL", "flag": "normal",
                                       "ref_low": 12.0, "ref_high": 16.0,
                                       "range_source": "table"}])
            with patch("app.reports.trends_router.PatientRepository") as pat_cls, \
                 patch("app.reports.trends_router.ReportRepository") as rep_cls, \
                 patch("app.reports.trends_router.log_access", new=AsyncMock()):
                pat = AsyncMock()
                pat.get_by_user_id.return_value = self._patient()
                pat.get_by_patient_id.return_value = self._patient()
                pat_cls.return_value = pat
                rep = AsyncMock()
                rep.list_all_for_patients.return_value = [r1, r2]
                rep_cls.return_value = rep
                r = client.get("/api/v1/trends/hemoglobin",
                               headers={"Authorization": f"Bearer {_token('p1', 'p@t.com', 'patient')}"})
                assert r.status_code == 200, r.text
                body = r.json()
                assert body["canonical_test"] == "hemoglobin"
                assert len(body["points"]) == 2
                assert body["points"][0]["report_id"] == "r1"  # chronological
                assert "This is not a diagnosis" in body["explanation"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_trends_uses_collection_date_with_upload_fallback(self):
        from datetime import timedelta

        app.dependency_overrides[get_current_user] = lambda: _user("p1", "p@t.com", "patient", "P")
        try:
            t0 = datetime.now(timezone.utc) - timedelta(days=30)
            r1 = _report("r1", "p1", [{"canonical_test": "hemoglobin", "canonical_name": "hemoglobin",
                                       "value": 11.0, "unit": "g/dL", "flag": "low",
                                       "ref_low": 12.0, "ref_high": 16.0,
                                       "range_source": "table"}], created=t0)
            r1.extracted_text = "Collection Date\n24/06/2023 08.49 PM\nHemoglobin 11.0 g/dL"
            r2 = _report("r2", "p1", [{"canonical_test": "hemoglobin", "canonical_name": "hemoglobin",
                                       "value": 13.0, "unit": "g/dL", "flag": "normal",
                                       "ref_low": 12.0, "ref_high": 16.0,
                                       "range_source": "table"}])
            r2.extracted_text = "Hemoglobin 13.0 g/dL"
            with patch("app.reports.trends_router.PatientRepository") as pat_cls, \
                 patch("app.reports.trends_router.ReportRepository") as rep_cls, \
                 patch("app.reports.trends_router.log_access", new=AsyncMock()):
                pat = AsyncMock()
                pat.get_by_user_id.return_value = self._patient()
                pat.get_by_patient_id.return_value = self._patient()
                pat_cls.return_value = pat
                rep = AsyncMock()
                rep.list_all_for_patients.return_value = [r1, r2]
                rep_cls.return_value = rep
                r = client.get("/api/v1/trends/hemoglobin",
                               headers={"Authorization": f"Bearer {_token('p1', 'p@t.com', 'patient')}"})
                assert r.status_code == 200, r.text
                points = r.json()["points"]
                assert points[0]["collected_on"] == "2023-06-24"
                assert points[0]["date_source"] == "collected"
                assert points[1]["date_source"] == "upload"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_trends_single_point_insufficient_data(self):
        app.dependency_overrides[get_current_user] = lambda: _user("p1", "p@t.com", "patient", "P")
        try:
            one = _report("r1", "p1", [{"canonical_test": "hemoglobin", "canonical_name": "hemoglobin",
                                        "value": 13.0, "unit": "g/dL", "flag": "normal",
                                        "ref_low": 12.0, "ref_high": 16.0,
                                        "range_source": "table"}])
            with patch("app.reports.trends_router.PatientRepository") as pat_cls, \
                 patch("app.reports.trends_router.ReportRepository") as rep_cls, \
                 patch("app.reports.trends_router.log_access", new=AsyncMock()):
                pat = AsyncMock()
                pat.get_by_user_id.return_value = self._patient()
                pat.get_by_patient_id.return_value = self._patient()
                pat_cls.return_value = pat
                rep = AsyncMock()
                rep.list_all_for_patients.return_value = [one]
                rep_cls.return_value = rep
                r = client.get("/api/v1/trends/Hb",
                               headers={"Authorization": f"Bearer {_token('p1', 'p@t.com', 'patient')}"})
                assert r.status_code == 200
                assert r.json()["point_count"] == 1
                assert r.json()["direction"] == "insufficient_data"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_trends_unknown_test_400(self):
        app.dependency_overrides[get_current_user] = lambda: _user("p1", "p@t.com", "patient", "P")
        try:
            r = client.get("/api/v1/trends/unobtanium",
                           headers={"Authorization": f"Bearer {_token('p1', 'p@t.com', 'patient')}"})
            assert r.status_code == 400
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_doctor_needs_patient_id(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr")
        try:
            doctor = AsyncMock()
            doctor.is_verified = True
            doctor.verification_status = "approved"
            with patch(
                "app.database.repositories.doctor_repository.DoctorRepository.get_by_user_id",
                new=AsyncMock(return_value=doctor),
            ):
                r = client.get("/api/v1/trends/hemoglobin",
                               headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"})
                assert r.status_code == 400
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_patient_cannot_see_other_trends(self):
        # patient role ignores patient_id param and uses own profile
        app.dependency_overrides[get_current_user] = lambda: _user("pa", "a@t.com", "patient", "A")
        try:
            with patch("app.reports.trends_router.PatientRepository") as pat_cls, \
                 patch("app.reports.trends_router.ReportRepository") as rep_cls, \
                 patch("app.reports.trends_router.log_access", new=AsyncMock()):
                pat = AsyncMock()
                pat.get_by_user_id.return_value = self._patient(pid="pa", uid="pa")
                pat.get_by_patient_id.return_value = self._patient(pid="pa", uid="pa")
                pat_cls.return_value = pat
                rep = AsyncMock()
                rep.list_all_for_patients.return_value = []
                rep_cls.return_value = rep
                r = client.get("/api/v1/trends/wbc", params={"patient_id": "pb"},
                               headers={"Authorization": f"Bearer {_token('pa', 'a@t.com', 'patient')}"})
                assert r.status_code == 200
                rep.list_all_for_patients.assert_called_once()
                ids = rep.list_all_for_patients.call_args[0][0]
                assert "pa" in ids
                assert "pb" not in ids
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_summary_lists_only_tests_with_two_points(self):
        app.dependency_overrides[get_current_user] = lambda: _user("p1", "p@t.com", "patient", "P")
        try:
            r1 = _report("r1", "p1", [
                {"canonical_test": "hemoglobin", "canonical_name": "hemoglobin", "value": 11.0,
                 "unit": "g/dL", "flag": "low", "ref_low": 12.0, "ref_high": 16.0,
                 "range_source": "table"},
                {"canonical_test": "wbc", "canonical_name": "wbc", "value": 7.0,
                 "unit": "x10^3/uL", "flag": "normal", "ref_low": 4.0, "ref_high": 11.0,
                 "range_source": "table"},
            ])
            r2 = _report("r2", "p1", [
                {"canonical_test": "hemoglobin", "canonical_name": "hemoglobin", "value": 13.0,
                 "unit": "g/dL", "flag": "normal", "ref_low": 12.0, "ref_high": 16.0,
                 "range_source": "table"},
            ])
            with patch("app.reports.trends_router.PatientRepository") as pat_cls, \
                 patch("app.reports.trends_router.ReportRepository") as rep_cls, \
                 patch("app.reports.trends_router.log_access", new=AsyncMock()):
                pat = AsyncMock()
                pat.get_by_user_id.return_value = self._patient()
                pat.get_by_patient_id.return_value = self._patient()
                pat_cls.return_value = pat
                rep = AsyncMock()
                rep.list_all_for_patients.return_value = [r1, r2]
                rep_cls.return_value = rep
                r = client.get("/api/v1/trends/summary",
                               headers={"Authorization": f"Bearer {_token('p1', 'p@t.com', 'patient')}"})
                assert r.status_code == 200, r.text
                body = r.json()
                assert [item["canonical_test"] for item in body["tests"]] == ["hemoglobin"]
                assert body["insufficient_tests"][0]["canonical_test"] == "wbc"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
