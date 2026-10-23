from typing import Optional
from app.database.collections import PATIENT_PROFILES
from app.database.repositories.base_repository import BaseRepository
from app.models.patient import PatientInDB


class PatientRepository(BaseRepository):
    def __init__(self):
        super().__init__(PATIENT_PROFILES)

    async def create_profile(self, user_id: str, full_name: str, **kwargs) -> PatientInDB:
        data = {
            "user_id": user_id,
            # Reports/prescriptions reference patients by the user UUID, so the
            # profile carries the same value as its canonical patient_id.
            "patient_id": kwargs.pop("patient_id", user_id),
            "full_name": full_name,
            **kwargs,
        }
        created = await self.create(data)
        return PatientInDB(**created)

    async def get_by_user_id(self, user_id: str) -> Optional[PatientInDB]:
        doc = await self.get_by_field("user_id", user_id)
        return PatientInDB(**doc) if doc else None

    async def get_by_patient_id(self, patient_id: str) -> Optional[PatientInDB]:
        # Accept the canonical patient_id, the owning user id, or the profile
        # document id: callers (history, prescriptions, dossier links) use
        # whichever identifier they have on hand.
        doc = await self.get_by_field("patient_id", patient_id)
        if doc:
            return PatientInDB(**doc)
        doc = await self.get_by_field("user_id", patient_id)
        if doc:
            return PatientInDB(**doc)
        doc = await self.get_by_id(patient_id)
        return PatientInDB(**doc) if doc else None

    async def update_profile(self, patient_id: str, **kwargs) -> Optional[PatientInDB]:
        kwargs.pop("user_id", None)
        kwargs.pop("patient_id", None)
        kwargs.pop("id", None)
        updated = await self.update(patient_id, kwargs)
        return PatientInDB(**updated) if updated else None
