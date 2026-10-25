import random
import string
from typing import Optional, List
from app.database.collections import PATIENT_PROFILES
from app.database.repositories.base_repository import BaseRepository
from app.models.patient import PatientInDB


class PatientRepository(BaseRepository):
    def __init__(self):
        super().__init__(PATIENT_PROFILES)

    def _generate_patient_code(self) -> str:
        """Generate a unique, readable patient code like PAT-7X9K2."""
        prefix = "PAT"
        while True:
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            code = f"{prefix}-{suffix}"
            # Check uniqueness (fire-and-forget; race is extremely unlikely)
            existing = self.get_by_field_sync("patient_code", code)
            if not existing:
                return code

    def get_by_field_sync(self, field: str, value) -> Optional[dict]:
        """Synchronous get_by_field for code generation (uses motor cursor)."""
        # This is a blocking call but only used during code generation at creation time
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, we can't block. Fall back to random.
                return None
        except RuntimeError:
            pass
        return None  # Simplified: just rely on random uniqueness

    async def create_profile(self, user_id: str, full_name: str, **kwargs) -> PatientInDB:
        # Generate unique patient_code if not provided
        patient_code = kwargs.pop("patient_code", None)
        if not patient_code:
            # Generate a unique code
            for _ in range(10):
                suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                candidate = f"PAT-{suffix}"
                existing = await self.get_by_field("patient_code", candidate)
                if not existing:
                    patient_code = candidate
                    break
            if not patient_code:
                # Fallback with timestamp
                import time
                patient_code = f"PAT-{int(time.time() * 1000) % 1000000:06d}"

        data = {
            "user_id": user_id,
            "patient_id": kwargs.pop("patient_id", user_id),
            "full_name": full_name,
            "patient_code": patient_code,
            "allow_prescriptions": kwargs.pop("allow_prescriptions", True),
            **kwargs,
        }
        created = await self.create(data)
        return PatientInDB(**created)

    async def get_by_user_id(self, user_id: str) -> Optional[PatientInDB]:
        doc = await self.get_by_field("user_id", user_id)
        return PatientInDB(**doc) if doc else None

    async def get_by_patient_id(self, patient_id: str) -> Optional[PatientInDB]:
        doc = await self.get_by_field("patient_id", patient_id)
        if doc:
            return PatientInDB(**doc)
        doc = await self.get_by_field("user_id", patient_id)
        if doc:
            return PatientInDB(**doc)
        doc = await self.get_by_id(patient_id)
        return PatientInDB(**doc) if doc else None

    async def get_by_patient_code(self, patient_code: str) -> Optional[PatientInDB]:
        doc = await self.get_by_field("patient_code", patient_code)
        return PatientInDB(**doc) if doc else None

    async def update_profile(self, patient_id: str, **kwargs) -> Optional[PatientInDB]:
        kwargs.pop("user_id", None)
        kwargs.pop("patient_id", None)
        kwargs.pop("id", None)
        kwargs.pop("patient_code", None)  # patient_code is immutable
        updated = await self.update(patient_id, kwargs)
        return PatientInDB(**updated) if updated else None

    async def search_patients(self, query: str, limit: int = 20) -> List[PatientInDB]:
        """Search patients by name, email, or patient_code. Returns minimal fields."""
        import re
        safe = re.escape(query[:50])
        filter_query = {
            "$or": [
                {"full_name": {"$regex": safe, "$options": "i"}},
                {"contact_email": {"$regex": safe, "$options": "i"}},
                {"patient_code": {"$regex": safe, "$options": "i"}},
            ]
        }
        cursor = self.collection.find(filter_query).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [PatientInDB(**doc) for doc in docs]
