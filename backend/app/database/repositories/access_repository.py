from typing import Optional
from datetime import datetime, timezone
from app.database.collections import ACCESS_REQUESTS, ACCESS_GRANTS
from app.database.repositories.base_repository import BaseRepository
from app.models.access import AccessRequestInDB, AccessGrantInDB


class AccessRequestRepository(BaseRepository):
    def __init__(self):
        super().__init__(ACCESS_REQUESTS)

    async def create_request(self, **kwargs) -> AccessRequestInDB:
        created = await self.create(kwargs)
        return AccessRequestInDB(**created)

    async def pending_for(self, patient_id: str, doctor_id: str) -> Optional[AccessRequestInDB]:
        cursor = self.collection.find(
            {"patient_id": patient_id, "doctor_id": doctor_id, "status": "pending"}
        )
        docs = await cursor.to_list(length=5)
        return AccessRequestInDB(**docs[0]) if docs else None

    async def incoming(self, patient_id: str, status: Optional[str] = None, limit: int = 50):
        filt: dict = {"patient_id": patient_id}
        if status:
            filt["status"] = status
        cursor = self.collection.find(filt)
        try:
            cursor.sort("created_at", -1)
        except Exception:
            pass
        docs = await cursor.to_list(length=limit)
        return [AccessRequestInDB(**d) for d in docs]

    async def outgoing(self, doctor_id: str, limit: int = 50):
        cursor = self.collection.find({"doctor_id": doctor_id})
        try:
            cursor.sort("created_at", -1)
        except Exception:
            pass
        docs = await cursor.to_list(length=limit)
        return [AccessRequestInDB(**d) for d in docs]

    async def decide(self, request_id: str, status: str) -> Optional[AccessRequestInDB]:
        updated = await self.update(request_id, {"status": status, "decided_at": datetime.now(timezone.utc)})
        return AccessRequestInDB(**updated) if updated else None


class AccessGrantRepository(BaseRepository):
    def __init__(self):
        super().__init__(ACCESS_GRANTS)

    async def create_grant(self, **kwargs) -> AccessGrantInDB:
        created = await self.create(kwargs)
        return AccessGrantInDB(**created)

    async def get_active(self, patient_id: str, doctor_id: str) -> Optional[AccessGrantInDB]:
        doc = await self.collection.find_one(
            {"patient_id": patient_id, "doctor_id": doctor_id, "status": "active"}
        )
        return AccessGrantInDB(**doc) if doc else None

    async def list_active_for_doctor(self, doctor_id: str, limit: int = 200):
        cursor = self.collection.find({"doctor_id": doctor_id, "status": "active"})
        docs = await cursor.to_list(length=limit)
        return [AccessGrantInDB(**d) for d in docs]

    async def list_for_patient(self, patient_id: str, limit: int = 200):
        cursor = self.collection.find({"patient_id": patient_id})
        try:
            cursor.sort("created_at", -1)
        except Exception:
            pass
        docs = await cursor.to_list(length=limit)
        return [AccessGrantInDB(**d) for d in docs]

    async def revoke(self, grant_id: str) -> Optional[AccessGrantInDB]:
        now = datetime.now(timezone.utc)
        updated = await self.update(grant_id, {"status": "revoked", "revoked_at": now})
        return AccessGrantInDB(**updated) if updated else None

    async def mark_expired(self, grant_id: str) -> Optional[AccessGrantInDB]:
        updated = await self.update(grant_id, {"status": "expired"})
        return AccessGrantInDB(**updated) if updated else None
