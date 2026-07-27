"""
Intake Agent — sole reader of raw uploaded documents.

Converts documents into Patient Context JSON for all downstream agents.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.ai.consumers.diagnosis_interfaces import (
    build_diagnosis_request_from_context,
    patient_context_as_agent_input,
)
from app.ai.intake.pipelines import (
    compute_age_years,
    document_upload_pipeline,
    entity_extraction_pipeline,
    knowledge_graph_builder_pipeline,
    ocr_pipeline,
    patient_context_builder_pipeline,
    risk_profiling_pipeline,
)
from app.ai.intake.patient_context import PatientContext
from app.config import get_settings
from app.core.logging import get_logger
from app.database.http import get_http_client
logger = get_logger("hospital_ai.intake.agent")


class IntakeAgent:
    """UML Intake Agent responsibilities orchestration."""

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

    def _base(self) -> str:
        return get_settings().supabase_url.rstrip("/")

    def _get(self, table: str, params: List[tuple[str, str]]) -> List[Dict[str, Any]]:
        try:
            response = get_http_client().get(
                f"{self._base()}/rest/v1/{table}",
                headers=self._headers(),
                params=params,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        if response.status_code >= 400:
            return []
        rows = response.json()
        return rows if isinstance(rows, list) else []

    def _post(self, table: str, body: Dict[str, Any]) -> Dict[str, Any]:
        response = get_http_client().post(
            f"{self._base()}/rest/v1/{table}",
            headers=self._headers(prefer="return=representation"),
            json=body,
        )
        if response.status_code >= 400:
            logger.error("POST %s failed: %s", table, response.text)
            raise HTTPException(status_code=400, detail=response.text)
        rows = response.json() or []
        return rows[0] if rows else {}

    def _patch(self, table: str, row_id: str, body: Dict[str, Any]) -> None:
        response = get_http_client().patch(
            f"{self._base()}/rest/v1/{table}",
            headers=self._headers(prefer="return=minimal"),
            params=[("id", f"eq.{row_id}")],
            json=body,
        )
        if response.status_code >= 400:
            logger.error("PATCH %s failed: %s", table, response.text)

    def _append_timeline(
        self, timeline: List[Dict[str, Any]], step: str, detail: str
    ) -> List[Dict[str, Any]]:
        timeline.append(
            {
                "step": step,
                "detail": detail,
                "at": datetime.utcnow().isoformat() + "Z",
            }
        )
        return timeline

    def _fetch_patient(self, patient_id: UUID) -> Dict[str, Any]:
        rows = self._get(
            "patients",
            [
                (
                    "select",
                    "id,patient_number,first_name,last_name,date_of_birth,gender,"
                    "blood_group,allergies,medical_history,current_medications,ai_context",
                ),
                ("id", f"eq.{patient_id}"),
            ],
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Patient not found")
        return rows[0]

    def _exists(self, table: str, row_id: Optional[UUID]) -> bool:
        if not row_id:
            return False
        rows = self._get(table, [("select", "id"), ("id", f"eq.{row_id}")])
        return bool(rows)

    def _download_document_bytes(self, storage_path: str) -> bytes:
        from app.services.medical_storage_service import BUCKET

        settings = get_settings()
        url = (
            f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{BUCKET}/{storage_path}"
        )
        try:
            response = get_http_client().get(
                url,
                headers={
                    "apikey": settings.supabase_service_role_key,
                    "Authorization": f"Bearer {settings.supabase_service_role_key}",
                },
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to download document") from exc
        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to download document from storage ({response.status_code})",
            )
        return response.content

    def _collect_medical_history(self, patient: Dict[str, Any], patient_id: UUID) -> str:
        parts: List[str] = []
        if patient.get("medical_history"):
            parts.append(f"Recorded history: {patient['medical_history']}")
        if patient.get("current_medications"):
            parts.append(f"Current medications: {patient['current_medications']}")
        if patient.get("allergies"):
            parts.append(f"Allergies: {patient['allergies']}")

        records = self._get(
            "medical_records",
            [
                (
                    "select",
                    "title,record_type,diagnosis,treatment,notes,created_at",
                ),
                ("patient_id", f"eq.{patient_id}"),
                ("order", "created_at.desc"),
                ("limit", "20"),
            ],
        )
        for r in records:
            parts.append(
                f"[{r.get('record_type')}] {r.get('title')}: "
                f"dx={r.get('diagnosis') or '—'}; tx={r.get('treatment') or '—'}"
            )

        appts = self._get(
            "appointments",
            [
                (
                    "select",
                    "appointment_number,appointment_date,visit_type,reason_for_visit,status",
                ),
                ("patient_id", f"eq.{patient_id}"),
                ("order", "appointment_date.desc"),
                ("limit", "10"),
            ],
        )
        for a in appts:
            parts.append(
                f"Appointment {a.get('appointment_number')} "
                f"({a.get('appointment_date')} {a.get('visit_type')}): "
                f"{a.get('reason_for_visit') or a.get('status')}"
            )
        return "\n".join(parts) if parts else "No prior structured history available."

    def process_document(
        self,
        *,
        document_id: UUID,
        created_by: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        docs = self._get(
            "medical_documents",
            [
                (
                    "select",
                    "id,medical_record_id,file_name,file_url,storage_path,file_type,file_size",
                ),
                ("id", f"eq.{document_id}"),
            ],
        )
        if not docs:
            raise HTTPException(status_code=404, detail="Document not found")
        doc = docs[0]

        records = self._get(
            "medical_records",
            [
                ("select", "id,patient_id,appointment_id,doctor_id,title,record_type"),
                ("id", f"eq.{doc['medical_record_id']}"),
            ],
        )
        if not records:
            raise HTTPException(status_code=404, detail="Medical record not found")
        record = records[0]
        patient_id = UUID(str(record["patient_id"]))
        appointment_id = (
            UUID(str(record["appointment_id"])) if record.get("appointment_id") else None
        )
        doctor_id = UUID(str(record["doctor_id"])) if record.get("doctor_id") else None

        patient = self._fetch_patient(patient_id)
        document_upload_pipeline.validate_registration(
            patient_exists=True,
            appointment_exists=self._exists("appointments", appointment_id),
            doctor_exists=self._exists("doctors", doctor_id),
            require_appointment=False,
            require_doctor=False,
        )

        timeline: List[Dict[str, Any]] = []
        job = self._post(
            "document_processing_jobs",
            {
                "patient_id": str(patient_id),
                "medical_record_id": str(record["id"]),
                "document_id": str(document_id),
                "appointment_id": str(appointment_id) if appointment_id else None,
                "doctor_id": str(doctor_id) if doctor_id else None,
                "status": "Queued",
                "current_step": "Queued",
                "progress_pct": 0,
                "timeline": timeline,
                "created_by": str(created_by) if created_by else None,
                "started_at": datetime.utcnow().isoformat() + "Z",
            },
        )
        job_id = str(job["id"])

        try:
            timeline = self._append_timeline(timeline, "Validating", "Validated patient/record links")
            self._patch(
                "document_processing_jobs",
                job_id,
                {
                    "status": "Validating",
                    "current_step": "Validating",
                    "progress_pct": 10,
                    "timeline": timeline,
                },
            )

            file_bytes = self._download_document_bytes(doc["storage_path"])
            timeline = self._append_timeline(
                timeline, "OCR", f"Running OCR on {doc['file_name']}"
            )
            self._patch(
                "document_processing_jobs",
                job_id,
                {
                    "status": "OCR",
                    "current_step": "OCR",
                    "progress_pct": 30,
                    "timeline": timeline,
                },
            )
            ocr = ocr_pipeline.run(
                file_bytes=file_bytes,
                content_type=doc.get("file_type") or "application/octet-stream",
                file_name=doc.get("file_name") or "document",
            )

            # Mark medical record OCR status
            self._patch(
                "medical_records",
                str(record["id"]),
                {"ocr_status": "completed"},
            )

            timeline = self._append_timeline(
                timeline, "EntityExtraction", "Extracting medical entities"
            )
            self._patch(
                "document_processing_jobs",
                job_id,
                {
                    "status": "EntityExtraction",
                    "current_step": "EntityExtraction",
                    "progress_pct": 50,
                    "ocr_provider": ocr.provider,
                    "ocr_text": ocr.text,
                    "ocr_confidence": ocr.confidence,
                    "timeline": timeline,
                },
            )
            entities = entity_extraction_pipeline.run(ocr.text)

            history = self._collect_medical_history(patient, patient_id)
            age = compute_age_years(patient.get("date_of_birth"))
            allergies = []
            if patient.get("allergies"):
                allergies = [
                    a.strip()
                    for a in str(patient["allergies"]).replace(";", ",").split(",")
                    if a.strip()
                ]

            timeline = self._append_timeline(timeline, "RiskProfiling", "Computing risk profile")
            self._patch(
                "document_processing_jobs",
                job_id,
                {
                    "status": "RiskProfiling",
                    "current_step": "RiskProfiling",
                    "progress_pct": 65,
                    "extracted_entities": entities.to_dict(),
                    "timeline": timeline,
                },
            )
            risk = risk_profiling_pipeline.run(
                entities, allergies=allergies, age_years=age
            )

            timeline = self._append_timeline(
                timeline, "KnowledgeGraph", "Building patient knowledge graph"
            )
            self._patch(
                "document_processing_jobs",
                job_id,
                {
                    "status": "KnowledgeGraph",
                    "current_step": "KnowledgeGraph",
                    "progress_pct": 80,
                    "risk_profile": risk.model_dump(mode="json"),
                    "timeline": timeline,
                },
            )
            graph = knowledge_graph_builder_pipeline.run(
                patient_id=str(patient_id),
                patient_label=f"{patient.get('first_name')} {patient.get('last_name')}".strip(),
                entities=entities,
                risk=risk,
                doctor_ids=[str(doctor_id)] if doctor_id else None,
                appointment_ids=[str(appointment_id)] if appointment_id else None,
                medical_record_ids=[str(record["id"])],
            )

            # Upsert knowledge graph
            existing_graphs = self._get(
                "patient_knowledge_graphs",
                [("select", "id,graph_version"), ("patient_id", f"eq.{patient_id}")],
            )
            graph_payload = {
                "patient_id": str(patient_id),
                "nodes": [n.model_dump(mode="json") for n in graph.nodes],
                "edges": [e.model_dump(mode="json") for e in graph.edges],
                "summary": graph.summary,
            }
            if existing_graphs:
                graph_db_id = str(existing_graphs[0]["id"])
                version = int(existing_graphs[0].get("graph_version") or 1) + 1
                self._patch(
                    "patient_knowledge_graphs",
                    graph_db_id,
                    {**graph_payload, "graph_version": version},
                )
            else:
                created_graph = self._post(
                    "patient_knowledge_graphs", {**graph_payload, "graph_version": 1}
                )
                graph_db_id = str(created_graph["id"])

            timeline = self._append_timeline(
                timeline, "ContextBuild", "Building Patient Context JSON"
            )
            self._patch(
                "document_processing_jobs",
                job_id,
                {
                    "status": "ContextBuild",
                    "current_step": "ContextBuild",
                    "progress_pct": 90,
                    "knowledge_graph_refs": {
                        "graph_id": graph_db_id,
                        "node_count": len(graph.nodes),
                        "edge_count": len(graph.edges),
                    },
                    "timeline": timeline,
                },
            )

            context = patient_context_builder_pipeline.build(
                patient=patient,
                history_text=history,
                entities=entities,
                risk=risk,
                graph=graph,
                source_document_ids=[str(document_id)],
                source_job_ids=[job_id],
                graph_db_id=graph_db_id,
            )
            context_json = context.to_dict()

            # Upsert patient_ai_context
            existing_ctx = self._get(
                "patient_ai_context",
                [("select", "id,context_version,source_job_ids,source_document_ids"), ("patient_id", f"eq.{patient_id}")],
            )
            ctx_body = {
                "patient_id": str(patient_id),
                "context_json": context_json,
                "medical_history_summary": history[:4000],
                "risk_level": risk.risk_level,
                "risk_profile": risk.model_dump(mode="json"),
                "confidence_score": context.confidence_score,
                "knowledge_graph_id": graph_db_id,
                "source_job_ids": [job_id],
                "source_document_ids": [str(document_id)],
                "built_at": datetime.utcnow().isoformat() + "Z",
            }
            if existing_ctx:
                prev_jobs = existing_ctx[0].get("source_job_ids") or []
                prev_docs = existing_ctx[0].get("source_document_ids") or []
                ctx_body["context_version"] = int(existing_ctx[0].get("context_version") or 1) + 1
                ctx_body["source_job_ids"] = list(dict.fromkeys([*prev_jobs, job_id]))
                ctx_body["source_document_ids"] = list(
                    dict.fromkeys([*prev_docs, str(document_id)])
                )
                self._patch("patient_ai_context", str(existing_ctx[0]["id"]), ctx_body)
            else:
                ctx_body["context_version"] = 1
                self._post("patient_ai_context", ctx_body)

            # Mirror onto patients.ai_context for legacy UI
            self._patch(
                "patients",
                str(patient_id),
                {
                    "ai_context": context_json,
                    "latest_diagnosis": ", ".join(context.conditions) or None,
                },
            )

            timeline = self._append_timeline(timeline, "Completed", "Intake pipeline finished")
            self._patch(
                "document_processing_jobs",
                job_id,
                {
                    "status": "Completed",
                    "current_step": "Completed",
                    "progress_pct": 100,
                    "patient_context": context_json,
                    "timeline": timeline,
                    "completed_at": datetime.utcnow().isoformat() + "Z",
                },
            )

            return {
                "job_id": job_id,
                "patient_id": str(patient_id),
                "document_id": str(document_id),
                "status": "Completed",
                "patient_context": context_json,
                "entities": entities.to_dict(),
                "risk_profile": risk.model_dump(mode="json"),
                "knowledge_graph": graph.preview(),
                "ocr": {
                    "provider": ocr.provider,
                    "confidence": ocr.confidence,
                    "text_preview": ocr.text[:500],
                },
                "timeline": timeline,
                "confidence_score": context.confidence_score,
                "diagnosis_request_preview": build_diagnosis_request_from_context(
                    context
                ).model_dump(mode="json"),
            }
        except HTTPException:
            self._patch(
                "document_processing_jobs",
                job_id,
                {
                    "status": "Failed",
                    "current_step": "Failed",
                    "error_message": "HTTP error during intake",
                    "timeline": self._append_timeline(timeline, "Failed", "HTTP error"),
                },
            )
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Intake pipeline failed")
            self._patch(
                "document_processing_jobs",
                job_id,
                {
                    "status": "Failed",
                    "current_step": "Failed",
                    "error_message": str(exc),
                    "timeline": self._append_timeline(timeline, "Failed", str(exc)),
                },
            )
            raise HTTPException(status_code=500, detail=f"Intake pipeline failed: {exc}") from exc

    def get_patient_context(self, patient_id: UUID) -> PatientContext:
        rows = self._get(
            "patient_ai_context",
            [("select", "context_json"), ("patient_id", f"eq.{patient_id}")],
        )
        if not rows or not rows[0].get("context_json"):
            raise HTTPException(
                status_code=404,
                detail="Patient context not built yet. Run Intake on a document first.",
            )
        return PatientContext.model_validate(rows[0]["context_json"])

    def get_agent_input(self, patient_id: UUID) -> Dict[str, Any]:
        """Canonical JSON for Diagnosis / other agents."""
        return patient_context_as_agent_input(self.get_patient_context(patient_id))


intake_agent = IntakeAgent()
