"""Recompute ``lab_results`` for existing reports from their stored OCR text.

Usage (PowerShell, from the ``backend`` directory):
    python scripts/reparse_labs.py

Safety:
- Only reads ``extracted_text`` that is already stored on each report.
- Writes standardised ``lab_results`` (including report/date/unit metadata)
  plus the lab-derived measurement entities. Existing non-lab entities and the
  AI interpretation are left untouched.
- Patient exclusions and corrected values are preserved across reparses.
- Deterministic and idempotent: running it twice yields the same lab values.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _age_years(date_of_birth) -> float | None:
    if not date_of_birth:
        return None
    dob = date_of_birth
    if isinstance(dob, str):
        try:
            dob = datetime.fromisoformat(dob.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dob.tzinfo is None:
        dob = dob.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dob).days / 365.25


async def reparse_labs() -> dict:
    from app.database.connection import close_mongo_connection, connect_to_mongo
    from app.database.repositories.patient_repository import PatientRepository
    from app.database.repositories.report_repository import ReportRepository
    from app.reports.services.lab_parser import parse_lab_results
    from app.reports.services.reference_ranges import REFERENCE_RANGES
    from app.reports.services.report_service import ReportService
    from app.reports.services.trend_service import enrich_lab_results

    await connect_to_mongo()
    try:
        patients = PatientRepository()
        reports = ReportRepository()

        profiles = await patients.collection.find({}).to_list(length=None)
        by_patient: dict[str, dict] = {}
        for profile in profiles:
            for key in ("id", "user_id", "patient_id"):
                value = profile.get(key)
                if value:
                    by_patient.setdefault(value, profile)

        docs = await reports.collection.find({}).to_list(length=None)
        summary = {
            "scanned": len(docs),
            "with_text": 0,
            "without_text": 0,
            "reports_with_labs": 0,
            "total_values": 0,
            "reports": [],
        }
        for doc in docs:
            text = (doc.get("extracted_text") or "").strip()
            report_id = doc.get("id")
            if not text:
                summary["without_text"] += 1
                labs: list[dict] = []
            else:
                summary["with_text"] += 1
                profile = by_patient.get(doc.get("patient_id"))
                labs = parse_lab_results(
                    text,
                    gender=profile.get("gender") if profile else None,
                    age_years=_age_years(profile.get("date_of_birth")) if profile else None,
                )
                labs = enrich_lab_results(
                    labs,
                    report_id=report_id or "",
                    report_text=text,
                    created_at=doc.get("created_at"),
                    existing=doc.get("lab_results") or [],
                )

            # Keep the measurement entities in sync with the recomputed labs.
            # Existing non-lab entities are preserved; old lab-derived
            # measurement entities are replaced (not duplicated).
            existing_entities = doc.get("entities") or []
            lab_keys = set(REFERENCE_RANGES)
            kept_entities = [
                entity
                for entity in existing_entities
                if not (
                    entity.get("type") == "measurement"
                    and entity.get("normalized_text") in lab_keys
                )
            ]
            entities = [*kept_entities, *ReportService._lab_measurement_entities(labs)]

            if report_id:
                await reports.collection.update_one(
                    {"id": report_id},
                    {
                        "$set": {
                            "lab_results": labs,
                            "entities": entities,
                            "updated_at": datetime.now(timezone.utc),
                        }
                    },
                )
            if labs:
                summary["reports_with_labs"] += 1
                summary["total_values"] += len(labs)
            summary["reports"].append(
                {
                    "id": report_id,
                    "title": doc.get("title"),
                    "status": doc.get("status"),
                    "has_text": bool(text),
                    "lab_count": len(labs),
                    "tests": [lab.get("canonical_name") for lab in labs],
                }
            )

        return summary
    finally:
        await close_mongo_connection()


async def main() -> None:
    result = await reparse_labs()
    print("\nPer-report results:")
    for item in result["reports"]:
        tests = ", ".join(item["tests"]) if item["tests"] else "-"
        print(
            f"  {item['id']} | {item['title']!r} | status={item['status']} | "
            f"text={'yes' if item['has_text'] else 'no'} | labs={item['lab_count']} | {tests}"
        )
    print(
        "\nReparse complete: "
        f"scanned={result['scanned']} "
        f"with_text={result['with_text']} "
        f"without_text={result['without_text']} "
        f"reports_with_labs={result['reports_with_labs']} "
        f"total_lab_values={result['total_values']}"
    )


if __name__ == "__main__":
    asyncio.run(main())
