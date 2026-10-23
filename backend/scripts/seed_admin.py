"""Seed the first admin user from env vars (Phase 0b).

Usage (PowerShell):
    $env:ADMIN_EMAIL="admin@example.com"
    $env:ADMIN_PASSWORD="Admin1234"
    python scripts/seed_admin.py

Reads ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_FULL_NAME from the environment
(or backend/.env). Creates a user with role "admin" if the email is not
already registered. Never logs or prints the password.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings


async def seed_initial_admin() -> dict:
    from app.core.security import get_password_hash
    from app.database.connection import connect_to_mongo, close_mongo_connection
    from app.database.repositories.user_repository import UserRepository

    email = (os.getenv("ADMIN_EMAIL") or settings.admin_email or "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD") or settings.admin_password or ""
    full_name = os.getenv("ADMIN_FULL_NAME") or settings.admin_full_name or "System Administrator"

    if not email or not password:
        raise SystemExit("Set ADMIN_EMAIL and ADMIN_PASSWORD env vars to seed the first admin.")
    if len(password) < 8:
        raise SystemExit("ADMIN_PASSWORD must be at least 8 characters.")

    await connect_to_mongo()
    try:
        repo = UserRepository()
        existing = await repo.get_by_email(email)
        if existing:
            return {"created": False, "email": email, "user_id": existing.id}
        hashed = get_password_hash(password)
        user = await repo.create_user(
            email=email, hashed_password=hashed, role="admin", full_name=full_name
        )
        return {"created": True, "email": email, "user_id": user.id}
    finally:
        await close_mongo_connection()


async def main() -> None:
    result = await seed_initial_admin()
    if result["created"]:
        print(f"Admin created: {result['email']} (id={result['user_id']})")
    else:
        print(f"Admin already exists: {result['email']} (id={result['user_id']})")


if __name__ == "__main__":
    asyncio.run(main())
