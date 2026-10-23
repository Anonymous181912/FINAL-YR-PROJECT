from typing import Optional
from app.database.collections import NOTIFICATIONS
from app.database.repositories.base_repository import BaseRepository
from app.models.notification import NotificationInDB


class NotificationRepository(BaseRepository):
    def __init__(self):
        super().__init__(NOTIFICATIONS)

    async def create_notification(self, **kwargs) -> NotificationInDB:
        created = await self.create(kwargs)
        return NotificationInDB(**created)

    async def create_if_absent(self, dedupe_key: str, **kwargs) -> Optional[NotificationInDB]:
        existing = await self.get_by_field("dedupe_key", dedupe_key)
        if existing:
            return None
        try:
            created = await self.create({**kwargs, "dedupe_key": dedupe_key})
        except Exception:
            # Race (unique index) or unavailable DB: treat as already present.
            return None
        return NotificationInDB(**created)

    async def list_for_user(self, user_id: str, limit: int = 50) -> list[NotificationInDB]:
        cursor = self.collection.find({"user_id": user_id})
        try:
            cursor.sort("created_at", -1)
        except Exception:
            pass
        docs = await cursor.to_list(length=limit)
        out = []
        for doc in docs:
            try:
                out.append(NotificationInDB(**doc))
            except Exception:
                continue
        return out

    async def mark_read(self, notification_id: str, user_id: str) -> Optional[NotificationInDB]:
        doc = await self.get_by_id(notification_id)
        if not doc or doc.get("user_id") != user_id:
            return None
        updated = await self.update(notification_id, {"is_read": True})
        return NotificationInDB(**updated) if updated else None

    async def mark_all_read(self, user_id: str) -> int:
        try:
            result = await self.collection.update_many(
                {"user_id": user_id, "is_read": False}, {"$set": {"is_read": True}}
            )
            return result.modified_count
        except Exception:
            return 0
