"""Announcements + notifications services."""

from math import ceil
from typing import Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.core.logging import get_logger
from app.database.http import get_http_client
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementListResponse,
    AnnouncementPriority,
    AnnouncementResponse,
    AnnouncementUpdate,
    NotificationCategory,
    NotificationListResponse,
    NotificationResponse,
)

logger = get_logger("hospital_ai.announcements")

ANN_SELECT = (
    "id,title,description,priority,category,is_active,created_by,created_at,updated_at"
)
NOTIF_SELECT = (
    "id,user_id,title,message,category,priority,link,is_read,created_at"
)


class AnnouncementService:
    def _headers(self, prefer: Optional[str] = None) -> Dict[str, str]:
        settings = get_settings()
        settings.require_supabase()
        headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _url(self) -> str:
        return f"{get_settings().supabase_url.rstrip('/')}/rest/v1/hospital_announcements"

    def _notif_url(self) -> str:
        return f"{get_settings().supabase_url.rstrip('/')}/rest/v1/hospital_notifications"

    def _handle(self, response: httpx.Response, action: str) -> None:
        if response.status_code < 400:
            return
        logger.error("%s failed: %s %s", action, response.status_code, response.text)
        detail = "Announcement operation failed"
        try:
            body = response.json()
            detail = body.get("message") or body.get("error") or detail
        except Exception:  # noqa: BLE001
            pass
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Not found")
        if 400 <= response.status_code < 500:
            raise HTTPException(status_code=400, detail=detail)
        raise HTTPException(status_code=502, detail=detail)

    def list_announcements(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        priority: Optional[AnnouncementPriority] = None,
        active_only: bool = False,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> AnnouncementListResponse:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10
        order = "desc" if sort_order.lower() == "desc" else "asc"
        if sort_by not in {"created_at", "priority", "title", "updated_at"}:
            sort_by = "created_at"
        params: List[tuple[str, str]] = [
            ("select", ANN_SELECT),
            ("order", f"{sort_by}.{order}"),
        ]
        if priority:
            params.append(("priority", f"eq.{priority.value}"))
        if active_only:
            params.append(("is_active", "eq.true"))
        if search:
            safe = search.strip().replace("\\", "\\\\").replace("*", "\\*").replace(",", "\\,")
            if safe:
                params.append(
                    (
                        "or",
                        f"(title.ilike.*{safe}*,description.ilike.*{safe}*,category.ilike.*{safe}*)",
                    )
                )
        offset = (page - 1) * page_size
        headers = self._headers(prefer="count=exact")
        headers["Range-Unit"] = "items"
        headers["Range"] = f"{offset}-{offset + page_size - 1}"
        try:
            response = get_http_client().get(self._url(), headers=headers, params=params)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        self._handle(response, "list_announcements")
        total = 0
        cr = response.headers.get("content-range", "")
        if "/" in cr:
            try:
                total = int(cr.split("/")[-1])
            except ValueError:
                total = 0
        rows = response.json() if isinstance(response.json(), list) else []
        items = [AnnouncementResponse.model_validate(r) for r in rows if isinstance(r, dict)]
        return AnnouncementListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=ceil(total / page_size) if page_size and total else 0,
        )

    def get_announcement(self, announcement_id: UUID) -> AnnouncementResponse:
        try:
            response = get_http_client().get(
                self._url(),
                headers=self._headers(),
                params=[("select", ANN_SELECT), ("id", f"eq.{announcement_id}")],
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        self._handle(response, "get_announcement")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=404, detail="Announcement not found")
        return AnnouncementResponse.model_validate(rows[0])

    def create_announcement(
        self, payload: AnnouncementCreate, created_by: UUID
    ) -> AnnouncementResponse:
        body = payload.model_dump(mode="json")
        body["created_by"] = str(created_by)
        try:
            response = get_http_client().post(
                self._url(),
                headers=self._headers(prefer="return=representation"),
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        self._handle(response, "create_announcement")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=502, detail="Announcement created but no data returned")
        created = AnnouncementResponse.model_validate(rows[0])
        # Mirror into notification center (broadcast)
        self._create_notification(
            user_id=None,
            title=created.title,
            message=created.description[:500],
            category=NotificationCategory.ANNOUNCEMENTS,
            priority=created.priority,
            link="/announcements",
        )
        return created

    def update_announcement(
        self, announcement_id: UUID, payload: AnnouncementUpdate
    ) -> AnnouncementResponse:
        body = payload.model_dump(mode="json", exclude_unset=True)
        if not body:
            return self.get_announcement(announcement_id)
        try:
            response = get_http_client().patch(
                self._url(),
                headers=self._headers(prefer="return=representation"),
                params=[("id", f"eq.{announcement_id}")],
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        self._handle(response, "update_announcement")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=404, detail="Announcement not found")
        return AnnouncementResponse.model_validate(rows[0])

    def delete_announcement(self, announcement_id: UUID) -> None:
        self.get_announcement(announcement_id)
        try:
            response = get_http_client().delete(
                self._url(),
                headers=self._headers(),
                params=[("id", f"eq.{announcement_id}")],
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        self._handle(response, "delete_announcement")

    def _create_notification(
        self,
        *,
        user_id: Optional[UUID],
        title: str,
        message: str,
        category: NotificationCategory,
        priority: AnnouncementPriority,
        link: Optional[str] = None,
    ) -> None:
        body = {
            "user_id": str(user_id) if user_id else None,
            "title": title,
            "message": message,
            "category": category.value,
            "priority": priority.value,
            "link": link,
            "is_read": False,
        }
        try:
            get_http_client().post(
                self._notif_url(),
                headers=self._headers(prefer="return=minimal"),
                json=body,
            )
        except httpx.HTTPError:
            logger.warning("Failed to create notification", exc_info=True)

    def list_notifications(
        self, *, user_id: Optional[UUID] = None, unread_only: bool = False
    ) -> NotificationListResponse:
        params: List[tuple[str, str]] = [
            ("select", NOTIF_SELECT),
            ("order", "created_at.desc"),
            ("limit", "50"),
        ]
        # Broadcast (null user) + user-specific
        if user_id:
            params.append(("or", f"(user_id.is.null,user_id.eq.{user_id})"))
        if unread_only:
            params.append(("is_read", "eq.false"))
        try:
            response = get_http_client().get(
                self._notif_url(), headers=self._headers(), params=params
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        if response.status_code >= 400:
            return NotificationListResponse(items=[], total=0, unread_count=0)
        rows = response.json() if isinstance(response.json(), list) else []
        items = [
            NotificationResponse.model_validate(r) for r in rows if isinstance(r, dict)
        ]
        unread = sum(1 for i in items if not i.is_read)
        return NotificationListResponse(
            items=items, total=len(items), unread_count=unread
        )

    def mark_read(self, notification_id: UUID) -> NotificationResponse:
        try:
            response = get_http_client().patch(
                self._notif_url(),
                headers=self._headers(prefer="return=representation"),
                params=[("id", f"eq.{notification_id}")],
                json={"is_read": True},
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        self._handle(response, "mark_notification_read")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=404, detail="Notification not found")
        return NotificationResponse.model_validate(rows[0])

    def mark_all_read(self, user_id: Optional[UUID] = None) -> None:
        params: List[tuple[str, str]] = [("is_read", "eq.false")]
        if user_id:
            params.append(("or", f"(user_id.is.null,user_id.eq.{user_id})"))
        try:
            get_http_client().patch(
                self._notif_url(),
                headers=self._headers(prefer="return=minimal"),
                params=params,
                json={"is_read": True},
            )
        except httpx.HTTPError:
            logger.warning("mark_all_read failed", exc_info=True)


announcement_service = AnnouncementService()
