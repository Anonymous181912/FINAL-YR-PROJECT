"""Refresh tokens + password resets (Phase 6c). Opaque tokens; only SHA-256
hashes are stored, so a database read alone never yields a usable token."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel

from app.database.collections import REFRESH_TOKENS, PASSWORD_RESETS
from app.database.repositories.base_repository import BaseRepository


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class RefreshTokenRepository(BaseRepository):
    def __init__(self):
        super().__init__(REFRESH_TOKENS)

    async def issue(self, user_id: str, days: int = 7) -> str:
        token = secrets.token_urlsafe(48)
        await self.create({
            "user_id": user_id,
            "token_hash": _hash(token),
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=days),
            "revoked": False,
        })
        return token

    async def redeem(self, token: str) -> Optional[dict]:
        """Rotation: valid token is revoked and its user returned (or None)."""
        doc = await self.get_by_field("token_hash", _hash(token))
        if not doc or doc.get("revoked"):
            return None
        exp = doc.get("expires_at")
        if exp is not None:
            if isinstance(exp, str):
                try:
                    exp = datetime.fromisoformat(exp)
                except ValueError:
                    return None
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp <= datetime.now(timezone.utc):
                return None
        await self.update(doc["id"], {"revoked": True})
        return doc

    async def revoke(self, token: str) -> bool:
        doc = await self.get_by_field("token_hash", _hash(token))
        if not doc:
            return False
        await self.update(doc["id"], {"revoked": True})
        return True

    async def revoke_all_for_user(self, user_id: str) -> int:
        try:
            result = await self.collection.update_many(
                {"user_id": user_id, "revoked": False}, {"$set": {"revoked": True}})
            return result.modified_count
        except Exception:
            return 0


class PasswordResetRepository(BaseRepository):
    def __init__(self):
        super().__init__(PASSWORD_RESETS)

    async def issue(self, user_id: str, minutes: int = 60) -> str:
        token = secrets.token_urlsafe(32)
        await self.create({
            "user_id": user_id,
            "token_hash": _hash(token),
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=minutes),
            "used": False,
        })
        return token

    async def consume(self, token: str) -> Optional[dict]:
        doc = await self.get_by_field("token_hash", _hash(token))
        if not doc or doc.get("used"):
            return None
        exp = doc.get("expires_at")
        if exp is not None:
            if isinstance(exp, str):
                try:
                    exp = datetime.fromisoformat(exp)
                except ValueError:
                    return None
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp <= datetime.now(timezone.utc):
                return None
        await self.update(doc["id"], {"used": True})
        return doc


class RefreshRequest(BaseModel):
    refresh_token: str


class ResetRequest(BaseModel):
    token: str
    new_password: str


class ForgotRequest(BaseModel):
    email: str
