from typing import Optional, Any
from app.database.collections import PRESCRIPTIONS
from app.database.repositories.base_repository import BaseRepository
from app.models.prescription import PrescriptionInDB


class PrescriptionRepository(BaseRepository):
    def __init__(self):
        super().__init__(PRESCRIPTIONS)

    async def create_prescription(self, patient_id: str, doctor_id: str, **kwargs) -> PrescriptionInDB:
        data = {
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            **kwargs,
        }
        created = await self.create(data)
        return PrescriptionInDB(**created)

    async def get_by_id(self, prescription_id: str) -> Optional[PrescriptionInDB]:
        doc = await super().get_by_id(prescription_id)
        return PrescriptionInDB(**doc) if doc else None

    async def get_by_token(self, token: str) -> Optional[PrescriptionInDB]:
        doc = await self.get_by_field("verification_token", token)
        return PrescriptionInDB(**doc) if doc else None

    async def get_by_patient_since(self, patient_id: str, since, limit: int = 100) -> list[PrescriptionInDB]:
        """Prescriptions for reminder scans (created_at >= since)."""
        cursor = self.collection.find({"patient_id": patient_id, "created_at": {"$gte": since}})
        docs = await cursor.to_list(length=limit)
        return [PrescriptionInDB(**doc) for doc in docs]

    async def list_by_patient(self, patient_id: str, skip: int = 0, limit: int = 20) -> list[PrescriptionInDB]:
        cursor = self.collection.find({"patient_id": patient_id})
        cursor.skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [PrescriptionInDB(**doc) for doc in docs]

    async def list_by_doctor(self, doctor_id: str, skip: int = 0, limit: int = 20) -> list[PrescriptionInDB]:
        cursor = self.collection.find({"doctor_id": doctor_id})
        cursor.skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [PrescriptionInDB(**doc) for doc in docs]

    async def update_prescription(self, prescription_id: str, **kwargs) -> Optional[PrescriptionInDB]:
        kwargs.pop("id", None)
        kwargs.pop("patient_id", None)
        kwargs.pop("doctor_id", None)
        kwargs.pop("created_at", None)
        updated = await self.update(prescription_id, kwargs)
        return PrescriptionInDB(**updated) if updated else None
