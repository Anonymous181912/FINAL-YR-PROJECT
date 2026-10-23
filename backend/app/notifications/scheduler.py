"""Background reminder scheduler (Phase 2c).

An asyncio task started in the app lifespan. Every
``reminder_interval_hours`` it scans recent prescriptions and creates
in-app notifications for (a) upcoming follow-up visits and (b) medicine
courses about to finish. Email is best-effort and ONLY sent when SMTP is
configured; otherwise in-app notifications only (per spec).
"""

from __future__ import annotations

import asyncio
import logging
import re
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger("healthcare_system")

_DURATION_RE = re.compile(r"(?P<n>\d+)\s*(?P<u>days?|weeks?|months?|d|w|m)\b", re.IGNORECASE)


def parse_duration_days(text: str | None):
    """Parse '7 days' / '2 weeks' / '1 month' -> days (int) or None."""
    if not text:
        return None
    match = _DURATION_RE.search(text)
    if not match:
        return None
    n = int(match.group("n"))
    unit = match.group("u").lower()
    if unit.startswith("w"):
        return n * 7
    if unit.startswith("m") and not unit.startswith("d"):
        # 'm'/'month(s)'; plain 'd' handled below ('days' starts with 'd' too).
        if unit in ("m", "month", "months"):
            return n * 30
    return n


def _smtp_configured() -> bool:
    from app.core.config import settings

    return bool(settings.smtp_host and settings.smtp_from)


def send_email_best_effort(to_email: str, subject: str, body: str) -> bool:
    from app.core.config import settings

    if not _smtp_configured() or not to_email:
        return False
    try:
        msg = EmailMessage()
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)
        if settings.smtp_use_tls:
            server: smtplib.SMTP = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
            server.starttls()
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
        try:
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        finally:
            try:
                server.quit()
            except Exception:
                pass
        return True
    except Exception as exc:
        logger.warning(f"Reminder email failed (non-fatal): {exc}")
        return False


async def run_reminder_cycle(now: datetime | None = None) -> dict:
    """One scan cycle. Returns counts; safe to call in tests with mocks."""
    from app.core.config import settings
    from app.database.repositories.prescription_repository import PrescriptionRepository
    from app.database.repositories.patient_repository import PatientRepository
    from app.database.repositories.notification_repository import NotificationRepository

    if not settings.notifications_enabled:
        return {"skipped": True}

    now = now or datetime.now(timezone.utc)
    rx_repo = PrescriptionRepository()
    patient_repo = PatientRepository()
    notif_repo = NotificationRepository()
    created = 0

    # Recent prescriptions (last 120 days) via patient profiles is expensive;
    # instead scan the prescriptions collection directly.
    try:
        cursor = rx_repo.collection.find(
            {"created_at": {"$gte": now - timedelta(days=120)}}
        )
        docs = await cursor.to_list(length=2000)
    except Exception as exc:
        logger.warning(f"Reminder scan failed (non-fatal): {exc}")
        return {"created": 0, "error": str(exc)}

    for doc in docs:
        try:
            pid = doc.get("patient_id")
            rid = doc.get("id")
            # (a) follow-up within the next 3 days
            follow_up = doc.get("follow_up_date")
            if isinstance(follow_up, str):
                try:
                    follow_up = datetime.fromisoformat(follow_up)
                except ValueError:
                    follow_up = None
            if follow_up is not None:
                if follow_up.tzinfo is None:
                    follow_up = follow_up.replace(tzinfo=timezone.utc)
                delta = (follow_up - now).days
                if 0 <= delta <= 3:
                    key = f"followup:{rid}:{follow_up.date().isoformat()}"
                    notif = await notif_repo.create_if_absent(
                        key,
                        user_id=pid,
                        kind="follow_up",
                        title="Upcoming follow-up visit",
                        body=f"You have a follow-up visit scheduled on {follow_up.date().isoformat()}.",
                        link="/prescriptions",
                        ref_id=rid,
                    )
                    if notif:
                        created += 1
                        _maybe_email(pid, patient_repo, "Upcoming follow-up visit",
                                     f"Reminder: follow-up visit on {follow_up.date().isoformat()}.")
            # (b) medicine course ending within 2 days
            created_at = doc.get("created_at") or now
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at)
                except ValueError:
                    created_at = now
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            for item in doc.get("items") or []:
                days = parse_duration_days(item.get("duration") if isinstance(item, dict) else getattr(item, "duration", None))
                if not days:
                    continue
                end = created_at + timedelta(days=days)
                if 0 <= (end - now).days <= 2:
                    name = item.get("medicine_name") if isinstance(item, dict) else getattr(item, "medicine_name", "medicine")
                    key = f"medend:{rid}:{name}:{end.date().isoformat()}"
                    notif = await notif_repo.create_if_absent(
                        key,
                        user_id=pid,
                        kind="medication_end",
                        title="Medicine course finishing soon",
                        body=f"'{name}' course ends around {end.date().isoformat()}. Ask your doctor before stopping or repeating it.",
                        link="/prescriptions",
                        ref_id=rid,
                    )
                    if notif:
                        created += 1
        except Exception as exc:
            logger.warning(f"Reminder item failed (non-fatal): {exc}")
            continue
    return {"created": created}


def _maybe_email(patient_id: str, patient_repo, subject: str, body: str) -> None:
    """Fire-and-forget email; never raises, never blocks the cycle."""

    async def _send():
        try:
            patient = await patient_repo.get_by_patient_id(patient_id)
            email = getattr(patient, "contact_email", None) if patient else None
            if email:
                send_email_best_effort(email, subject, body)
        except Exception:
            pass

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_send())
    except RuntimeError:
        pass


def start_reminder_scheduler():
    """Start the background task. Returns a stop() callable for lifespan."""
    from app.core.config import settings

    if not settings.notifications_enabled:
        logger.info("Notifications disabled; reminder scheduler not started")
        return lambda: None

    stop_event = asyncio.Event()

    async def _loop():
        interval = max(1, settings.reminder_interval_hours) * 3600
        # First cycle shortly after startup so fresh installs remind promptly.
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=60)
            return
        except asyncio.TimeoutError:
            pass
        while not stop_event.is_set():
            try:
                await run_reminder_cycle()
            except Exception as exc:
                logger.warning(f"Reminder cycle failed (non-fatal): {exc}")
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning("No running loop; reminder scheduler not started")
        return lambda: None
    task = loop.create_task(_loop())

    def _stop():
        stop_event.set()
        task.cancel()

    return _stop
