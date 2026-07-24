"""Announcements + notifications REST API."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.auth.dependencies import CurrentUser
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementListResponse,
    AnnouncementPriority,
    AnnouncementResponse,
    AnnouncementUpdate,
    MessageResponse,
    NotificationListResponse,
    NotificationResponse,
)
from app.services.announcement_service import announcement_service

router = APIRouter(prefix="/announcements", tags=["announcements"])
notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=AnnouncementListResponse)
def list_announcements(
    _current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    priority: Optional[AnnouncementPriority] = Query(None),
    active_only: bool = Query(False),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
) -> AnnouncementListResponse:
    return announcement_service.list_announcements(
        page=page,
        page_size=page_size,
        search=search,
        priority=priority,
        active_only=active_only,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{announcement_id}", response_model=AnnouncementResponse)
def get_announcement(
    announcement_id: UUID, _current_user: CurrentUser
) -> AnnouncementResponse:
    return announcement_service.get_announcement(announcement_id)


@router.post("", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
def create_announcement(
    body: AnnouncementCreate, current_user: CurrentUser
) -> AnnouncementResponse:
    return announcement_service.create_announcement(body, created_by=current_user.id)


@router.put("/{announcement_id}", response_model=AnnouncementResponse)
def update_announcement(
    announcement_id: UUID, body: AnnouncementUpdate, _current_user: CurrentUser
) -> AnnouncementResponse:
    return announcement_service.update_announcement(announcement_id, body)


@router.delete("/{announcement_id}", response_model=MessageResponse)
def delete_announcement(
    announcement_id: UUID, _current_user: CurrentUser
) -> MessageResponse:
    announcement_service.delete_announcement(announcement_id)
    return MessageResponse(message="Announcement deleted successfully")


@notifications_router.get("", response_model=NotificationListResponse)
def list_notifications(
    current_user: CurrentUser,
    unread_only: bool = Query(False),
) -> NotificationListResponse:
    return announcement_service.list_notifications(
        user_id=current_user.id, unread_only=unread_only
    )


@notifications_router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: UUID, _current_user: CurrentUser
) -> NotificationResponse:
    return announcement_service.mark_read(notification_id)


@notifications_router.post("/read-all", response_model=MessageResponse)
def mark_all_notifications_read(current_user: CurrentUser) -> MessageResponse:
    announcement_service.mark_all_read(user_id=current_user.id)
    return MessageResponse(message="All notifications marked as read")
