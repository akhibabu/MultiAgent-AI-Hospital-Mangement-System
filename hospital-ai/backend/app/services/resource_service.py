"""Hospital resources CRUD."""

from math import ceil
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.core.logging import get_logger
from app.database.http import get_http_client
from app.schemas.resource import (
    HospitalResourceCreate,
    HospitalResourceListResponse,
    HospitalResourceResponse,
    HospitalResourceUpdate,
    ResourceStatus,
    ResourceType,
)

logger = get_logger("hospital_ai.resources")

SELECT = (
    "id,resource_name,resource_type,quantity,available_quantity,status,"
    "location,notes,created_at,updated_at"
)
SORTABLE = {"resource_name", "resource_type", "status", "quantity", "created_at", "updated_at"}


class ResourceService:
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
        return f"{get_settings().supabase_url.rstrip('/')}/rest/v1/hospital_resources"

    def _handle(self, response: httpx.Response, action: str) -> None:
        if response.status_code < 400:
            return
        logger.error("%s failed: %s %s", action, response.status_code, response.text)
        detail = "Resource operation failed"
        try:
            body = response.json()
            detail = body.get("message") or body.get("error") or detail
        except Exception:  # noqa: BLE001
            pass
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Resource not found")
        if 400 <= response.status_code < 500:
            raise HTTPException(status_code=400, detail=detail)
        raise HTTPException(status_code=502, detail=detail)

    def list_resources(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        status: Optional[ResourceStatus] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> HospitalResourceListResponse:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10
        if sort_by not in SORTABLE:
            sort_by = "created_at"
        order = "desc" if sort_order.lower() == "desc" else "asc"
        params: List[tuple[str, str]] = [
            ("select", SELECT),
            ("order", f"{sort_by}.{order}"),
        ]
        if resource_type:
            params.append(("resource_type", f"eq.{resource_type.value}"))
        if status:
            params.append(("status", f"eq.{status.value}"))
        if search:
            safe = search.strip().replace("\\", "\\\\").replace("*", "\\*").replace(",", "\\,")
            if safe:
                params.append(
                    (
                        "or",
                        f"(resource_name.ilike.*{safe}*,location.ilike.*{safe}*)",
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
        self._handle(response, "list_resources")
        total = 0
        cr = response.headers.get("content-range", "")
        if "/" in cr:
            try:
                total = int(cr.split("/")[-1])
            except ValueError:
                total = 0
        rows = response.json() if isinstance(response.json(), list) else []
        items = [HospitalResourceResponse.model_validate(r) for r in rows if isinstance(r, dict)]
        return HospitalResourceListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=ceil(total / page_size) if page_size and total else 0,
        )

    def get_resource(self, resource_id: UUID) -> HospitalResourceResponse:
        try:
            response = get_http_client().get(
                self._url(),
                headers=self._headers(),
                params=[("select", SELECT), ("id", f"eq.{resource_id}")],
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        self._handle(response, "get_resource")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=404, detail="Resource not found")
        return HospitalResourceResponse.model_validate(rows[0])

    def create_resource(self, payload: HospitalResourceCreate) -> HospitalResourceResponse:
        try:
            response = get_http_client().post(
                self._url(),
                headers=self._headers(prefer="return=representation"),
                json=payload.model_dump(mode="json"),
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        self._handle(response, "create_resource")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=502, detail="Resource created but no data returned")
        return HospitalResourceResponse.model_validate(rows[0])

    def update_resource(
        self, resource_id: UUID, payload: HospitalResourceUpdate
    ) -> HospitalResourceResponse:
        body = payload.model_dump(mode="json", exclude_unset=True)
        if not body:
            return self.get_resource(resource_id)
        if "quantity" in body or "available_quantity" in body:
            current = self.get_resource(resource_id)
            qty = body.get("quantity", current.quantity)
            avail = body.get("available_quantity", current.available_quantity)
            if avail > qty:
                raise HTTPException(
                    status_code=400,
                    detail="Available quantity cannot exceed total quantity",
                )
        try:
            response = get_http_client().patch(
                self._url(),
                headers=self._headers(prefer="return=representation"),
                params=[("id", f"eq.{resource_id}")],
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        self._handle(response, "update_resource")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=404, detail="Resource not found")
        return HospitalResourceResponse.model_validate(rows[0])

    def delete_resource(self, resource_id: UUID) -> None:
        self.get_resource(resource_id)
        try:
            response = get_http_client().delete(
                self._url(),
                headers=self._headers(),
                params=[("id", f"eq.{resource_id}")],
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        self._handle(response, "delete_resource")

    def all_rows(self) -> List[Dict[str, Any]]:
        try:
            response = get_http_client().get(
                self._url(),
                headers=self._headers(),
                params=[("select", SELECT), ("order", "resource_type.asc")],
            )
        except httpx.HTTPError:
            return []
        if response.status_code >= 400:
            return []
        rows = response.json()
        return rows if isinstance(rows, list) else []


resource_service = ResourceService()
