"""Announcement and notification schemas."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AnnouncementPriority(str, Enum):
    LOW = "Low"
    NORMAL = "Normal"
    HIGH = "High"
    EMERGENCY = "Emergency"


class NotificationCategory(str, Enum):
    APPOINTMENTS = "Appointments"
    RESOURCES = "Resources"
    ANNOUNCEMENTS = "Announcements"
    SYSTEM = "System"


class AnnouncementBase(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=5000)
    priority: AnnouncementPriority = AnnouncementPriority.NORMAL
    category: str = Field(default="Hospital Notice", max_length=100)
    is_active: bool = True

    @field_validator("title", "description", "category")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, min_length=1, max_length=5000)
    priority: Optional[AnnouncementPriority] = None
    category: Optional[str] = Field(default=None, max_length=100)
    is_active: Optional[bool] = None


class AnnouncementResponse(AnnouncementBase):
    id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class AnnouncementListResponse(BaseModel):
    items: List[AnnouncementResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class NotificationResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    title: str
    message: str
    category: NotificationCategory
    priority: AnnouncementPriority
    link: Optional[str] = None
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int


class MessageResponse(BaseModel):
    message: str
