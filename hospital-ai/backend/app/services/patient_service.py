"""Patient business logic against Supabase (PostgREST)."""

from math import ceil
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.config import get_settings
from app.core.logging import get_logger
from app.database.http import get_http_client
from app.schemas.patient import (
    BloodGroup,
    PatientCreate,
    PatientGender,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)

logger = get_logger("hospital_ai.patients")

PATIENT_SELECT = (
    "id,patient_number,first_name,last_name,date_of_birth,gender,blood_group,"
    "phone,email,address,city,state,country,"
    "emergency_contact_name,emergency_contact_phone,"
    "allergies,medical_history,current_medications,"
    "insurance_provider,insurance_number,"
    "ai_context,latest_diagnosis,latest_report,prediction_history,"
    "created_by,created_at,updated_at"
)

SORTABLE_COLUMNS = {
    "patient_number",
    "first_name",
    "last_name",
    "date_of_birth",
    "gender",
    "blood_group",
    "phone",
    "created_at",
    "updated_at",
}


class PatientService:
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
        settings = get_settings()
        return f"{settings.supabase_url.rstrip('/')}/rest/v1/patients"

    def _handle_http_error(self, response: httpx.Response, action: str) -> None:
        if response.status_code < 400:
            return
        logger.error("%s failed: %s %s", action, response.status_code, response.text)
        detail = "Patient operation failed"
        try:
            body = response.json()
            detail = body.get("message") or body.get("error") or detail
        except Exception:  # noqa: BLE001
            pass
        if response.status_code == 404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
        if response.status_code == 409:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflict while saving patient (duplicate value)",
            )
        if 400 <= response.status_code < 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail,
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )

    def _to_response(self, row: Dict[str, Any]) -> PatientResponse:
        return PatientResponse.model_validate(row)

    def list_patients(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        gender: Optional[PatientGender] = None,
        blood_group: Optional[BloodGroup] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> PatientListResponse:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10
        if sort_by not in SORTABLE_COLUMNS:
            sort_by = "created_at"
        order = "desc" if sort_order.lower() == "desc" else "asc"

        # Use httpx params so values like "AB+" are encoded as AB%2B (not a space).
        query_params: List[tuple[str, str]] = [
            ("select", PATIENT_SELECT),
            ("order", f"{sort_by}.{order}"),
        ]

        if search:
            raw = search.strip().replace(",", " ")
            tokens = [t for t in raw.split() if t]
            if tokens:
                or_parts: List[str] = []
                for token in tokens:
                    # Escape PostgREST reserved filter chars in user input
                    safe = (
                        token.replace("\\", "\\\\")
                        .replace("*", "\\*")
                        .replace(",", "\\,")
                        .replace("(", "\\(")
                        .replace(")", "\\)")
                    )
                    or_parts.extend(
                        [
                            f"first_name.ilike.*{safe}*",
                            f"last_name.ilike.*{safe}*",
                            f"patient_number.ilike.*{safe}*",
                            f"phone.ilike.*{safe}*",
                        ]
                    )
                query_params.append(("or", f"({','.join(or_parts)})"))

        if gender:
            query_params.append(("gender", f"eq.{gender.value}"))
        if blood_group:
            query_params.append(("blood_group", f"eq.{blood_group.value}"))

        offset = (page - 1) * page_size
        headers = self._headers(prefer="count=exact")
        headers["Range-Unit"] = "items"
        headers["Range"] = f"{offset}-{offset + page_size - 1}"

        try:
            response = get_http_client().get(
                self._base_url(),
                headers=headers,
                params=query_params,
            )
        except httpx.HTTPError as exc:
            logger.error("list_patients unreachable: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to reach Supabase",
            ) from exc

        self._handle_http_error(response, "list_patients")

        total = 0
        content_range = response.headers.get("content-range", "")
        # content-range: 0-9/42 or */0
        if "/" in content_range:
            try:
                total = int(content_range.split("/")[-1])
            except ValueError:
                total = 0

        rows = response.json() or []
        items = [self._to_response(row) for row in rows]
        total_pages = ceil(total / page_size) if page_size and total else 0

        return PatientListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_patient(self, patient_id: UUID) -> PatientResponse:
        url = f"{self._base_url()}?id=eq.{patient_id}&select={PATIENT_SELECT}"
        try:
            response = get_http_client().get(url, headers=self._headers())
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to reach Supabase",
            ) from exc

        self._handle_http_error(response, "get_patient")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
        return self._to_response(rows[0])

    def create_patient(self, payload: PatientCreate, created_by: UUID) -> PatientResponse:
        body = payload.model_dump(mode="json")
        body["created_by"] = str(created_by)
        # patient_number is assigned by DB trigger

        try:
            response = get_http_client().post(
                self._base_url(),
                headers=self._headers(prefer="return=representation"),
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to reach Supabase",
            ) from exc

        self._handle_http_error(response, "create_patient")
        rows = response.json() or []
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Patient created but no data returned",
            )
        logger.info("Created patient %s by %s", rows[0].get("patient_number"), created_by)
        return self._to_response(rows[0])

    def update_patient(self, patient_id: UUID, payload: PatientUpdate) -> PatientResponse:
        body = payload.model_dump(mode="json", exclude_unset=True)
        if not body:
            return self.get_patient(patient_id)

        url = f"{self._base_url()}?id=eq.{patient_id}"
        try:
            response = get_http_client().patch(
                url,
                headers=self._headers(prefer="return=representation"),
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to reach Supabase",
            ) from exc

        self._handle_http_error(response, "update_patient")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
        logger.info("Updated patient %s", patient_id)
        return self._to_response(rows[0])

    def delete_patient(self, patient_id: UUID) -> None:
        # Ensure exists first for a clear 404
        self.get_patient(patient_id)
        url = f"{self._base_url()}?id=eq.{patient_id}"
        try:
            response = get_http_client().delete(url, headers=self._headers())
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to reach Supabase",
            ) from exc

        self._handle_http_error(response, "delete_patient")
        logger.info("Deleted patient %s", patient_id)


patient_service = PatientService()
