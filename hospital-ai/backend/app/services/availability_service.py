"""Doctor availability business logic."""

from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.core.logging import get_logger
from app.database.http import get_http_client
from app.schemas.availability import (
    AvailabilityCreate,
    AvailabilityListResponse,
    AvailabilityResponse,
    AvailabilityUpdate,
)

logger = get_logger("hospital_ai.availability")

AVAIL_SELECT = (
    "id,doctor_id,day_of_week,start_time,end_time,slot_duration,"
    "is_available,created_at,updated_at"
)


class AvailabilityService:
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
        return f"{get_settings().supabase_url.rstrip('/')}/rest/v1/doctor_availability"

    def _handle_error(self, response: httpx.Response, action: str) -> None:
        if response.status_code < 400:
            return
        logger.error("%s failed: %s %s", action, response.status_code, response.text)
        detail = "Availability operation failed"
        try:
            body = response.json()
            detail = body.get("message") or body.get("error") or detail
        except Exception:  # noqa: BLE001
            pass
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Availability slot not found")
        if response.status_code == 409:
            raise HTTPException(status_code=409, detail="Overlapping availability slot")
        if 400 <= response.status_code < 500:
            raise HTTPException(status_code=400, detail=detail)
        raise HTTPException(status_code=502, detail=detail)

    def _to_response(self, row: Dict[str, Any]) -> AvailabilityResponse:
        return AvailabilityResponse.model_validate(row)

    def list_for_doctor(self, doctor_id: UUID) -> AvailabilityListResponse:
        try:
            response = get_http_client().get(
                self._base_url(),
                headers=self._headers(),
                params=[
                    ("select", AVAIL_SELECT),
                    ("doctor_id", f"eq.{doctor_id}"),
                    ("order", "day_of_week.asc,start_time.asc"),
                ],
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc

        self._handle_error(response, "list_availability")
        rows = response.json() or []
        items = [self._to_response(row) for row in rows]
        return AvailabilityListResponse(items=items, total=len(items))

    def create(self, payload: AvailabilityCreate) -> AvailabilityResponse:
        body = payload.model_dump(mode="json")
        try:
            response = get_http_client().post(
                self._base_url(),
                headers=self._headers(prefer="return=representation"),
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc

        self._handle_error(response, "create_availability")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=502, detail="Slot created but no data returned")
        return self._to_response(rows[0])

    def update(self, slot_id: UUID, payload: AvailabilityUpdate) -> AvailabilityResponse:
        body = payload.model_dump(mode="json", exclude_unset=True)
        if not body:
            raise HTTPException(status_code=400, detail="No fields to update")
        try:
            response = get_http_client().patch(
                self._base_url(),
                headers=self._headers(prefer="return=representation"),
                params=[("id", f"eq.{slot_id}")],
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc

        self._handle_error(response, "update_availability")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=404, detail="Availability slot not found")
        return self._to_response(rows[0])

    def delete(self, slot_id: UUID) -> None:
        try:
            response = get_http_client().delete(
                self._base_url(),
                headers=self._headers(prefer="return=representation"),
                params=[("id", f"eq.{slot_id}")],
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc

        self._handle_error(response, "delete_availability")
        rows = response.json() if response.content else []
        if response.status_code == 200 and rows == []:
            # Some PostgREST configs return empty on delete without prefer
            pass
        logger.info("Deleted availability %s", slot_id)


availability_service = AvailabilityService()
