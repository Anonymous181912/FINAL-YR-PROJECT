"""End-to-end prescription portal flow against the real API and MongoDB.

These tests use real HTTP calls (TestClient), real JWTs from /auth/login and
real database writes -- no repository or dependency mocks. They skip when
MongoDB is not reachable so the mocked unit suite still runs anywhere.

Covers the reported bug: a doctor saves a draft, issues it, and only the
target patient sees it (plus the issue notification).
"""

import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import get_password_hash
from app.database.collections import (
    ACCESS_GRANTS,
    ACCESS_REQUESTS,
    AUDIT_LOGS,
    DOCTOR_PROFILES,
    NOTIFICATIONS,
    PATIENT_PROFILES,
    PRESCRIPTIONS,
    REFRESH_TOKENS,
    USERS,
)
from app.main import app


@pytest.fixture(autouse=True)
def _verified_doctor_default():
    """Shadow conftest's mock: this module needs real doctor verification."""
    yield


@pytest.fixture(autouse=True)
def _allow_grants_default():
    """Shadow conftest's mock: this module needs the real consent-grant gate."""
    yield


def _mongo_available() -> bool:
    async def _ping() -> bool:
        from motor.motor_asyncio import AsyncIOMotorClient

        client = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=2000)
        try:
            await client.admin.command("ping")
            return True
        except Exception:
            return False
        finally:
            client.close()

    return asyncio.run(_ping())


def _new_id() -> str:
    return str(uuid.uuid4())


async def _seed() -> dict:
    from motor.motor_asyncio import AsyncIOMotorClient

    suffix = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    password = "E2ePass1234"
    hashed = get_password_hash(password)

    doctor_id = _new_id()
    patient_one_id = _new_id()
    patient_two_id = _new_id()
    users = [
        {
            "id": doctor_id,
            "email": f"e2e-doctor-{suffix}@example.com",
            "hashed_password": hashed,
            "role": "doctor",
            "full_name": "E2E Doctor",
            "is_active": True,
            "failed_login_attempts": 0,
            "locked_until": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": patient_one_id,
            "email": f"e2e-patient-one-{suffix}@example.com",
            "hashed_password": hashed,
            "role": "patient",
            "full_name": "E2E Patient One",
            "is_active": True,
            "failed_login_attempts": 0,
            "locked_until": None,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": patient_two_id,
            "email": f"e2e-patient-two-{suffix}@example.com",
            "hashed_password": hashed,
            "role": "patient",
            "full_name": "E2E Patient Two",
            "is_active": True,
            "failed_login_attempts": 0,
            "locked_until": None,
            "created_at": now,
            "updated_at": now,
        },
    ]
    patient_codes = [f"E2EONE{suffix.upper()}", f"E2ETWO{suffix.upper()}"]
    patient_profiles = [
        {
            "id": _new_id(),
            "user_id": patient_one_id,
            "patient_id": patient_one_id,
            "full_name": "E2E Patient One",
            "patient_code": patient_codes[0],
            "allow_prescriptions": True,
            "allergies": [],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": _new_id(),
            "user_id": patient_two_id,
            "patient_id": patient_two_id,
            "full_name": "E2E Patient Two",
            "patient_code": patient_codes[1],
            "allow_prescriptions": True,
            "allergies": [],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
    ]
    doctor_profile = {
        "id": _new_id(),
        "user_id": doctor_id,
        "doctor_id": doctor_id,
        "full_name": "E2E Doctor",
        "specialization": "General",
        "license_number": f"E2E-LIC-{suffix}",
        "is_verified": True,
        "verification_status": "approved",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }

    client = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=3000)
    db = client[settings.mongodb_db_name]
    try:
        await db[USERS].insert_many(users)
        await db[DOCTOR_PROFILES].insert_one(doctor_profile)
        await db[PATIENT_PROFILES].insert_many(patient_profiles)
    finally:
        client.close()

    return {
        "suffix": suffix,
        "password": password,
        "emails": {
            "doctor": users[0]["email"],
            "patient_one": users[1]["email"],
            "patient_two": users[2]["email"],
        },
        "user_ids": [u["id"] for u in users],
        "doctor_id": doctor_id,
        "patient_ids": [patient_one_id, patient_two_id],
        "patient_codes": patient_codes,
    }


async def _cleanup(seed: dict) -> None:
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=3000)
    db = client[settings.mongodb_db_name]
    try:
        await db[PRESCRIPTIONS].delete_many({"doctor_id": seed["doctor_id"]})
        await db[NOTIFICATIONS].delete_many({"user_id": {"$in": seed["patient_ids"]}})
        await db[REFRESH_TOKENS].delete_many({"user_id": {"$in": seed["user_ids"]}})
        await db[AUDIT_LOGS].delete_many({
            "$or": [
                {"actor_id": {"$in": seed["user_ids"]}},
                {"patient_id": {"$in": seed["patient_ids"]}},
            ]
        })
        await db[ACCESS_GRANTS].delete_many({
            "$or": [
                {"patient_id": {"$in": seed["patient_ids"]}},
                {"doctor_id": seed["doctor_id"]},
            ]
        })
        await db[ACCESS_REQUESTS].delete_many({
            "$or": [
                {"patient_id": {"$in": seed["patient_ids"]}},
                {"doctor_id": seed["doctor_id"]},
            ]
        })
        await db[PATIENT_PROFILES].delete_many({"user_id": {"$in": seed["patient_ids"]}})
        await db[DOCTOR_PROFILES].delete_many({"user_id": seed["doctor_id"]})
        await db[USERS].delete_many({"id": {"$in": seed["user_ids"]}})
    finally:
        client.close()


def _login(client: TestClient, email: str, password: str, portal: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password, "portal": portal},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.skipif(not _mongo_available(), reason="MongoDB not reachable")
def test_doctor_draft_issue_and_patient_isolation_real_api():
    seed = asyncio.run(_seed())
    try:
        with TestClient(app) as client:
            doctor_token = _login(client, seed["emails"]["doctor"], seed["password"], "doctor")

            # Root cause guard: the slash-less URL 307s to an absolute URL.
            redirect = client.post(
                "/api/v1/prescriptions",
                json={"patient_id": seed["patient_ids"][0], "items": [{"medicine_name": "X", "dosage": "1", "frequency": "OD", "duration": "1 day"}]},
                headers=_auth(doctor_token),
                follow_redirects=False,
            )
            assert redirect.status_code == 307
            assert redirect.headers["location"].endswith("/api/v1/prescriptions/")

            # Doctor looks the patient up by patient_code.
            search = client.get(
                "/api/v1/patients/search",
                params={"q": seed["patient_codes"][0]},
                headers=_auth(doctor_token),
            )
            assert search.status_code == 200, search.text
            matches = search.json()
            assert len(matches) == 1
            assert matches[0]["patient_id"] == seed["patient_ids"][0]
            canonical_patient_id = matches[0]["patient_id"]

            # Save draft through the exact URL the frontend now uses.
            created = client.post(
                "/api/v1/prescriptions/",
                json={
                    "patient_id": canonical_patient_id,
                    "diagnosis_notes": "E2E draft",
                    "items": [
                        {
                            "medicine_name": "Paracetamol",
                            "dosage": "500mg",
                            "frequency": "OD",
                            "duration": "3 days",
                        }
                    ],
                },
                headers=_auth(doctor_token),
                follow_redirects=False,
            )
            assert created.status_code == 201, created.text
            draft = created.json()
            assert draft["status"] == "draft"
            assert draft["patient_id"] == canonical_patient_id
            rx_id = draft["id"]

            patient_one_token = _login(client, seed["emails"]["patient_one"], seed["password"], "patient")
            patient_two_token = _login(client, seed["emails"]["patient_two"], seed["password"], "patient")

            # Draft must stay invisible to the patient.
            before = client.get("/api/v1/prescriptions/patient", headers=_auth(patient_one_token))
            assert before.status_code == 200
            assert rx_id not in [rx["id"] for rx in before.json()]

            # Issue to patient.
            issued = client.post(
                f"/api/v1/prescriptions/{rx_id}/issue",
                headers=_auth(doctor_token),
                follow_redirects=False,
            )
            assert issued.status_code == 200, issued.text
            assert issued.json()["status"] == "issued"

            # Target patient sees and can open it.
            after = client.get("/api/v1/prescriptions/patient", headers=_auth(patient_one_token))
            assert after.status_code == 200
            assert rx_id in [rx["id"] for rx in after.json()]
            detail = client.get(f"/api/v1/prescriptions/{rx_id}", headers=_auth(patient_one_token))
            assert detail.status_code == 200
            assert detail.json()["id"] == rx_id

            # Other patient must not see it.
            other = client.get("/api/v1/prescriptions/patient", headers=_auth(patient_two_token))
            assert other.status_code == 200
            assert rx_id not in [rx["id"] for rx in other.json()]

            # Issue created the patient notification.
            notifications = client.get("/api/v1/notifications/", headers=_auth(patient_one_token))
            assert notifications.status_code == 200
            assert any(
                n.get("kind") == "prescription_issued" and n.get("ref_id") == rx_id
                for n in notifications.json()
            )
    finally:
        asyncio.run(_cleanup(seed))
