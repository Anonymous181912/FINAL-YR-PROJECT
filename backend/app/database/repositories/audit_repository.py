from typing import Optional
from datetime import datetime, timezone
from app.database.collections import AUDIT_LOGS
from app.database.repositories.base_repository import BaseRepository
from app.models.audit import AuditLogInDB


class AuditRepository(BaseRepository):
    def __init__(self):
        super().__init__(AUDIT_LOGS)

    async def log(self, **kwargs) -> Optional[AuditLogInDB]:
        payload = {**kwargs, "timestamp": datetime.now(timezone.utc)}
        try:
            created = await self.create(payload)
        except Exception:
            return None
        try:
            return AuditLogInDB(**created)
        except Exception:
            return None

    async def for_patient(self, patient_id: str, limit: int = 100):
        cursor = self.collection.find({"patient_id": patient_id})
        try:
            cursor.sort("timestamp", -1)
        except Exception:
            pass
        docs = await cursor.to_list(length=limit)
        out = []
        for d in docs:
            try:
                out.append(AuditLogInDB(**d))
            except Exception:
                continue
        return out

    async def search(self, actor_id=None, action=None, patient_id=None,
                     resource_type=None, limit: int = 100):
        filt: dict = {}
        if actor_id:
            filt["actor_id"] = actor_id
        if action:
            filt["action"] = action
        if patient_id:
            filt["patient_id"] = patient_id
        if resource_type:
            filt["resource_type"] = resource_type
        cursor = self.collection.find(filt)
        try:
            cursor.sort("timestamp", -1)
        except Exception:
            pass
        docs = await cursor.to_list(length=limit)
        out = []
        for d in docs:
            try:
                out.append(AuditLogInDB(**d))
            except Exception:
                continue
        return out
