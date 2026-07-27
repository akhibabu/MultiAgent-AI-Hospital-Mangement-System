"""Medical Entity Recognition repository + context/status updaters."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException

from app.repositories.intake_repositories import (
    DocumentProcessingJobRepository,
    PatientAIContextRepository,
    SupabaseRestRepository,
)
from app.repositories.ocr_repository import OCRRepository


class MedicalEntityRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("medical_entities")

    def create_many(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not rows:
            return []
        out: List[Dict[str, Any]] = []
        # Insert in small batches for PostgREST reliability
        batch_size = 50
        for i in range(0, len(rows), batch_size):
            chunk = rows[i : i + batch_size]
            try:
                response_rows = self._insert_many(chunk)
                out.extend(response_rows)
            except HTTPException:
                # Fallback: insert one-by-one
                for row in chunk:
                    out.append(self.insert(row))
        return out

    def _insert_many(self, body: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        import httpx
        from app.database.http import get_http_client

        try:
            response = get_http_client().post(
                self._url(),
                headers=self._headers(prefer="return=representation"),
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to insert medical_entities: {response.text[:300]}",
            )
        data = response.json()
        return data if isinstance(data, list) else [data]

    def list_for_job(self, job_id: UUID) -> List[Dict[str, Any]]:
        return self.select(
            [
                ("select", "*"),
                ("processing_job_id", f"eq.{job_id}"),
                ("order", "created_at.asc"),
            ]
        )

    def delete_for_job(self, job_id: UUID) -> None:
        """Allow re-run of NER for the same job."""
        import httpx
        from app.database.http import get_http_client

        try:
            get_http_client().delete(
                self._url(),
                headers=self._headers(),
                params=[("processing_job_id", f"eq.{job_id}")],
            )
        except httpx.HTTPError:
            pass


class MedicalEntityResultRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("medical_entity_results")

    def create(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.insert(body)

    def get_by_job(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        rows = self.select(
            [
                ("select", "*"),
                ("processing_job_id", f"eq.{job_id}"),
                ("limit", "1"),
            ]
        )
        return rows[0] if rows else None

    def upsert_for_job(self, job_id: UUID, body: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.get_by_job(job_id)
        if existing:
            return self.update(UUID(str(existing["id"])), body)
        return self.insert({**body, "processing_job_id": str(job_id)})


class NERStatusUpdater:
    STAGE_NER = "Medical Entity Recognition"
    STAGE_RISK = "Patient Risk Profiling"

    def __init__(self, jobs: Optional[DocumentProcessingJobRepository] = None) -> None:
        self._jobs = jobs or DocumentProcessingJobRepository()

    def get_job(self, job_id: UUID) -> Dict[str, Any]:
        row = self._jobs.get_by_id(job_id)
        if not row:
            raise HTTPException(status_code=404, detail="Processing job not found")
        return row

    def mark_ner_running(self, job_id: UUID) -> Dict[str, Any]:
        return self._jobs.update(
            job_id,
            {
                "status": "Processing",
                "current_stage": self.STAGE_NER,
                "error_message": None,
            },
        )

    def mark_ner_failed(self, job_id: UUID, error: str) -> Dict[str, Any]:
        return self._jobs.update(
            job_id,
            {
                "status": "Failed",
                "current_stage": self.STAGE_NER,
                "error_message": error[:2000],
            },
        )

    def mark_ner_complete(self, job_id: UUID) -> Dict[str, Any]:
        """NER done → advance stage marker to Risk Profiling (not executed)."""
        return self._jobs.update(
            job_id,
            {
                "status": "Processing",
                "current_stage": self.STAGE_RISK,
                "error_message": None,
            },
        )


class NERContextUpdater:
    """Append recognized entities into patient_ai_context (preserve history + OCR)."""

    def __init__(
        self,
        *,
        contexts: Optional[PatientAIContextRepository] = None,
    ) -> None:
        self._contexts = contexts or PatientAIContextRepository()

    def append_entities(
        self,
        *,
        patient_id: UUID,
        processing_job_id: UUID,
        entities_payload: Dict[str, Any],
        confidence: float,
        entity_count: int,
    ) -> Dict[str, Any]:
        row = self._contexts.get_by_patient(patient_id)
        context: Dict[str, Any] = {}
        if row and isinstance(row.get("patient_context_json"), dict):
            context = dict(row["patient_context_json"])

        meta = dict(context.get("metadata") or {})
        version = int(meta.get("version") or 1) + 1
        stamp = datetime.utcnow().isoformat() + "Z"

        sources = list(meta.get("data_sources") or [])
        sources.append(
            {
                "type": "ner",
                "processing_job_id": str(processing_job_id),
                "entity_count": entity_count,
                "at": stamp,
            }
        )

        summary = entities_payload.get("summary") or {}
        stats = entities_payload.get("statistics") or {}

        context["medical_entities"] = entities_payload.get("entities") or []
        context["ner_result"] = entities_payload
        context["recognized_diseases"] = summary.get("conditions") or []
        context["recognized_medications"] = summary.get("current_medications") or []
        context["recognized_symptoms"] = summary.get("symptoms") or []
        context["recognized_vitals"] = summary.get("vitals") or []
        context["recognized_tests"] = summary.get("recent_tests") or []
        context["recognized_procedures"] = summary.get("recent_procedures") or []
        context["recognized_allergies"] = summary.get("allergies") or []
        context["entity_summary"] = summary
        context["entity_statistics"] = stats
        context["ner_metadata"] = {
            "completed": True,
            "confidence": confidence,
            "entity_count": entity_count,
            "timestamp": stamp,
            "processing_job_id": str(processing_job_id),
        }
        context["metadata"] = {
            **meta,
            "version": version,
            "ner_confidence": confidence,
            "last_updated": stamp,
            "data_sources": sources,
        }

        payload = {
            "processing_job_id": str(processing_job_id),
            "status": "Pending",
            "ner_completed": True,
            "ner_confidence": confidence,
            "ner_timestamp": stamp,
            "ner_entity_count": entity_count,
            "patient_context_json": context,
            "context_version": version,
            "current_summary": (
                (row or {}).get("current_summary")
                or "Patient context enriched with recognized medical entities."
            ),
        }

        if row:
            return self._contexts.update(UUID(str(row["id"])), payload)
        return self._contexts.create({"patient_id": str(patient_id), **payload})


# Re-export OCR repo for pipeline convenience
__all__ = [
    "MedicalEntityRepository",
    "MedicalEntityResultRepository",
    "NERStatusUpdater",
    "NERContextUpdater",
    "OCRRepository",
]
