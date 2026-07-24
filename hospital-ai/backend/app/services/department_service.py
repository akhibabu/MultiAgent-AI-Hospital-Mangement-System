"""Department business logic."""

from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.config import get_settings
from app.core.logging import get_logger
from app.database.http import get_http_client
from app.schemas.department import (
    DepartmentCreate,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdate,
)

logger = get_logger("hospital_ai.departments")

DEPARTMENT_SELECT = (
    "id,name,description,floor_number,head_doctor_id,created_at,updated_at"
)


class DepartmentService:
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

    def _base_url(self) -> str:
        return f"{get_settings().supabase_url.rstrip('/')}/rest/v1/departments"

    def _doctors_url(self) -> str:
        return f"{get_settings().supabase_url.rstrip('/')}/rest/v1/doctors"

    def _handle_error(self, response: httpx.Response, action: str) -> None:
        if response.status_code < 400:
            return
        logger.error("%s failed: %s %s", action, response.status_code, response.text)
        detail = "Department operation failed"
        try:
            body = response.json()
            detail = body.get("message") or body.get("error") or detail
        except Exception:  # noqa: BLE001
            pass
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Department not found")
        if response.status_code == 409:
            raise HTTPException(status_code=409, detail="Department name already exists")
        if 400 <= response.status_code < 500:
            raise HTTPException(status_code=400, detail=detail)
        raise HTTPException(status_code=502, detail=detail)

    def _enrich(self, row: Dict[str, Any]) -> DepartmentResponse:
        dept_id = row["id"]
        doctors_count = 0
        head_name = None

        try:
            count_resp = get_http_client().get(
                self._doctors_url(),
                headers={**self._headers(prefer="count=exact"), "Range": "0-0"},
                params=[("select", "id"), ("department_id", f"eq.{dept_id}")],
            )
            if count_resp.status_code < 400:
                cr = count_resp.headers.get("content-range", "")
                if "/" in cr:
                    doctors_count = int(cr.split("/")[-1] or 0)
        except Exception as exc:  # noqa: BLE001
            logger.warning("doctors_count failed: %s", exc)

        head_id = row.get("head_doctor_id")
        if head_id:
            try:
                head_resp = get_http_client().get(
                    self._doctors_url(),
                    headers=self._headers(),
                    params=[
                        ("select", "first_name,last_name"),
                        ("id", f"eq.{head_id}"),
                    ],
                )
                if head_resp.status_code < 400:
                    heads = head_resp.json() or []
                    if heads:
                        head_name = f"{heads[0]['first_name']} {heads[0]['last_name']}"
            except Exception as exc:  # noqa: BLE001
                logger.warning("head doctor lookup failed: %s", exc)

        return DepartmentResponse(
            id=row["id"],
            name=row["name"],
            description=row.get("description"),
            floor_number=row.get("floor_number"),
            head_doctor_id=row.get("head_doctor_id"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            doctors_count=doctors_count,
            patients_count=0,
            head_doctor_name=head_name,
        )

    def list_departments(self, search: Optional[str] = None) -> DepartmentListResponse:
        params: List[tuple[str, str]] = [
            ("select", DEPARTMENT_SELECT),
            ("order", "name.asc"),
        ]
        if search and search.strip():
            term = search.strip()
            params.append(("name", f"ilike.*{term}*"))

        try:
            response = get_http_client().get(
                self._base_url(),
                headers=self._headers(prefer="count=exact"),
                params=params,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc

        self._handle_error(response, "list_departments")
        rows = response.json() or []
        items = [self._enrich(row) for row in rows]
        return DepartmentListResponse(items=items, total=len(items))

    def get_department(self, department_id: UUID) -> DepartmentResponse:
        try:
            response = get_http_client().get(
                self._base_url(),
                headers=self._headers(),
                params=[("select", DEPARTMENT_SELECT), ("id", f"eq.{department_id}")],
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc

        self._handle_error(response, "get_department")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=404, detail="Department not found")
        return self._enrich(rows[0])

    def create_department(self, payload: DepartmentCreate) -> DepartmentResponse:
        body = payload.model_dump(mode="json")
        try:
            response = get_http_client().post(
                self._base_url(),
                headers=self._headers(prefer="return=representation"),
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc

        self._handle_error(response, "create_department")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=502, detail="Department created but no data returned")
        logger.info("Created department %s", rows[0].get("name"))
        return self._enrich(rows[0])

    def update_department(
        self, department_id: UUID, payload: DepartmentUpdate
    ) -> DepartmentResponse:
        body = payload.model_dump(mode="json", exclude_unset=True)
        if not body:
            return self.get_department(department_id)
        try:
            response = get_http_client().patch(
                self._base_url(),
                headers=self._headers(prefer="return=representation"),
                params=[("id", f"eq.{department_id}")],
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc

        self._handle_error(response, "update_department")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=404, detail="Department not found")
        return self._enrich(rows[0])

    def delete_department(self, department_id: UUID) -> None:
        self.get_department(department_id)
        try:
            response = get_http_client().delete(
                self._base_url(),
                headers=self._headers(),
                params=[("id", f"eq.{department_id}")],
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        self._handle_error(response, "delete_department")
        logger.info("Deleted department %s", department_id)


department_service = DepartmentService()
