"""Patient Risk Profiling repository + context/status updaters."""

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


class PatientRiskProfileRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("patient_risk_profiles")

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


class RiskStatusUpdater:
    STAGE_RISK = "Patient Risk Profiling"
    STAGE_KG = "Patient Knowledge Graph"

    def __init__(self, jobs: Optional[DocumentProcessingJobRepository] = None) -> None:
        self._jobs = jobs or DocumentProcessingJobRepository()

    def get_job(self, job_id: UUID) -> Dict[str, Any]:
        row = self._jobs.get_by_id(job_id)
        if not row:
            raise HTTPException(status_code=404, detail="Processing job not found")
        return row

    def mark_risk_running(self, job_id: UUID) -> Dict[str, Any]:
        return self._jobs.update(
            job_id,
            {
                "status": "Processing",
                "current_stage": self.STAGE_RISK,
                "error_message": None,
            },
        )

    def mark_risk_failed(self, job_id: UUID, error: str) -> Dict[str, Any]:
        return self._jobs.update(
            job_id,
            {
                "status": "Failed",
                "current_stage": self.STAGE_RISK,
                "error_message": error[:2000],
            },
        )

    def mark_risk_complete(self, job_id: UUID) -> Dict[str, Any]:
        """Risk done → advance marker to Knowledge Graph (not executed)."""
        return self._jobs.update(
            job_id,
            {
                "status": "Processing",
                "current_stage": self.STAGE_KG,
                "error_message": None,
            },
        )


class RiskContextUpdater:
    """Append risk assessment into patient_ai_context (preserve prior stages)."""

    def __init__(
        self,
        *,
        contexts: Optional[PatientAIContextRepository] = None,
    ) -> None:
        self._contexts = contexts or PatientAIContextRepository()

    def append_risk(
        self,
        *,
        patient_id: UUID,
        processing_job_id: UUID,
        risk_payload: Dict[str, Any],
        overall_level: str,
        overall_score: float,
        confidence: float,
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
                "type": "risk",
                "processing_job_id": str(processing_job_id),
                "overall_level": overall_level,
                "overall_score": overall_score,
                "at": stamp,
            }
        )

        context["risk_profile"] = risk_payload
        context["overall_risk"] = {
            "level": overall_level,
            "score": overall_score,
            "confidence": confidence,
            "assessed_at": stamp,
        }
        context["risk_categories"] = risk_payload.get("categories") or []
        context["risk_factors"] = risk_payload.get("top_risk_factors") or []
        context["risk_alerts"] = risk_payload.get("alerts") or []
        context["risk_metadata"] = {
            "completed": True,
            "overall_level": overall_level,
            "overall_score": overall_score,
            "confidence": confidence,
            "timestamp": stamp,
            "processing_job_id": str(processing_job_id),
            "disclaimer": risk_payload.get("disclaimer"),
        }
        context["metadata"] = {
            **meta,
            "version": version,
            "risk_confidence": confidence,
            "last_updated": stamp,
            "data_sources": sources,
        }

        payload = {
            "processing_job_id": str(processing_job_id),
            "status": "Pending",
            "risk_completed": True,
            "risk_level": overall_level,
            "risk_score": overall_score,
            "risk_timestamp": stamp,
            "patient_context_json": context,
            "context_version": version,
            "current_summary": (
                (row or {}).get("current_summary")
                or f"Patient risk profile: {overall_level} ({overall_score:.0f})."
            ),
        }

        if row:
            return self._contexts.update(UUID(str(row["id"])), payload)
        return self._contexts.create({"patient_id": str(patient_id), **payload})
