"""Audit helper (Phase 3): fire-and-forget PHI access logging."""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("healthcare_system")


async def log_access(
    actor_id: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Never raises: audit must not break clinical flows."""
    try:
        from app.database.repositories.audit_repository import AuditRepository

        await AuditRepository().log(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            patient_id=patient_id,
            ip=ip,
            user_agent=user_agent,
        )
    except Exception as exc:
        logger.warning(f"Audit log failed (non-fatal): {exc}")


def client_info(request) -> tuple[Optional[str], Optional[str]]:
    """Best-effort (ip, user_agent) from a Starlette request (may be None)."""
    try:
        ip = request.client.host if request and request.client else None
    except Exception:
        ip = None
    try:
        ua = request.headers.get("user-agent") if request else None
    except Exception:
        ua = None
    return ip, ua
