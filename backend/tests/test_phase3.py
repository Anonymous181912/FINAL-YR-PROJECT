"""Phase 3 tests: consent flow, enforcement negatives, grant helper, audit."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.dependencies import get_current_user

# Original helper implementations (captured at import, before the conftest
# allow-stub replaces the module attributes for pre-existing tests).
from app.access.grants import get_active_grant as _REAL_GET_GRANT
from app.access.grants import require_active_grant as _REAL_REQUIRE_GRANT

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


def _grant(gid="g1", pid="p1", did="d1", status="active", expires=None, scope=None):
    from app.models.access import AccessGrantInDB

    now = datetime.now(timezone.utc)
    return AccessGrantInDB(id=gid, patient_id=pid, doctor_id=did,
                           scope=scope or ["reports", "prescriptions", "history"],
                           status=status, created_at=now, updated_at=now,
                           expires_at=expires)


def _patient_prof(pid="p1", uid="p1"):
    p = AsyncMock()
    p.id = pid
    p.user_id = uid
    p.patient_id = pid
    p.full_name = "P"
    return p


class TestAccessFlow:
    def test_doctor_requests_patient_approves(self):
        # doctor creates request (no pre-existing grant: override allow-stub)
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr")
        try:
            with patch("app.access.router.AccessRequestRepository") as req_cls, \
                 patch("app.access.router.AccessGrantRepository") as grant_cls, \
                 patch("app.access.grants.get_active_grant", new=AsyncMock(return_value=None)):
                req = AsyncMock()
                req.pending_for.return_value = None
                req.create_request.return_value = AsyncMock(id="req1", patient_id="p1", doctor_id="d1",
                                                            scope=["reports"], message=None, status="pending",
                                                            created_at=datetime.now(timezone.utc),
                                                            updated_at=datetime.now(timezone.utc),
                                                            decided_at=None)
                req_cls.return_value = req
                grant_cls.return_value = AsyncMock()
                r = client.post("/api/v1/access/requests",
                                json={"patient_id": "p1", "scope": ["reports"]},
                                headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"})
                assert r.status_code == 201, r.text
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        # patient approves with expiry
        app.dependency_overrides[get_current_user] = lambda: _user("p1", "p@t.com", "patient", "P")
        try:
            with patch("app.access.router.AccessRequestRepository") as req_cls, \
                 patch("app.access.router.AccessGrantRepository") as grant_cls, \
                 patch("app.access.router.PatientRepository") as pat_cls:
                req = AsyncMock()
                doc = {"id": "req1", "patient_id": "p1", "doctor_id": "d1", "scope": ["reports"],
                       "message": None, "status": "pending",
                       "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
                       "decided_at": None}
                req.get_by_id.return_value = doc
                req.decide.return_value = AsyncMock()
                req_cls.return_value = req
                grant = AsyncMock()
                grant.get_active.return_value = None
                new_grant = _grant(expires=datetime.now(timezone.utc) + timedelta(days=7))
                grant.create_grant.return_value = new_grant
                grant.get_active.return_value = new_grant
                grant_cls.return_value = grant
                pat = AsyncMock()
                pat.get_by_user_id.return_value = _patient_prof()
                pat_cls.return_value = pat
                r = client.post("/api/v1/access/requests/req1/approve",
                                json={"expires_in_days": 7},
                                headers={"Authorization": f"Bearer {_token('p1', 'p@t.com', 'patient')}"})
                assert r.status_code == 200, r.text
                assert r.json()["status"] == "active"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_patient_denies_and_revokes(self):
        app.dependency_overrides[get_current_user] = lambda: _user("p1", "p@t.com", "patient", "P")
        try:
            with patch("app.access.router.AccessRequestRepository") as req_cls, \
                 patch("app.access.router.AccessGrantRepository") as grant_cls, \
                 patch("app.access.router.PatientRepository") as pat_cls:
                doc = {"id": "req1", "patient_id": "p1", "doctor_id": "d1", "scope": ["reports"],
                       "message": None, "status": "pending",
                       "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
                       "decided_at": None}
                req = AsyncMock()
                req.get_by_id.return_value = doc
                from app.models.access import AccessRequestInDB

                _now = datetime.now(timezone.utc)
                req.decide.return_value = AccessRequestInDB(
                    id="req1", patient_id="p1", doctor_id="d1", scope=["reports"],
                    message=None, status="denied", created_at=_now, updated_at=_now,
                    decided_at=_now)
                req_cls.return_value = req
                pat = AsyncMock()
                pat.get_by_user_id.return_value = _patient_prof()
                pat_cls.return_value = pat
                grant = AsyncMock()
                grant.get_by_id.return_value = {"id": "g1", "patient_id": "p1", "doctor_id": "d1",
                                                "scope": ["reports"], "status": "active",
                                                "created_at": datetime.now(timezone.utc),
                                                "updated_at": datetime.now(timezone.utc)}
                grant.revoke.return_value = _grant(status="revoked")
                grant_cls.return_value = grant
                assert client.post("/api/v1/access/requests/req1/deny",
                                   headers={"Authorization": f"Bearer {_token('p1', 'p@t.com', 'patient')}"}).status_code == 200
                assert client.delete("/api/v1/access/grants/g1",
                                     headers={"Authorization": f"Bearer {_token('p1', 'p@t.com', 'patient')}"}).status_code == 204
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_wrong_patient_cannot_decide(self):
        app.dependency_overrides[get_current_user] = lambda: _user("other", "o@t.com", "patient", "O")
        try:
            with patch("app.access.router.AccessRequestRepository") as req_cls, \
                 patch("app.access.router.PatientRepository") as pat_cls:
                doc = {"id": "req1", "patient_id": "p1", "doctor_id": "d1", "scope": ["reports"],
                       "message": None, "status": "pending",
                       "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
                       "decided_at": None}
                req = AsyncMock()
                req.get_by_id.return_value = doc
                req_cls.return_value = req
                pat = AsyncMock()
                other = _patient_prof(pid="other", uid="other")
                pat.get_by_user_id.return_value = other
                pat_cls.return_value = pat
                r = client.post("/api/v1/access/requests/req1/approve", json={"expires_in_days": 7},
                                headers={"Authorization": f"Bearer {_token('other', 'o@t.com', 'patient')}"})
                assert r.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestGrantHelper:
    def test_expired_grant_denied(self):
        import asyncio

        async def run():
            from app.access import grants as g

            past = datetime.now(timezone.utc) - timedelta(days=1)
            with patch.object(g.AccessGrantRepository, "get_active",
                              new=AsyncMock(return_value=_grant(expires=past))), \
                 patch.object(g.AccessGrantRepository, "mark_expired",
                              new=AsyncMock()) as mark:
                assert await _REAL_GET_GRANT("p1", "d1") is None
                mark.assert_called_once()

        asyncio.run(run())

    def test_revoked_grant_denied(self):
        import asyncio

        async def run():
            from app.access import grants as g

            with patch.object(g.AccessGrantRepository, "get_active",
                              new=AsyncMock(return_value=None)):
                assert await _REAL_GET_GRANT("p1", "d1") is None

        asyncio.run(run())

    def test_scope_mismatch_denied(self):
        import asyncio

        async def run():
            from app.access import grants as g

            future = datetime.now(timezone.utc) + timedelta(days=5)
            with patch.object(g.AccessGrantRepository, "get_active",
                              new=AsyncMock(return_value=_grant(expires=future, scope=["reports"]))):
                assert await _REAL_GET_GRANT("p1", "d1", scope="history") is None
                assert await _REAL_GET_GRANT("p1", "d1", scope="reports") is not None

        asyncio.run(run())

    def test_require_active_grant_404(self):
        import asyncio
        from fastapi import HTTPException

        async def run():
            with patch("app.access.grants.get_active_grant", new=AsyncMock(return_value=None)):
                # Re-import real implementation bypassing the patched attribute.
                import importlib
                import app.access.grants as gmod

                real = _REAL_REQUIRE_GRANT
                try:
                    await real("p1", "d1")
                    raise AssertionError("should have raised")
                except HTTPException as exc:
                    assert exc.status_code == 404

        asyncio.run(run())


class TestEnforcementNegatives:
    """Each doctor path denies without a grant (grant gate raises)."""

    from contextlib import contextmanager

    @staticmethod
    @contextmanager
    def _deny():
        from fastapi import HTTPException

        async def _raise404(*a, **k):
            raise HTTPException(status_code=404, detail="Patient not found")

        async def _raise403(*a, **k):
            raise HTTPException(status_code=403, detail="No active access grant")

        with patch("app.access.grants.require_active_grant", new=_raise404), \
             patch("app.access.grants.require_grant_or_403", new=_raise403):
            yield

    def _doctor(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr")

    def test_patient_detail_404(self):
        self._doctor()
        try:
            with self._deny(), patch("app.patients.router.PatientRepository") as repo_cls:
                inst = AsyncMock()
                prof = _patient_prof()
                prof.user_id = "p1"
                inst.get_by_patient_id.return_value = prof
                repo_cls.return_value = inst
                r = client.get("/api/v1/patients/p1",
                               headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"})
                assert r.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_report_get_404(self):
        self._doctor()
        try:
            with self._deny(), \
                 patch("app.reports.services.report_service.ReportRepository") as repo_cls:
                rep = AsyncMock()
                rep.id = "r1"
                rep.patient_id = "p1"
                inst = AsyncMock()
                inst.get_by_id.return_value = rep
                repo_cls.return_value = inst
                r = client.get("/api/v1/reports/r1",
                               headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"})
                assert r.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_history_404(self):
        self._doctor()
        try:
            with self._deny():
                r = client.get("/api/v1/history/patient/p1",
                               headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"})
                assert r.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_prescription_create_403(self):
        self._doctor()
        try:
            with self._deny(), patch("app.prescriptions.router.PatientRepository.get_by_patient_id", new_callable=AsyncMock) as mock_get_patient:
                from unittest.mock import MagicMock
                from datetime import datetime, timezone
                mock_patient = MagicMock()
                mock_patient.patient_code = "PAT-ABC12"
                mock_patient.allow_prescriptions = False  # Patient has disabled prescriptions
                mock_patient.emergency_token = None
                mock_patient.id = "p1"
                mock_patient.user_id = "p1"
                mock_patient.patient_id = "p1"
                mock_patient.created_at = datetime.now(timezone.utc)
                mock_patient.updated_at = datetime.now(timezone.utc)
                mock_get_patient.return_value = mock_patient
                
                r = client.post("/api/v1/prescriptions",
                                json={"patient_id": "p1", "items": [
                                    {"medicine_name": "A", "dosage": "1", "frequency": "OD", "duration": "3 days"}]},
                                headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"})
                assert r.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_unverified_doctor_still_403_first(self):
        # Verification precedes grants: unverified -> 403 even with grants denied.
        self._doctor()
        try:
            prof = AsyncMock()
            prof.is_verified = False
            prof.verification_status = "pending"
            with self._deny(), patch(
                    "app.database.repositories.doctor_repository.DoctorRepository.get_by_user_id",
                    new=AsyncMock(return_value=prof)):
                r = client.get("/api/v1/patients/",
                               headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"})
                assert r.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestAudit:
    def test_doctor_read_writes_audit(self):
        self._doctor_with_grant()
        try:
            with patch("app.reports.services.report_service.ReportRepository") as repo_cls, \
                 patch("app.database.repositories.audit_repository.AuditRepository") as audit_cls:
                rep = AsyncMock()
                rep.id = "r1"
                rep.patient_id = "p1"
                rep.title = "Blood Test"
                rep.category = "Blood Test"
                rep.doctor_id = None
                rep.original_text = None
                rep.extracted_text = "Hemoglobin 14 g/dL"
                rep.extraction_method = "text"
                rep.entities = []
                rep.lab_results = []
                rep.nlp_status = "completed"
                rep.ai_status = "not_started"
                rep.ai_interpretation = None
                rep.important_findings = []
                rep.simplified_explanation = None
                rep.glossary = {}
                rep.metadata = {}
                rep.status = "completed"
                rep.error_message = None
                rep.file_path = None
                rep.file_name = "t.txt"
                rep.file_size = 10
                rep.ocr_used = False
                rep.nlp_processed_at = None
                rep.ai_processed_at = None
                rep.processed_at = datetime.now(timezone.utc)
                rep.created_at = datetime.now(timezone.utc)
                rep.updated_at = datetime.now(timezone.utc)
                inst = AsyncMock()
                inst.get_by_id.return_value = rep
                repo_cls.return_value = inst
                audit = AsyncMock()
                audit_cls.return_value = audit
                r = client.get("/api/v1/reports/r1",
                               headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"})
                assert r.status_code == 200
                assert audit.log.await_count >= 1
                kwargs = audit.log.await_args.kwargs
                assert kwargs["actor_id"] == "d1" and kwargs["patient_id"] == "p1"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def _doctor_with_grant(self):
        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr")

    def test_patient_sees_audit(self):
        app.dependency_overrides[get_current_user] = lambda: _user("p1", "p@t.com", "patient", "P")
        try:
            with patch("app.audit.router.PatientRepository") as pat_cls, \
                 patch("app.audit.router.AuditRepository") as audit_cls:
                pat = AsyncMock()
                pat.get_by_user_id.return_value = _patient_prof()
                pat_cls.return_value = pat
                audit = AsyncMock()
                audit.for_patient.return_value = []
                audit_cls.return_value = audit
                assert client.get("/api/v1/audit/me",
                                  headers={"Authorization": f"Bearer {_token('p1', 'p@t.com', 'patient')}"}).status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_admin_audit_search_and_doctor_forbidden(self):
        app.dependency_overrides[get_current_user] = lambda: _user("a1", "a@t.com", "admin", "Admin")
        try:
            with patch("app.audit.router.AuditRepository") as audit_cls:
                audit = AsyncMock()
                audit.search.return_value = []
                audit_cls.return_value = audit
                assert client.get("/api/v1/audit/", params={"action": "read"},
                                  headers={"Authorization": f"Bearer {_token('a1', 'a@t.com', 'admin')}"}).status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        app.dependency_overrides[get_current_user] = lambda: _user("d1", "d@t.com", "doctor", "Dr")
        try:
            assert client.get("/api/v1/audit/",
                              headers={"Authorization": f"Bearer {_token('d1', 'd@t.com', 'doctor')}"}).status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)
