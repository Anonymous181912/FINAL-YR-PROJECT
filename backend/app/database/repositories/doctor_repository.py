from typing import Optional
from app.database.collections import DOCTOR_PROFILES
from app.database.repositories.base_repository import BaseRepository
from app.models.doctor import DoctorInDB


class DoctorRepository(BaseRepository):
    def __init__(self):
        super().__init__(DOCTOR_PROFILES)

    async def create_profile(self, user_id: str, full_name: str, **kwargs) -> DoctorInDB:
        data = {
            "user_id": user_id,
            # Prescriptions reference doctors by the user UUID, so the profile
            # carries the same value as its canonical doctor_id.
            "doctor_id": kwargs.pop("doctor_id", user_id),
            "full_name": full_name,
            **kwargs,
        }
        created = await self.create(data)
        return DoctorInDB(**created)

    async def get_by_user_id(self, user_id: str) -> Optional[DoctorInDB]:
        doc = await self.get_by_field("user_id", user_id)
        return DoctorInDB(**doc) if doc else None

    async def get_by_doctor_id(self, doctor_id: str) -> Optional[DoctorInDB]:
        doc = await self.get_by_field("doctor_id", doctor_id)
        if doc:
            return DoctorInDB(**doc)
        doc = await self.get_by_field("user_id", doctor_id)
        if doc:
            return DoctorInDB(**doc)
        doc = await self.get_by_id(doctor_id)
        return DoctorInDB(**doc) if doc else None

    async def update_profile(self, doctor_id: str, **kwargs) -> Optional[DoctorInDB]:
        kwargs.pop("user_id", None)
        kwargs.pop("doctor_id", None)
        kwargs.pop("id", None)
        # Verification fields are admin-only; never editable via /doctors/me.
        kwargs.pop("is_verified", None)
        kwargs.pop("verification_status", None)
        updated = await self.update(doctor_id, kwargs)
        return DoctorInDB(**updated) if updated else None

    async def list_pending(self, skip: int = 0, limit: int = 50):
        docs = await self.list(skip=skip, limit=limit, filter={"verification_status": "pending"})
        return [DoctorInDB(**doc) for doc in docs]

    async def set_verification(self, doctor_id: str, status: str) -> Optional[DoctorInDB]:
        if status not in ("approved", "rejected", "pending"):
            return None
        updated = await self.update(
            doctor_id,
            {"verification_status": status, "is_verified": status == "approved"},
        )
        return DoctorInDB(**updated) if updated else None
