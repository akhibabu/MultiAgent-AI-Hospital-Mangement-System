"""Doctor business logic against Supabase PostgREST."""

from math import ceil
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.config import get_settings
from app.core.logging import get_logger
from app.database.http import get_http_client
from app.schemas.doctor import (
    AvailabilityStatus,
    DepartmentBrief,
    DoctorCreate,
    DoctorListResponse,
    DoctorResponse,
    DoctorUpdate,
)

logger = get_logger("hospital_ai.doctors")

DOCTOR_SELECT = (
    "id,doctor_number,first_name,last_name,email,phone,gender,date_of_birth,"
    "department_id,specialization,qualification,experience_years,license_number,"
    "consultation_fee,availability_status,profile_photo_url,bio,"
    "ai_summary,performance_metrics,predicted_workload,recommended_schedule,"
    "created_by,created_at,updated_at"
)

SORTABLE = {
    "doctor_number",
    "first_name",
    "last_name",
    "specialization",
    "experience_years",
    "consultation_fee",
    "availability_status",
    "created_at",
    "updated_at",
}


class DoctorService:
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
        return f"{get_settings().supabase_url.rstrip('/')}/rest/v1/doctors"

    def _handle_error(self, response: httpx.Response, action: str) -> None:
        if response.status_code < 400:
            return
        logger.error("%s failed: %s %s", action, response.status_code, response.text)
        detail = "Doctor operation failed"
        try:
            body = response.json()
            detail = body.get("message") or body.get("error") or detail
        except Exception:  # noqa: BLE001
            pass
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Doctor not found")
        if response.status_code == 409:
            raise HTTPException(status_code=409, detail="Conflict (duplicate email or license)")
        if 400 <= response.status_code < 500:
            raise HTTPException(status_code=400, detail=detail)
        raise HTTPException(status_code=502, detail=detail)

    def _to_response(
        self,
        row: Dict[str, Any],
        departments: Optional[Dict[str, DepartmentBrief]] = None,
    ) -> DoctorResponse:
        data = dict(row)
        data.pop("department", None)
        data.pop("departments", None)
        dept_id = data.get("department_id")
        if dept_id and departments and str(dept_id) in departments:
            data["department"] = departments[str(dept_id)]
        else:
            data["department"] = None
        return DoctorResponse.model_validate(data)

    def _load_departments(
        self, department_ids: List[str]
    ) -> Dict[str, DepartmentBrief]:
        unique = [d for d in dict.fromkeys(department_ids) if d]
        if not unique:
            return {}
        settings = get_settings()
        url = f"{settings.supabase_url.rstrip('/')}/rest/v1/departments"
        try:
            response = get_http_client().get(
                url,
                headers=self._headers(),
                params=[
                    ("select", "id,name"),
                    ("id", f"in.({','.join(unique)})"),
                ],
            )
        except httpx.HTTPError:
            return {}
        if response.status_code >= 400:
            return {}
        rows = response.json()
        if not isinstance(rows, list):
            return {}
        return {
            str(row["id"]): DepartmentBrief(id=row["id"], name=row["name"])
            for row in rows
            if isinstance(row, dict)
        }

    def list_doctors(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        department_id: Optional[UUID] = None,
        availability_status: Optional[AvailabilityStatus] = None,
        min_experience: Optional[int] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> DoctorListResponse:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10
        if sort_by not in SORTABLE:
            sort_by = "created_at"
        order = "desc" if sort_order.lower() == "desc" else "asc"

        params: List[tuple[str, str]] = [
            ("select", DOCTOR_SELECT),
            ("order", f"{sort_by}.{order}"),
        ]

        if search:
            tokens = [t for t in search.strip().replace(",", " ").split() if t]
            if tokens:
                or_parts: List[str] = []
                for token in tokens:
                    safe = (
                        token.replace("\\", "\\\\")
                        .replace("*", "\\*")
                        .replace(",", "\\,")
                    )
                    or_parts.extend(
                        [
                            f"first_name.ilike.*{safe}*",
                            f"last_name.ilike.*{safe}*",
                            f"doctor_number.ilike.*{safe}*",
                            f"specialization.ilike.*{safe}*",
                        ]
                    )
                params.append(("or", f"({','.join(or_parts)})"))

        if department_id:
            params.append(("department_id", f"eq.{department_id}"))
        if availability_status:
            params.append(("availability_status", f"eq.{availability_status.value}"))
        if min_experience is not None:
            params.append(("experience_years", f"gte.{min_experience}"))

        offset = (page - 1) * page_size
        headers = self._headers(prefer="count=exact")
        headers["Range-Unit"] = "items"
        headers["Range"] = f"{offset}-{offset + page_size - 1}"

        try:
            response = get_http_client().get(
                self._base_url(), headers=headers, params=params
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc

        self._handle_error(response, "list_doctors")
        total = 0
        cr = response.headers.get("content-range", "")
        if "/" in cr:
            try:
                total = int(cr.split("/")[-1])
            except ValueError:
                total = 0

        rows = response.json()
        if not isinstance(rows, list):
            logger.error("Unexpected doctors payload: %s", rows)
            raise HTTPException(
                status_code=502,
                detail="Unexpected response from database while listing doctors",
            )

        dept_map = self._load_departments(
            [str(row.get("department_id")) for row in rows if isinstance(row, dict)]
        )
        items = [
            self._to_response(row, dept_map)
            for row in rows
            if isinstance(row, dict)
        ]
        total_pages = ceil(total / page_size) if page_size and total else 0
        return DoctorListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_doctor(self, doctor_id: UUID) -> DoctorResponse:
        try:
            response = get_http_client().get(
                self._base_url(),
                headers=self._headers(),
                params=[("select", DOCTOR_SELECT), ("id", f"eq.{doctor_id}")],
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc

        self._handle_error(response, "get_doctor")
        rows = response.json()
        if not isinstance(rows, list) or not rows:
            raise HTTPException(status_code=404, detail="Doctor not found")
        row = rows[0]
        if not isinstance(row, dict):
            raise HTTPException(status_code=502, detail="Unexpected doctor payload")
        dept_map = self._load_departments([str(row.get("department_id") or "")])
        return self._to_response(row, dept_map)

    def create_doctor(self, payload: DoctorCreate, created_by: UUID) -> DoctorResponse:
        body = payload.model_dump(mode="json")
        body["created_by"] = str(created_by)
        try:
            response = get_http_client().post(
                self._base_url(),
                headers=self._headers(prefer="return=representation"),
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc

        self._handle_error(response, "create_doctor")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=502, detail="Doctor created but no data returned")
        # Re-fetch with department embed
        return self.get_doctor(UUID(rows[0]["id"]))

    def update_doctor(self, doctor_id: UUID, payload: DoctorUpdate) -> DoctorResponse:
        body = payload.model_dump(mode="json", exclude_unset=True)
        if not body:
            return self.get_doctor(doctor_id)
        try:
            response = get_http_client().patch(
                self._base_url(),
                headers=self._headers(prefer="return=representation"),
                params=[("id", f"eq.{doctor_id}")],
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc

        self._handle_error(response, "update_doctor")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=404, detail="Doctor not found")
        return self.get_doctor(doctor_id)

    def delete_doctor(self, doctor_id: UUID) -> None:
        self.get_doctor(doctor_id)
        try:
            response = get_http_client().delete(
                self._base_url(),
                headers=self._headers(),
                params=[("id", f"eq.{doctor_id}")],
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        self._handle_error(response, "delete_doctor")
        logger.info("Deleted doctor %s", doctor_id)


doctor_service = DoctorService()
