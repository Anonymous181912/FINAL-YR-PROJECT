"""Shared pytest fixtures (Phase 0).

- Disables slowapi rate limiting for the test suite (all tests use the same
  ``testclient`` IP, so per-minute budgets would otherwise flake the suite).
- Clears FastAPI dependency overrides after each test to avoid leakage.
- Provides a verified-doctor default for ``DoctorRepository.get_by_user_id``
  so pre-existing doctor tests (which override ``get_current_user``) keep
  passing under the new verification gate. Negative tests patch this again
  with unverified/None profiles.
"""

from unittest.mock import AsyncMock, patch

import pytest


def _verified_doctor_profile(user_id="doctor-user-123"):
    from datetime import datetime, timezone

    profile = AsyncMock()
    profile.id = "doctor-profile-123"
    profile.user_id = user_id
    profile.doctor_id = user_id
    profile.full_name = "Dr. Test"
    profile.specialization = "General"
    profile.contact_phone = None
    profile.contact_email = None
    profile.license_number = "LIC-123"
    profile.is_verified = True
    profile.verification_status = "approved"
    profile.is_active = True
    profile.created_at = datetime.now(timezone.utc)
    profile.updated_at = datetime.now(timezone.utc)
    return profile


@pytest.fixture(autouse=True)
def _verified_doctor_default():
    with patch(
        "app.database.repositories.doctor_repository.DoctorRepository.get_by_user_id",
        new=AsyncMock(return_value=_verified_doctor_profile()),
    ):
        yield


@pytest.fixture(autouse=True)
def _disable_rate_limiting():
    from app.main import app

    limiter = getattr(app.state, "limiter", None)
    if limiter is not None:
        prev = getattr(limiter, "enabled", True)
        limiter.enabled = False
        try:
            yield
        finally:
            limiter.enabled = prev
    else:
        yield


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    from app.main import app

    try:
        yield
    finally:
        app.dependency_overrides.clear()


def _allow_grant(*args, **kwargs):
    grant = AsyncMock()
    grant.id = "grant-allow"
    grant.patient_id = args[0] if args else "p1"
    grant.doctor_id = args[1] if len(args) > 1 else "d1"
    grant.scope = ["reports", "prescriptions", "history"]
    grant.status = "active"
    grant.expires_at = None
    return grant


@pytest.fixture(autouse=True)
def _allow_grants_default():
    """Phase 3: pre-existing tests predate consent grants, so the grant
    gate allows by default. Phase-3 tests re-patch these with allow/deny
    cases explicitly (nested patches win over this outer one)."""
    import asyncio

    def _async_allow(*args, **kwargs):
        async def _inner():
            return _allow_grant(*args, **kwargs)

        return _inner()

    async def _canonical(patient_repo, patient_id):
        return patient_id

    async def _granted_ids(doctor_id):
        return ["p1", "patient-1", "patient-user-123", "pa", "pb"]

    with patch("app.access.grants.require_active_grant",
               new=_async_allow), \
         patch("app.access.grants.require_grant_or_403",
               new=_async_allow), \
         patch("app.access.grants.get_active_grant",
               new=_async_allow), \
         patch("app.access.grants.granted_patient_ids",
               new=_granted_ids), \
         patch("app.access.grants.canonical_patient_id",
               new=_canonical):
        yield
