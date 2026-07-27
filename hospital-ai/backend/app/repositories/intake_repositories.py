"""Supabase REST repository helpers for Intake Patient Registration."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.core.logging import get_logger
from app.database.http import get_http_client

logger = get_logger("hospital_ai.repositories.intake")


class SupabaseRestRepository:
    """Shared HTTP access for PostgREST tables (service-role)."""

    def __init__(self, table: str) -> None:
        self.table = table

    def _settings(self):
        settings = get_settings()
        settings.require_supabase()
        return settings

    def _headers(self, prefer: Optional[str] = None) -> Dict[str, str]:
        settings = self._settings()
        headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _url(self) -> str:
        return f"{self._settings().supabase_url.rstrip('/')}/rest/v1/{self.table}"

    def select(
        self,
        params: List[tuple[str, str]],
    ) -> List[Dict[str, Any]]:
        try:
            response = get_http_client().get(
                self._url(),
                headers=self._headers(),
                params=params,
            )
        except httpx.HTTPError as exc:
            logger.error("GET %s failed: %s", self.table, exc)
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        if response.status_code >= 400:
            logger.error("GET %s error: %s %s", self.table, response.status_code, response.text)
            # Surface PostgREST message when useful (e.g. unknown column)
            detail = f"Failed to query {self.table}"
            try:
                body = response.json()
                msg = body.get("message") or body.get("hint") or body.get("details")
                if isinstance(msg, str) and msg.strip():
                    detail = f"{detail}: {msg}"
            except Exception:  # noqa: BLE001
                pass
            raise HTTPException(status_code=502, detail=detail)
        rows = response.json()
        return rows if isinstance(rows, list) else []

    def insert(self, body: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = get_http_client().post(
                self._url(),
                headers=self._headers(prefer="return=representation"),
                json=body,
            )
        except httpx.HTTPError as exc:
            logger.error("POST %s failed: %s", self.table, exc)
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        if response.status_code >= 400:
            logger.error("POST %s error: %s", self.table, response.text)
            raise HTTPException(status_code=400, detail=response.text)
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=502, detail=f"{self.table} insert returned empty")
        return rows[0]

    def update(self, row_id: UUID, body: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = get_http_client().patch(
                self._url(),
                headers=self._headers(prefer="return=representation"),
                params=[("id", f"eq.{row_id}")],
                json=body,
            )
        except httpx.HTTPError as exc:
            logger.error("PATCH %s failed: %s", self.table, exc)
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        if response.status_code >= 400:
            logger.error("PATCH %s error: %s", self.table, response.text)
            raise HTTPException(status_code=400, detail=response.text)
        rows = response.json() or []
        return rows[0] if rows else {}

    def get_by_id(self, row_id: UUID, select: str = "*") -> Optional[Dict[str, Any]]:
        rows = self.select([("select", select), ("id", f"eq.{row_id}"), ("limit", "1")])
        return rows[0] if rows else None


class PatientRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("patients")

    def get(self, patient_id: UUID) -> Optional[Dict[str, Any]]:
        return self.get_by_id(
            patient_id,
            select="id,patient_number,first_name,last_name",
        )

    def get_full(self, patient_id: UUID) -> Optional[Dict[str, Any]]:
        return self.get_by_id(
            patient_id,
            select=(
                "id,patient_number,first_name,last_name,date_of_birth,gender,"
                "blood_group,phone,email,address,city,state,country,"
                "allergies,medical_history,current_medications,"
                "insurance_provider,insurance_number,latest_diagnosis,"
                "ai_context,created_at,updated_at"
            ),
        )


class DoctorRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("doctors")

    def get(self, doctor_id: UUID) -> Optional[Dict[str, Any]]:
        return self.get_by_id(
            doctor_id,
            select="id,doctor_number,first_name,last_name,availability_status",
        )

    def get_many(self, doctor_ids: List[UUID]) -> List[Dict[str, Any]]:
        if not doctor_ids:
            return []
        ids = ",".join(str(d) for d in dict.fromkeys(doctor_ids))
        return self.select(
            [
                (
                    "select",
                    "id,doctor_number,first_name,last_name,specialization,"
                    "department_id,qualification",
                ),
                ("id", f"in.({ids})"),
            ]
        )


class DepartmentRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("departments")

    def get_many(self, department_ids: List[UUID]) -> List[Dict[str, Any]]:
        if not department_ids:
            return []
        ids = ",".join(str(d) for d in dict.fromkeys(department_ids))
        return self.select(
            [
                ("select", "id,name,description,floor_number"),
                ("id", f"in.({ids})"),
            ]
        )


class AppointmentRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("appointments")

    def get(self, appointment_id: UUID) -> Optional[Dict[str, Any]]:
        return self.get_by_id(
            appointment_id,
            select="id,appointment_number,patient_id,doctor_id,appointment_date,status",
        )

    def list_for_patient(self, patient_id: UUID, limit: int = 100) -> List[Dict[str, Any]]:
        return self.select(
            [
                (
                    "select",
                    "id,appointment_number,patient_id,doctor_id,department_id,"
                    "appointment_date,start_time,end_time,status,visit_type,"
                    "reason_for_visit,notes,created_at",
                ),
                ("patient_id", f"eq.{patient_id}"),
                ("order", "appointment_date.desc"),
                ("limit", str(limit)),
            ]
        )


class MedicalRecordRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("medical_records")

    def list_for_patient(self, patient_id: UUID, limit: int = 200) -> List[Dict[str, Any]]:
        return self.select(
            [
                (
                    "select",
                    "id,patient_id,appointment_id,doctor_id,record_type,title,"
                    "description,diagnosis,treatment,notes,created_at,updated_at",
                ),
                ("patient_id", f"eq.{patient_id}"),
                ("order", "created_at.desc"),
                ("limit", str(limit)),
            ]
        )


class MedicalDocumentRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("medical_documents")

    def list_for_record_ids(
        self, record_ids: List[UUID], limit: int = 200
    ) -> List[Dict[str, Any]]:
        if not record_ids:
            return []
        ids = ",".join(str(r) for r in dict.fromkeys(record_ids))
        return self.select(
            [
                (
                    "select",
                    "id,medical_record_id,file_name,file_url,file_type,file_size,created_at",
                ),
                ("medical_record_id", f"in.({ids})"),
                ("order", "created_at.desc"),
                ("limit", str(limit)),
            ]
        )


class DocumentProcessingJobRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("document_processing_jobs")

    def find_duplicate(
        self,
        *,
        patient_id: UUID,
        document_name: str,
        file_size: int,
    ) -> Optional[Dict[str, Any]]:
        rows = self.select(
            [
                ("select", "id,document_name,status,created_at"),
                ("patient_id", f"eq.{patient_id}"),
                ("document_name", f"eq.{document_name}"),
                ("file_size", f"eq.{file_size}"),
                ("limit", "1"),
            ]
        )
        return rows[0] if rows else None

    def create(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.insert(body)

    def list_for_patient(self, patient_id: UUID, limit: int = 20) -> List[Dict[str, Any]]:
        return self.select(
            [
                ("select", "*"),
                ("patient_id", f"eq.{patient_id}"),
                ("order", "created_at.desc"),
                ("limit", str(limit)),
            ]
        )

    def latest_for_patient(self, patient_id: UUID) -> Optional[Dict[str, Any]]:
        rows = self.list_for_patient(patient_id, limit=1)
        return rows[0] if rows else None


class PatientAIContextRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("patient_ai_context")

    def get_by_patient(self, patient_id: UUID) -> Optional[Dict[str, Any]]:
        rows = self.select(
            [
                ("select", "*"),
                ("patient_id", f"eq.{patient_id}"),
                ("limit", "1"),
            ]
        )
        return rows[0] if rows else None

    def create(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.insert(body)

    def upsert_for_patient(
        self,
        *,
        patient_id: UUID,
        processing_job_id: UUID,
        status: str,
        current_summary: str,
    ) -> Dict[str, Any]:
        existing = self.get_by_patient(patient_id)
        payload = {
            "processing_job_id": str(processing_job_id),
            "status": status,
            "current_summary": current_summary,
        }
        if existing:
            return self.update(UUID(str(existing["id"])), payload)
        return self.create(
            {
                "patient_id": str(patient_id),
                **payload,
            }
        )


class PatientMedicalHistoryRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("patient_medical_history")

    def get_by_patient(self, patient_id: UUID) -> Optional[Dict[str, Any]]:
        rows = self.select(
            [
                ("select", "*"),
                ("patient_id", f"eq.{patient_id}"),
                ("limit", "1"),
            ]
        )
        return rows[0] if rows else None

    def upsert(
        self,
        *,
        patient_id: UUID,
        processing_job_id: UUID,
        medical_history_json: Dict[str, Any],
        timeline_json: List[Any],
    ) -> Dict[str, Any]:
        existing = self.get_by_patient(patient_id)
        payload = {
            "processing_job_id": str(processing_job_id),
            "medical_history_json": medical_history_json,
            "timeline_json": timeline_json,
            "last_updated": datetime_utcnow_iso(),
        }
        if existing:
            return self.update(UUID(str(existing["id"])), payload)
        return self.create(
            {
                "patient_id": str(patient_id),
                **payload,
            }
        )

    def create(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.insert(body)


def datetime_utcnow_iso() -> str:
    from datetime import datetime

    return datetime.utcnow().isoformat() + "Z"

