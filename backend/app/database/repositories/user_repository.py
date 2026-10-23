from typing import Optional
from app.database.collections import USERS
from app.database.repositories.base_repository import BaseRepository
from app.models.user import UserInDB


class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__(USERS)

    async def create_user(self, email: str, hashed_password: str, role: str, full_name: str, is_active: bool = True) -> UserInDB:
        data = {
            "email": email.lower(),
            "hashed_password": hashed_password,
            "role": role,
            "full_name": full_name,
            "is_active": is_active,
        }
        created = await self.create(data)
        return UserInDB(**created)

    async def get_by_email(self, email: str) -> Optional[UserInDB]:
        doc = await self.get_by_field("email", email.lower())
        return UserInDB(**doc) if doc else None

    async def get_by_id(self, user_id: str) -> Optional[UserInDB]:
        doc = await super().get_by_id(user_id)
        return UserInDB(**doc) if doc else None

    async def exists_email(self, email: str) -> bool:
        doc = await self.get_by_email(email)
        return doc is not None

    async def record_failed_login(self, user_id: str, max_attempts: int = 5,
                                  lock_minutes: int = 15):
        """Increment failures; lock the account past the threshold.

        Returns (locked: bool, attempts: int)."""
        from datetime import datetime, timezone, timedelta

        doc = await super().get_by_id(user_id)
        if not doc:
            return False, 0
        attempts = int(doc.get("failed_login_attempts", 0) or 0) + 1
        patch: dict = {"failed_login_attempts": attempts}
        locked = False
        if attempts >= max_attempts:
            patch["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=lock_minutes)
            locked = True
        await self.update(user_id, patch)
        return locked, attempts

    async def reset_lockout(self, user_id: str) -> None:
        await self.update(user_id, {"failed_login_attempts": 0, "locked_until": None})

    async def set_password(self, user_id: str, hashed_password: str) -> None:
        await self.update(user_id, {"hashed_password": hashed_password,
                                    "failed_login_attempts": 0, "locked_until": None})
