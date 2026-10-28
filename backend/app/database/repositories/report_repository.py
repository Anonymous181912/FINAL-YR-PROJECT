from typing import Optional, Any
from app.database.collections import REPORTS
from app.database.repositories.base_repository import BaseRepository
from app.models.report import ReportInDB


class ReportRepository(BaseRepository):
    def __init__(self):
        super().__init__(REPORTS)

    async def create_report(self, patient_id: str, category: str, title: str, **kwargs) -> ReportInDB:
        data = {
            "patient_id": patient_id,
            "category": category,
            "title": title,
            **kwargs,
        }
        created = await self.create(data)
        return ReportInDB(**created)

    async def get_by_id(self, report_id: str) -> Optional[ReportInDB]:
        doc = await super().get_by_id(report_id)
        return ReportInDB(**doc) if doc else None

    async def list_by_patient(self, patient_id: str, skip: int = 0, limit: int = 20) -> list[ReportInDB]:
        cursor = self.collection.find({"patient_id": patient_id})
        cursor.skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [ReportInDB(**doc) for doc in docs]

    async def list_all_for_patients(self, patient_ids: list[str]) -> list[ReportInDB]:
        """All reports for any of the patient/user ids (trend history)."""
        ids = [value for value in dict.fromkeys(patient_ids) if value]
        if not ids:
            return []
        cursor = self.collection.find({"patient_id": {"$in": ids}})
        docs = await cursor.to_list(length=None)
        return [ReportInDB(**doc) for doc in docs]

    async def update_nlp(self, report_id: str, entities: list[dict], nlp_status: str) -> Optional[ReportInDB]:
        from datetime import datetime, timezone
        data = {
            "entities": entities,
            "nlp_status": nlp_status,
            "nlp_processed_at": datetime.now(timezone.utc),
        }
        updated = await self.update(report_id, data)
        return ReportInDB(**updated) if updated else None

    async def update_processing(self, report_id: str, **fields) -> Optional[ReportInDB]:
        """Phase 4d: background worker writes pipeline results onto a pending doc."""
        fields.pop("id", None)
        fields.pop("patient_id", None)
        fields.pop("created_at", None)
        updated = await self.update(report_id, fields)
        return ReportInDB(**updated) if updated else None

    async def update_ai(self, report_id: str, ai_interpretation: dict[str, Any], ai_status: str) -> Optional[ReportInDB]:
        from datetime import datetime, timezone
        data = {
            "ai_interpretation": ai_interpretation,
            "ai_status": ai_status,
            "ai_processed_at": datetime.now(timezone.utc),
        }
        updated = await self.update(report_id, data)
        return ReportInDB(**updated) if updated else None
