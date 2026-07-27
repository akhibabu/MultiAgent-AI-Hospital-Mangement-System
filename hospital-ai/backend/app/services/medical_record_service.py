"""Medical records + documents business logic."""

from math import ceil
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.core.logging import get_logger
from app.database.http import get_http_client
from app.schemas.medical_record import (
    AppointmentBrief,
    DoctorBrief,
    MedicalAuditAction,
    MedicalDocumentResponse,
    MedicalRecordAuditListResponse,
    MedicalRecordAuditResponse,
    MedicalRecordCreate,
    MedicalRecordListResponse,
    MedicalRecordResponse,
    MedicalRecordType,
    MedicalRecordUpdate,
    PatientBrief,
)
from app.services.ai_placeholders import (
    get_ocr_service,
    get_embedding_service,
    get_medical_summary_service,
)
from app.services.medical_storage_service import medical_storage_service

logger = get_logger("hospital_ai.medical_records")

RECORD_SELECT = (
    "id,patient_id,appointment_id,doctor_id,record_type,title,description,"
    "diagnosis,treatment,notes,"
    "ai_summary,detected_conditions,risk_score,recommended_tests,"
    "embedding_id,vector_status,ocr_status,"
    "created_by,created_at,updated_at"
)

DOC_SELECT = (
    "id,medical_record_id,file_name,file_url,storage_path,file_type,"
    "file_size,uploaded_by,created_at"
)

SORTABLE = {
    "title",
    "record_type",
    "created_at",
    "updated_at",
}


class MedicalRecordService:
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

    def _records_url(self) -> str:
        return f"{get_settings().supabase_url.rstrip('/')}/rest/v1/medical_records"

    def _docs_url(self) -> str:
        return f"{get_settings().supabase_url.rstrip('/')}/rest/v1/medical_documents"

    def _audit_url(self) -> str:
        return f"{get_settings().supabase_url.rstrip('/')}/rest/v1/medical_record_audit"

    def _handle_error(self, response: httpx.Response, action: str) -> None:
        if response.status_code < 400:
            return
        logger.error("%s failed: %s %s", action, response.status_code, response.text)
        detail = "Medical record operation failed"
        try:
            body = response.json()
            detail = body.get("message") or body.get("error") or detail
        except Exception:  # noqa: BLE001
            pass
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Medical record not found")
        if response.status_code == 409:
            raise HTTPException(status_code=409, detail="Conflict")
        if 400 <= response.status_code < 500:
            raise HTTPException(status_code=400, detail=detail)
        raise HTTPException(status_code=502, detail=detail)

    def _get_json(self, url: str, params: List[tuple[str, str]]) -> Any:
        try:
            response = get_http_client().get(
                url, headers=self._headers(), params=params
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase"
            ) from exc
        if response.status_code >= 400:
            return None
        return response.json()

    def _write_audit(
        self,
        *,
        record_id: Optional[UUID],
        action: MedicalAuditAction,
        performed_by: Optional[UUID],
        document_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        body = {
            "record_id": str(record_id) if record_id else None,
            "document_id": str(document_id) if document_id else None,
            "action": action.value,
            "performed_by": str(performed_by) if performed_by else None,
            "details": details,
        }
        try:
            response = get_http_client().post(
                self._audit_url(),
                headers=self._headers(prefer="return=minimal"),
                json=body,
            )
            if response.status_code >= 400:
                logger.warning("Audit write failed: %s", response.text)
        except httpx.HTTPError:
            logger.warning("Audit write unreachable", exc_info=True)

    def _ensure_patient(self, patient_id: UUID) -> None:
        settings = get_settings()
        url = f"{settings.supabase_url.rstrip('/')}/rest/v1/patients"
        rows = self._get_json(url, [("select", "id"), ("id", f"eq.{patient_id}")])
        if not isinstance(rows, list) or not rows:
            raise HTTPException(status_code=400, detail="Patient not found")

    def _ensure_doctor(self, doctor_id: Optional[UUID]) -> None:
        if not doctor_id:
            return
        settings = get_settings()
        url = f"{settings.supabase_url.rstrip('/')}/rest/v1/doctors"
        rows = self._get_json(url, [("select", "id"), ("id", f"eq.{doctor_id}")])
        if not isinstance(rows, list) or not rows:
            raise HTTPException(status_code=400, detail="Doctor not found")

    def _ensure_appointment(self, appointment_id: Optional[UUID]) -> None:
        if not appointment_id:
            return
        settings = get_settings()
        url = f"{settings.supabase_url.rstrip('/')}/rest/v1/appointments"
        rows = self._get_json(url, [("select", "id"), ("id", f"eq.{appointment_id}")])
        if not isinstance(rows, list) or not rows:
            raise HTTPException(status_code=400, detail="Appointment not found")

    def _load_briefs(
        self, rows: List[Dict[str, Any]]
    ) -> Tuple[
        Dict[str, PatientBrief],
        Dict[str, DoctorBrief],
        Dict[str, AppointmentBrief],
    ]:
        patient_ids = list(
            dict.fromkeys(str(r["patient_id"]) for r in rows if r.get("patient_id"))
        )
        doctor_ids = list(
            dict.fromkeys(str(r["doctor_id"]) for r in rows if r.get("doctor_id"))
        )
        appt_ids = list(
            dict.fromkeys(
                str(r["appointment_id"]) for r in rows if r.get("appointment_id")
            )
        )
        settings = get_settings()
        patients: Dict[str, PatientBrief] = {}
        doctors: Dict[str, DoctorBrief] = {}
        appointments: Dict[str, AppointmentBrief] = {}

        if patient_ids:
            data = self._get_json(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/patients",
                [
                    ("select", "id,patient_number,first_name,last_name"),
                    ("id", f"in.({','.join(patient_ids)})"),
                ],
            )
            if isinstance(data, list):
                for row in data:
                    if isinstance(row, dict):
                        patients[str(row["id"])] = PatientBrief.model_validate(row)

        if doctor_ids:
            data = self._get_json(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/doctors",
                [
                    ("select", "id,doctor_number,first_name,last_name"),
                    ("id", f"in.({','.join(doctor_ids)})"),
                ],
            )
            if isinstance(data, list):
                for row in data:
                    if isinstance(row, dict):
                        doctors[str(row["id"])] = DoctorBrief.model_validate(row)

        if appt_ids:
            data = self._get_json(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/appointments",
                [
                    ("select", "id,appointment_number,appointment_date"),
                    ("id", f"in.({','.join(appt_ids)})"),
                ],
            )
            if isinstance(data, list):
                for row in data:
                    if isinstance(row, dict):
                        appointments[str(row["id"])] = AppointmentBrief.model_validate(
                            {
                                "id": row["id"],
                                "appointment_number": row["appointment_number"],
                                "appointment_date": str(row.get("appointment_date") or ""),
                            }
                        )

        return patients, doctors, appointments

    def _list_documents(
        self, record_ids: List[str], *, with_signed: bool = False
    ) -> Dict[str, List[MedicalDocumentResponse]]:
        if not record_ids:
            return {}
        rows = self._get_json(
            self._docs_url(),
            [
                ("select", DOC_SELECT),
                ("medical_record_id", f"in.({','.join(record_ids)})"),
                ("order", "created_at.desc"),
            ],
        )
        result: Dict[str, List[MedicalDocumentResponse]] = {rid: [] for rid in record_ids}
        if not isinstance(rows, list):
            return result
        for row in rows:
            if not isinstance(row, dict):
                continue
            doc = MedicalDocumentResponse.model_validate(row)
            if with_signed:
                try:
                    doc.signed_url = medical_storage_service.create_signed_url(
                        doc.storage_path
                    )
                except HTTPException:
                    doc.signed_url = doc.file_url
            result.setdefault(str(doc.medical_record_id), []).append(doc)
        return result

    def _to_response(
        self,
        row: Dict[str, Any],
        patients: Dict[str, PatientBrief],
        doctors: Dict[str, DoctorBrief],
        appointments: Dict[str, AppointmentBrief],
        documents: Optional[List[MedicalDocumentResponse]] = None,
    ) -> MedicalRecordResponse:
        data = dict(row)
        pid = str(data.get("patient_id") or "")
        did = str(data.get("doctor_id") or "")
        aid = str(data.get("appointment_id") or "")
        data["patient"] = patients.get(pid)
        data["doctor"] = doctors.get(did) if did else None
        data["appointment"] = appointments.get(aid) if aid else None
        data["documents"] = documents or []
        return MedicalRecordResponse.model_validate(data)

    def list_records(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        patient_id: Optional[UUID] = None,
        doctor_id: Optional[UUID] = None,
        appointment_id: Optional[UUID] = None,
        record_type: Optional[MedicalRecordType] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> MedicalRecordListResponse:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10
        if sort_by not in SORTABLE:
            sort_by = "created_at"
        order = "desc" if sort_order.lower() == "desc" else "asc"

        params: List[tuple[str, str]] = [
            ("select", RECORD_SELECT),
            ("order", f"{sort_by}.{order}"),
        ]
        if patient_id:
            params.append(("patient_id", f"eq.{patient_id}"))
        if doctor_id:
            params.append(("doctor_id", f"eq.{doctor_id}"))
        if appointment_id:
            params.append(("appointment_id", f"eq.{appointment_id}"))
        if record_type:
            params.append(("record_type", f"eq.{record_type.value}"))
        if date_from:
            params.append(("created_at", f"gte.{date_from}T00:00:00Z"))
        if date_to:
            params.append(("created_at", f"lte.{date_to}T23:59:59Z"))

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
                            f"title.ilike.*{safe}*",
                            f"diagnosis.ilike.*{safe}*",
                            f"treatment.ilike.*{safe}*",
                            f"notes.ilike.*{safe}*",
                            f"description.ilike.*{safe}*",
                        ]
                    )
                params.append(("or", f"({','.join(or_parts)})"))

        offset = (page - 1) * page_size
        headers = self._headers(prefer="count=exact")
        headers["Range-Unit"] = "items"
        headers["Range"] = f"{offset}-{offset + page_size - 1}"

        try:
            response = get_http_client().get(
                self._records_url(), headers=headers, params=params
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase"
            ) from exc

        self._handle_error(response, "list_medical_records")
        total = 0
        cr = response.headers.get("content-range", "")
        if "/" in cr:
            try:
                total = int(cr.split("/")[-1])
            except ValueError:
                total = 0

        rows = response.json()
        if not isinstance(rows, list):
            raise HTTPException(status_code=502, detail="Unexpected records payload")
        dict_rows = [r for r in rows if isinstance(r, dict)]
        patients, doctors, appointments = self._load_briefs(dict_rows)
        docs_map = self._list_documents([str(r["id"]) for r in dict_rows])
        items = [
            self._to_response(
                r,
                patients,
                doctors,
                appointments,
                docs_map.get(str(r["id"]), []),
            )
            for r in dict_rows
        ]
        total_pages = ceil(total / page_size) if page_size and total else 0
        return MedicalRecordListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_record(self, record_id: UUID) -> MedicalRecordResponse:
        try:
            response = get_http_client().get(
                self._records_url(),
                headers=self._headers(),
                params=[("select", RECORD_SELECT), ("id", f"eq.{record_id}")],
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase"
            ) from exc

        self._handle_error(response, "get_medical_record")
        rows = response.json()
        if not isinstance(rows, list) or not rows:
            raise HTTPException(status_code=404, detail="Medical record not found")
        row = rows[0]
        if not isinstance(row, dict):
            raise HTTPException(status_code=502, detail="Unexpected record payload")
        patients, doctors, appointments = self._load_briefs([row])
        docs = self._list_documents([str(record_id)], with_signed=True).get(
            str(record_id), []
        )
        return self._to_response(row, patients, doctors, appointments, docs)

    def create_record(
        self, payload: MedicalRecordCreate, created_by: UUID
    ) -> MedicalRecordResponse:
        self._ensure_patient(payload.patient_id)
        self._ensure_doctor(payload.doctor_id)
        self._ensure_appointment(payload.appointment_id)

        body = payload.model_dump(mode="json")
        body["created_by"] = str(created_by)
        # RAG placeholders default
        body["ocr_status"] = "pending"
        body["vector_status"] = "pending"

        try:
            response = get_http_client().post(
                self._records_url(),
                headers=self._headers(prefer="return=representation"),
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase"
            ) from exc

        self._handle_error(response, "create_medical_record")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=502, detail="Record created but no data returned")
        created = self.get_record(UUID(rows[0]["id"]))
        self._write_audit(
            record_id=created.id,
            action=MedicalAuditAction.CREATED,
            performed_by=created_by,
            details={"title": created.title, "record_type": created.record_type.value},
        )
        # DI hooks for future RAG (no-op stubs)
        get_medical_summary_service().summarize_record(record_id=created.id)
        return created

    def update_record(
        self, record_id: UUID, payload: MedicalRecordUpdate, updated_by: UUID
    ) -> MedicalRecordResponse:
        existing = self.get_record(record_id)
        body = payload.model_dump(mode="json", exclude_unset=True)
        if not body:
            return existing
        if "patient_id" in body:
            self._ensure_patient(UUID(str(body["patient_id"])))
        if "doctor_id" in body:
            self._ensure_doctor(
                UUID(str(body["doctor_id"])) if body["doctor_id"] else None
            )
        if "appointment_id" in body:
            self._ensure_appointment(
                UUID(str(body["appointment_id"])) if body["appointment_id"] else None
            )

        try:
            response = get_http_client().patch(
                self._records_url(),
                headers=self._headers(prefer="return=representation"),
                params=[("id", f"eq.{record_id}")],
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase"
            ) from exc

        self._handle_error(response, "update_medical_record")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=404, detail="Medical record not found")
        updated = self.get_record(record_id)
        self._write_audit(
            record_id=record_id,
            action=MedicalAuditAction.UPDATED,
            performed_by=updated_by,
            details={"fields": list(body.keys())},
        )
        return updated

    def delete_record(self, record_id: UUID, deleted_by: UUID) -> None:
        existing = self.get_record(record_id)
        for doc in existing.documents:
            medical_storage_service.delete_object(doc.storage_path)

        try:
            response = get_http_client().delete(
                self._records_url(),
                headers=self._headers(),
                params=[("id", f"eq.{record_id}")],
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase"
            ) from exc

        self._handle_error(response, "delete_medical_record")
        self._write_audit(
            record_id=record_id,
            action=MedicalAuditAction.DELETED,
            performed_by=deleted_by,
            details={"title": existing.title},
        )

    def upload_document(
        self,
        *,
        medical_record_id: UUID,
        filename: str,
        content_type: str,
        data: bytes,
        uploaded_by: UUID,
    ) -> MedicalDocumentResponse:
        record = self.get_record(medical_record_id)
        size = len(data)
        mime = medical_storage_service.validate_file(
            filename=filename or "upload.bin",
            content_type=content_type or "",
            size=size,
        )
        safe_filename = filename or "upload.bin"

        existing_docs = self._list_documents([str(medical_record_id)]).get(
            str(medical_record_id), []
        )
        for doc in existing_docs:
            if doc.file_name == safe_filename and doc.file_size == size:
                raise HTTPException(
                    status_code=409,
                    detail="Duplicate upload: same file name and size already exists on this record",
                )

        storage_path = medical_storage_service.build_storage_path(
            patient_id=str(record.patient_id),
            appointment_id=str(record.appointment_id)
            if record.appointment_id
            else None,
            filename=safe_filename,
        )
        file_url = medical_storage_service.upload_bytes(
            storage_path=storage_path, data=data, content_type=mime
        )

        body = {
            "medical_record_id": str(medical_record_id),
            "file_name": safe_filename,
            "file_url": file_url,
            "storage_path": storage_path,
            "file_type": mime,
            "file_size": size,
            "uploaded_by": str(uploaded_by),
        }
        try:
            response = get_http_client().post(
                self._docs_url(),
                headers=self._headers(prefer="return=representation"),
                json=body,
            )
        except httpx.HTTPError as exc:
            medical_storage_service.delete_object(storage_path)
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase"
            ) from exc

        if response.status_code >= 400:
            medical_storage_service.delete_object(storage_path)
            self._handle_error(response, "create_medical_document")

        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=502, detail="Document metadata not saved")
        doc = MedicalDocumentResponse.model_validate(rows[0])
        try:
            doc.signed_url = medical_storage_service.create_signed_url(doc.storage_path)
        except HTTPException:
            doc.signed_url = doc.file_url

        self._write_audit(
            record_id=medical_record_id,
            action=MedicalAuditAction.UPLOADED_FILE,
            performed_by=uploaded_by,
            document_id=doc.id,
            details={"file_name": doc.file_name, "file_size": doc.file_size},
        )

        # Intake Agent is the sole component allowed to OCR / extract entities.
        get_ocr_service().enqueue(document_id=doc.id, storage_path=doc.storage_path)
        get_embedding_service().embed_document(document_id=doc.id)

        try:
            get_http_client().patch(
                self._records_url(),
                headers=self._headers(prefer="return=minimal"),
                params=[("id", f"eq.{medical_record_id}")],
                json={"ocr_status": "queued"},
            )
        except httpx.HTTPError:
            pass

        return doc

    def get_document(self, document_id: UUID) -> MedicalDocumentResponse:
        rows = self._get_json(
            self._docs_url(),
            [("select", DOC_SELECT), ("id", f"eq.{document_id}")],
        )
        if not isinstance(rows, list) or not rows:
            raise HTTPException(status_code=404, detail="Document not found")
        doc = MedicalDocumentResponse.model_validate(rows[0])
        try:
            doc.signed_url = medical_storage_service.create_signed_url(doc.storage_path)
        except HTTPException:
            doc.signed_url = doc.file_url
        return doc

    def delete_document(self, document_id: UUID, deleted_by: UUID) -> None:
        doc = self.get_document(document_id)
        medical_storage_service.delete_object(doc.storage_path)
        try:
            response = get_http_client().delete(
                self._docs_url(),
                headers=self._headers(),
                params=[("id", f"eq.{document_id}")],
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase"
            ) from exc
        self._handle_error(response, "delete_medical_document")
        self._write_audit(
            record_id=doc.medical_record_id,
            action=MedicalAuditAction.DELETED_FILE,
            performed_by=deleted_by,
            document_id=document_id,
            details={"file_name": doc.file_name},
        )

    def list_audit(self, record_id: UUID) -> MedicalRecordAuditListResponse:
        self.get_record(record_id)
        rows = self._get_json(
            self._audit_url(),
            [
                (
                    "select",
                    "id,record_id,document_id,action,performed_by,details,timestamp",
                ),
                ("record_id", f"eq.{record_id}"),
                ("order", "timestamp.desc"),
            ],
        )
        if not isinstance(rows, list):
            return MedicalRecordAuditListResponse(items=[], total=0)
        items = [
            MedicalRecordAuditResponse.model_validate(r)
            for r in rows
            if isinstance(r, dict)
        ]
        return MedicalRecordAuditListResponse(items=items, total=len(items))


medical_record_service = MedicalRecordService()
