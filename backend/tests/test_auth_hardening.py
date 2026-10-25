"""Phase 6c tests: refresh rotation, logout, password reset, lockout."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_mongo():
    mock_db = MagicMock()

    def get_mock_collection(name):
        return AsyncMock()

    mock_db.__getitem__ = MagicMock(side_effect=get_mock_collection)

    with patch("app.database.connection.db", mock_db), \
         patch("app.database.connection.connect_to_mongo"), \
         patch("app.database.connection.close_mongo_connection"), \
         patch("app.database.indexes.create_indexes"):
        yield


def _db_user(uid="u1", email="a@test.com", role="patient", active=True):
    from app.models.user import UserInDB

    now = datetime.now(timezone.utc)
    return UserInDB(id=uid, email=email, role=role, full_name="Test User",
                    hashed_password="hashed", is_active=active,
                    created_at=now, updated_at=now)


class TestRefreshRotation:
    def test_use_twice_second_fails(self):
        import asyncio

        async def run():
            from app.auth.tokens import RefreshTokenRepository

            store: dict = {}

            async def fake_create(self, data):
                data = dict(data)
                data["id"] = "rt1"
                store[data["token_hash"]] = data
                return data

            async def fake_get_by_field(self, field, value):
                return store.get(value) if field == "token_hash" else None

            async def fake_update(self, _id, patch_):
                store[[k for k, v in store.items() if v["id"] == _id][0]].update(patch_)
                return store[[k for k, v in store.items() if v["id"] == _id][0]]

            with patch.object(RefreshTokenRepository, "create", new=fake_create), \
                 patch.object(RefreshTokenRepository, "get_by_field", new=fake_get_by_field), \
                 patch.object(RefreshTokenRepository, "update", new=fake_update):
                repo = RefreshTokenRepository()
                token = await repo.issue("u1")
                first = await repo.redeem(token)
                assert first is not None and first["user_id"] == "u1"
                assert await repo.redeem(token) is None  # rotated: single use
                assert await repo.revoke("never-issued") is False

        asyncio.run(run())

    def test_refresh_endpoint_rotates(self):
        with patch("app.auth.tokens.RefreshTokenRepository") as repo_cls, \
             patch("app.auth.router.UserRepository") as user_cls:
            repo = AsyncMock()
            repo.redeem.return_value = {"user_id": "u1"}
            repo.issue.return_value = "new-refresh"
            repo_cls.return_value = repo
            users = AsyncMock()
            users.get_by_id.return_value = _db_user()
            user_cls.return_value = users
            with patch("app.auth.router.create_access_token", return_value="access-1"):
                r = client.post("/api/v1/auth/refresh", json={"refresh_token": "old"})
                assert r.status_code == 200
                assert r.json()["refresh_token"] == "new-refresh"

    def test_logout_invalidates(self):
        with patch("app.auth.tokens.RefreshTokenRepository") as repo_cls:
            repo = AsyncMock()
            repo.revoke.return_value = True
            repo_cls.return_value = repo
            r = client.post("/api/v1/auth/logout", json={"refresh_token": "tok"})
            assert r.status_code == 200
            repo.revoke.assert_called_once_with("tok")


class TestPasswordReset:
    def test_forgot_always_200(self):
        with patch("app.auth.router.UserRepository") as user_cls:
            users = AsyncMock()
            users.get_by_email.return_value = None
            user_cls.return_value = users
            assert client.post("/api/v1/auth/forgot-password",
                               json={"email": "nobody@test.com"}).status_code == 200

    def test_forgot_sends_when_user_exists(self):
        with patch("app.auth.router.UserRepository") as user_cls, \
             patch("app.auth.tokens.PasswordResetRepository") as reset_cls, \
             patch("app.notifications.scheduler.send_email_best_effort", return_value=True) as mail:
            users = AsyncMock()
            users.get_by_email.return_value = _db_user()
            user_cls.return_value = users
            resets = AsyncMock()
            resets.issue.return_value = "reset-tok"
            reset_cls.return_value = resets
            assert client.post("/api/v1/auth/forgot-password",
                               json={"email": "a@test.com"}).status_code == 200
            mail.assert_called_once()

    def test_reset_weak_password_422(self):
        r = client.post("/api/v1/auth/reset-password",
                        json={"token": "t", "new_password": "short"})
        assert r.status_code == 422

    def test_reset_bad_token_400(self):
        with patch("app.auth.tokens.PasswordResetRepository") as reset_cls:
            resets = AsyncMock()
            resets.consume.return_value = None
            reset_cls.return_value = resets
            r = client.post("/api/v1/auth/reset-password",
                            json={"token": "bad", "new_password": "Strong1234"})
            assert r.status_code == 400

    def test_reset_success_revokes_sessions(self):
        with patch("app.auth.tokens.PasswordResetRepository") as reset_cls, \
             patch("app.auth.router.UserRepository") as user_cls, \
             patch("app.auth.tokens.RefreshTokenRepository") as refresh_cls:
            resets = AsyncMock()
            resets.consume.return_value = {"user_id": "u1"}
            reset_cls.return_value = resets
            users = AsyncMock()
            users.get_by_id.return_value = _db_user()
            user_cls.return_value = users
            refresh = AsyncMock()
            refresh_cls.return_value = refresh
            r = client.post("/api/v1/auth/reset-password",
                            json={"token": "good", "new_password": "Strong1234"})
            assert r.status_code == 200, r.text
            users.set_password.assert_called_once()
            refresh.revoke_all_for_user.assert_called_once_with("u1")


class TestLockout:
    def _login(self, patch_user, portal="patient"):
        return client.post("/api/v1/auth/login",
                           data={"username": "a@test.com", "password": "wrong", "portal": portal})

    def test_five_failures_lock(self):
        from app.core.security import get_password_hash

        with patch("app.auth.router.UserRepository") as user_cls:
            users = AsyncMock()
            user = _db_user()
            user.hashed_password = get_password_hash("right123")
            users.get_by_email.return_value = user
            users.record_failed_login.return_value = (False, 1)
            user_cls.return_value = users
            assert self._login(users).status_code == 401
            users.record_failed_login.return_value = (True, 5)
            assert self._login(users).status_code == 403

    def test_locked_account_rejects_correct_password(self):
        from datetime import timedelta

        from app.core.security import get_password_hash

        with patch("app.auth.router.UserRepository") as user_cls:
            user = _db_user()
            user.hashed_password = get_password_hash("right123")
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
            users = AsyncMock()
            users.get_by_email.return_value = user
            user_cls.return_value = users
            r = client.post("/api/v1/auth/login",
                            data={"username": "a@test.com", "password": "right123", "portal": "patient"})
            assert r.status_code == 403
            assert "locked" in r.json()["detail"].lower()
