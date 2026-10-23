"""Central consent-grant checks (Phase 3).

Every doctor read/write path touching patient data MUST go through
``require_active_grant`` (reads: 404 without leaking existence) or
``require_grant_or_403`` (writes: 403 with an actionable message).
Admins bypass grants; patients never need them (own data only).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status

from app.database.repositories.access_repository import AccessGrantRepository
from app.models.access import AccessGrantInDB


def _now():
    return datetime.now(timezone.utc)


async def get_active_grant(
    patient_id: str, doctor_id: str, scope: str = "reports"
) -> Optional[AccessGrantInDB]:
    repo = AccessGrantRepository()
    grant = await repo.get_active(patient_id, doctor_id)
    if grant is None:
        return None
    if grant.expires_at is not None:
        exp = grant.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp <= _now():
            try:
                await repo.mark_expired(grant.id)
            except Exception:
                pass
            return None
    if scope not in (grant.scope or []) and "all" not in (grant.scope or []):
        return None
    return grant


async def require_active_grant(
    patient_id: str, doctor_id: str, scope: str = "reports"
) -> AccessGrantInDB:
    """Reads: 404 when there is no grant (same as 'not found')."""
    grant = await get_active_grant(patient_id, doctor_id, scope)
    if grant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return grant


async def require_grant_or_403(
    patient_id: str, doctor_id: str, scope: str = "reports"
) -> AccessGrantInDB:
    """Writes: 403 telling the doctor to request access first."""
    grant = await get_active_grant(patient_id, doctor_id, scope)
    if grant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active access grant for this patient. Ask the patient to approve your access request first.",
        )
    return grant


async def granted_patient_ids(doctor_id: str) -> list[str]:
    """Canonical patient ids this doctor may access (active, unexpired)."""
    repo = AccessGrantRepository()
    grants = await repo.list_active_for_doctor(doctor_id)
    ids: list[str] = []
    for g in grants:
        if g.expires_at is not None:
            exp = g.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp <= _now():
                try:
                    await repo.mark_expired(g.id)
                except Exception:
                    pass
                continue
        ids.append(g.patient_id)
    return ids


async def canonical_patient_id(patient_repo, patient_id: str) -> Optional[str]:
    """Resolve any patient identifier to the canonical id (history-service rule)."""
    try:
        profile = await patient_repo.get_by_patient_id(patient_id)
    except Exception:
        return None
    if profile is None:
        return None
    return profile.patient_id or profile.user_id or profile.id
