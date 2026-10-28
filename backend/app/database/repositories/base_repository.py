import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.database.connection import get_database


class BaseRepository:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    @property
    def collection(self):
        return get_database()[self.collection_name]

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data.setdefault("id", self._generate_id())
        data["created_at"] = self._now()
        data["updated_at"] = self._now()
        await self.collection.insert_one(data)
        return data

    async def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"id": id})

    async def get_by_field(self, field: str, value: Any) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({field: value})

    async def update(self, id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data["updated_at"] = self._now()
        result = await self.collection.find_one_and_update(
            {"id": id},
            {"$set": data},
            return_document=True,
        )
        return result

    async def delete(self, id: str) -> bool:
        result = await self.collection.delete_one({"id": id})
        return result.deleted_count > 0

    async def list(self, skip: int = 0, limit: int = 20, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        cursor = self.collection.find(filter or {})
        cursor.skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
