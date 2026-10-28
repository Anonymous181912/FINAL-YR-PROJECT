"""Create three synthetic dated blood reports for a living demo trend patient.

Usage (PowerShell, from the ``backend`` directory):
    python scripts/seed_demo_trends.py

The script is safe to re-run: the demo user, profile and three fixed report ids
are upserted. It never touches any other patient's data and does not create
uploaded files.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEMO_EMAIL = "demo.trends@example.com"
DEMO_PASSWORD = "DemoTrends123!"
DEMO_NAME = "Trend Demo Patient"

REPORTS = [
    {
        "id": "demo-trends-report-2026-01",
        "date": "2026-01-12",
        "title": "Blood Test - Trend Demo 12 Jan 2026",
        "rows": [
            ("Fasting Glucose", "95", "mg/dL", "70 - 100"),
            ("Post Prandial Glucose", "132", "mg/dL", "70 - 140"),
            ("Haemoglobin", "13.8", "g/dL", "13 - 17"),
            ("MCV", "88", "fL", "81 - 101"),
            ("Creatinine", "1.4", "mg/dL", "0.7 - 1.3"),
            ("Total Cholesterol", "180", "mg/dL", "125 - 200"),
        ],
    },
    {
        "id": "demo-trends-report-2026-04",
        "date": "2026-04-10",
        "title": "Blood Test - Trend Demo 10 Apr 2026",
        "rows": [
            ("Fasting Glucose", "112", "mg/dL", "70 - 100"),
            ("Post Prandial Glucose", "158", "mg/dL", "70 - 140"),
            ("Haemoglobin", "13.2", "g/dL", "13 - 17"),
            ("MCV", "87", "fL", "81 - 101"),
            ("Creatinine", "1.2", "mg/dL", "0.7 - 1.3"),
            ("Total Cholesterol", "205", "mg/dL", "125 - 200"),
        ],
    },
    {
        "id": "demo-trends-report-2026-07",
        "date": "2026-07-10",
        "title": "Blood Test - Trend Demo 10 Jul 2026",
        "rows": [
            ("Fasting Glucose", "128", "mg/dL", "70 - 100"),
            ("Post Prandial Glucose", "171", "mg/dL", "70 - 140"),
            ("Haemoglobin", "12.6", "g/dL", "13 - 17"),
            ("MCV", "86", "fL", "81 - 101"),
            ("Creatinine", "1.0", "mg/dL", "0.7 - 1.3"),
            ("Total Cholesterol", "190", "mg/dL", "125 - 200"),
        ],
    },
]


def _report_text(report: dict) -> str:
    day, month, year = report["date"].split("-")[2], report["date"].split("-")[1], report["date"].split("-")[0]
    lines = [f"Collection Date : {day}/{month}/{year}", "Blood Test Report", ""]
    for name, value, unit, ref in report["rows"]:
        lines.append(f"{name} {value} {unit} ({ref})")
    return "\n".join(lines) + "\n"


async def seed_demo_trends() -> dict:
    from app.core.security import get_password_hash
    from app.database.connection import close_mongo_connection, connect_to_mongo
    from app.database.repositories.patient_repository import PatientRepository
    from app.database.repositories.user_repository import UserRepository
    from app.database.collections import REPORTS as REPORTS_COLLECTION
    from app.database.connection import get_database
    from app.reports.services.lab_parser import parse_lab_results
    from app.reports.services.report_service import ReportService
    from app.reports.services.trend_service import enrich_lab_results

    await connect_to_mongo()
    try:
        users = UserRepository()
        user = await users.get_by_email(DEMO_EMAIL)
        created_user = False
        if user is None:
            user = await users.create_user(
                email=DEMO_EMAIL,
                hashed_password=get_password_hash(DEMO_PASSWORD),
                role="patient",
                full_name=DEMO_NAME,
            )
            created_user = True
        elif user.role != "patient":
            raise SystemExit(
                f"{DEMO_EMAIL} exists with role '{user.role}', expected 'patient'."
            )
        else:
            await users.set_password(user.id, get_password_hash(DEMO_PASSWORD))

        patients = PatientRepository()
        profile = await patients.get_by_user_id(user.id)
        if profile is None:
            profile = await patients.create_profile(
                user_id=user.id,
                full_name=DEMO_NAME,
                patient_id=user.id,
                date_of_birth=datetime(1990, 5, 15),
                gender="female",
                contact_email=DEMO_EMAIL,
            )
        patient_key = profile.patient_id or profile.user_id or profile.id or user.id

        collection = get_database()[REPORTS_COLLECTION]
        now = datetime.now(timezone.utc)
        saved = []
        for item in REPORTS:
            text = _report_text(item)
            report_date = datetime.fromisoformat(item["date"] + "T09:00:00+00:00")
            labs = parse_lab_results(text, gender="female")
            labs = enrich_lab_results(
                labs,
                report_id=item["id"],
                report_text=text,
                created_at=report_date,
            )
            doc = {
                "id": item["id"],
                "patient_id": patient_key,
                "doctor_id": None,
                "category": "Blood Test",
                "title": item["title"],
                "original_text": text,
                "extracted_text": text,
                "extraction_method": "text",
                "entities": ReportService._lab_measurement_entities(labs),
                "lab_results": labs,
                "nlp_status": "completed",
                "ai_status": "not_started",
                "ai_interpretation": None,
                "important_findings": [],
                "simplified_explanation": None,
                "glossary": {},
                "metadata": {"seed": "demo_trends_v1"},
                "status": "completed",
                "error_message": None,
                "file_path": None,
                "file_name": f"demo_trends_{item['date']}.txt",
                "file_size": len(text.encode("utf-8")),
                "ocr_used": False,
                "nlp_processed_at": now,
                "ai_processed_at": None,
                "processed_at": now,
                "created_at": report_date,
                "updated_at": now,
            }
            await collection.update_one({"id": item["id"]}, {"$set": doc}, upsert=True)
            saved.append({"id": item["id"], "date": item["date"], "lab_values": len(labs)})

        return {
            "created_user": created_user,
            "user_id": user.id,
            "patient_id": patient_key,
            "reports": saved,
        }
    finally:
        await close_mongo_connection()


async def main() -> None:
    result = await seed_demo_trends()
    print(f"Demo patient ready: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    print(f"  user_id={result['user_id']} patient_id={result['patient_id']}")
    for item in result["reports"]:
        print(f"  {item['id']} | {item['date']} | labs={item['lab_values']}")
    print(f"User created: {result['created_user']}")


if __name__ == "__main__":
    asyncio.run(main())
