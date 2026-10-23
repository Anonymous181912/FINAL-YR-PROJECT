"""Notifications router (Phase 2c): own inbox + mark read."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.notification import NotificationInDB
from app.database.repositories.notification_repository import NotificationRepository

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=List[NotificationInDB])
async def list_notifications(
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
):
    repo = NotificationRepository()
    items = await repo.list_for_user(current_user.id, limit=limit)
    if unread_only:
        items = [n for n in items if not n.is_read]
    return items


@router.patch("/{notification_id}/read", response_model=NotificationInDB)
async def mark_notification_read(notification_id: str, current_user: User = Depends(get_current_user)):
    repo = NotificationRepository()
    updated = await repo.mark_read(notification_id, current_user.id)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return updated


@router.post("/read-all")
async def mark_all_read(current_user: User = Depends(get_current_user)):
    repo = NotificationRepository()
    count = await repo.mark_all_read(current_user.id)
    return {"marked_read": count}
