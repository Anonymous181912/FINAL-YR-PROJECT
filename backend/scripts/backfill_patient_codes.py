"""Backfill ``patient_code`` for existing patient profiles.

Usage (PowerShell, from the ``backend`` directory):
    python scripts/backfill_patient_codes.py

Assigns a unique ``PAT-XXXXX`` code to every patient profile that has no
code (missing, null, or blank). Safe to run repeatedly: a second run finds
nothing to update and reports ``updated=0``.
"""

import asyncio
import os
import random
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _generate_candidate() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"PAT-{suffix}"


async def backfill_patient_codes() -> dict:
    from app.database.connection import connect_to_mongo, close_mongo_connection
    from app.database.repositories.patient_repository import PatientRepository

    await connect_to_mongo()
    try:
        repo = PatientRepository()
        missing_query = {
            "$or": [
                {"patient_code": {"$exists": False}},
                {"patient_code": None},
                {"patient_code": ""},
            ]
        }
        docs = await repo.collection.find(missing_query).to_list(length=None)

        updated = 0
        for doc in docs:
            profile_id = doc.get("id")
            if not profile_id:
                continue

            code = None
            for _ in range(50):
                candidate = _generate_candidate()
                if not await repo.get_by_field("patient_code", candidate):
                    code = candidate
                    break
            if code is None:
                raise RuntimeError("Unable to generate a unique patient_code")

            await repo.update(profile_id, {"patient_code": code})
            updated += 1

        remaining = await repo.collection.count_documents(missing_query)
        return {"updated": updated, "remaining": remaining}
    finally:
        await close_mongo_connection()


async def main() -> None:
    result = await backfill_patient_codes()
    print(
        "Backfill complete: "
        f"updated={result['updated']} "
        f"remaining_without_code={result['remaining']}"
    )


if __name__ == "__main__":
    asyncio.run(main())
