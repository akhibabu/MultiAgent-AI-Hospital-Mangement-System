"""Patient Knowledge Graph repository + context/status updaters."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import HTTPException

from app.repositories.intake_repositories import (
    DocumentProcessingJobRepository,
    PatientAIContextRepository,
    SupabaseRestRepository,
)


class PatientKnowledgeGraphRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("patient_knowledge_graphs")

    def get_by_job(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        rows = self.select(
            [
                ("select", "*"),
                ("processing_job_id", f"eq.{job_id}"),
                ("limit", "1"),
            ]
        )
        return rows[0] if rows else None

    def get_latest_for_patient(self, patient_id: UUID) -> Optional[Dict[str, Any]]:
        rows = self.select(
            [
                ("select", "*"),
                ("patient_id", f"eq.{patient_id}"),
                ("order", "updated_at.desc"),
                ("limit", "1"),
            ]
        )
        return rows[0] if rows else None

    def upsert_for_job(self, job_id: UUID, body: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.get_by_job(job_id)
        stamp = datetime.utcnow().isoformat() + "Z"
        payload = {**body, "updated_at": stamp}
        if existing:
            return self.update(UUID(str(existing["id"])), payload)
        return self.insert(
            {**payload, "processing_job_id": str(job_id), "created_at": stamp}
        )


class KnowledgeGraphStatusUpdater:
    STAGE_KG = "Patient Knowledge Graph"
    STAGE_COMPLETED = "Completed"

    def __init__(self, jobs: Optional[DocumentProcessingJobRepository] = None) -> None:
        self._jobs = jobs or DocumentProcessingJobRepository()

    def get_job(self, job_id: UUID) -> Dict[str, Any]:
        row = self._jobs.get_by_id(job_id)
        if not row:
            raise HTTPException(status_code=404, detail="Processing job not found")
        return row

    def mark_kg_running(self, job_id: UUID) -> Dict[str, Any]:
        return self._jobs.update(
            job_id,
            {
                "status": "Processing",
                "current_stage": self.STAGE_KG,
                "error_message": None,
            },
        )

    def mark_kg_failed(self, job_id: UUID, error: str) -> Dict[str, Any]:
        return self._jobs.update(
            job_id,
            {
                "status": "Failed",
                "current_stage": self.STAGE_KG,
                "error_message": error[:2000],
            },
        )

    def mark_intake_complete(self, job_id: UUID) -> Dict[str, Any]:
        """Final Intake Agent stage complete."""
        return self._jobs.update(
            job_id,
            {
                "status": "Completed",
                "current_stage": self.STAGE_COMPLETED,
                "error_message": None,
                "processing_completed_at": datetime.utcnow().isoformat() + "Z",
            },
        )


class KnowledgeGraphContextUpdater:
    """Append knowledge graph summary into patient_ai_context."""

    def __init__(
        self,
        *,
        contexts: Optional[PatientAIContextRepository] = None,
    ) -> None:
        self._contexts = contexts or PatientAIContextRepository()

    def append_graph(
        self,
        *,
        patient_id: UUID,
        processing_job_id: UUID,
        graph_payload: Dict[str, Any],
        node_count: int,
        relationship_count: int,
        graph_version: int,
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
                "type": "knowledge_graph",
                "processing_job_id": str(processing_job_id),
                "node_count": node_count,
                "relationship_count": relationship_count,
                "graph_version": graph_version,
                "at": stamp,
            }
        )

        context["knowledge_graph"] = {
            "summary": graph_payload.get("summary"),
            "statistics": graph_payload.get("statistics"),
            "patient_summary": graph_payload.get("patient_summary"),
            "node_count": node_count,
            "relationship_count": relationship_count,
            "graph_version": graph_version,
            "updated_at": stamp,
        }
        context["knowledge_graph_summary"] = graph_payload.get("summary")
        context["kg_metadata"] = {
            "completed": True,
            "node_count": node_count,
            "relationship_count": relationship_count,
            "graph_version": graph_version,
            "timestamp": stamp,
            "processing_job_id": str(processing_job_id),
        }
        context["metadata"] = {
            **meta,
            "version": version,
            "last_updated": stamp,
            "data_sources": sources,
            "intake_completed": True,
        }

        payload = {
            "processing_job_id": str(processing_job_id),
            "status": "Completed",
            "kg_completed": True,
            "kg_node_count": node_count,
            "kg_relationship_count": relationship_count,
            "kg_version": graph_version,
            "kg_timestamp": stamp,
            "patient_context_json": context,
            "context_version": version,
            "current_summary": (
                graph_payload.get("summary")
                or (row or {}).get("current_summary")
                or "Patient knowledge graph completed."
            ),
        }

        if row:
            return self._contexts.update(UUID(str(row["id"])), payload)
        return self._contexts.create({"patient_id": str(patient_id), **payload})
