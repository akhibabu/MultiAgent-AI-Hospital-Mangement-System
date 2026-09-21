"""Emergency Agent service facade."""

from __future__ import annotations

import time
from typing import Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.emergency.models import EmergencyReport
from app.ai.emergency.pipeline import EmergencyPipeline
from app.core.logging import get_logger
from app.repositories.emergency_repository import EmergencyResultRepository
from app.repositories.intake_repositories import DocumentProcessingJobRepository
from app.schemas.emergency import (
    EmergencyHistoryItemOut,
    EmergencyResultOut,
    EmergencyStartRequest,
    EmergencyStartResponse,
)

logger = get_logger("hospital_ai.emergency.service")


class EmergencyService:
    def __init__(
        self,
        pipeline: Optional[EmergencyPipeline] = None,
        results: Optional[EmergencyResultRepository] = None,
    ) -> None:
        self._pipeline = pipeline or EmergencyPipeline()
        self._results = results or EmergencyResultRepository()

    def start(self, request: EmergencyStartRequest) -> EmergencyStartResponse:
        started = time.perf_counter()
        try:
            report: EmergencyReport = self._pipeline.run(request.patient_id)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Emergency pipeline failed patient=%s", request.patient_id)
            raise HTTPException(
                status_code=500, detail=f"Emergency Agent failed: {exc}"
            ) from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        jobs = DocumentProcessingJobRepository()
        latest_job = jobs.latest_for_patient(request.patient_id)

        row = self._results.create(
            {
                "patient_id": str(request.patient_id),
                "processing_job_id": str(latest_job["id"]) if latest_job else None,
                "vital_monitoring_json": report.vital_monitoring.model_dump(mode="json"),
                "triage_classification_json": report.triage_classification.model_dump(mode="json"),
                "critical_event_detection_json": report.critical_event_detection.model_dump(mode="json"),
                "icu_requirement_json": report.icu_requirement.model_dump(mode="json"),
                "emergency_alerts_json": report.emergency_alerts.model_dump(mode="json"),
                "patient_priority_json": report.patient_priority.model_dump(mode="json"),
                "summary": report.summary,
                "engine": report.engine,
                "status": "Completed",
                "warnings_json": report.warnings,
                "processing_time_ms": elapsed_ms,
            }
        )

        return EmergencyStartResponse(
            patient_id=request.patient_id,
            status="Completed",
            processing_time_ms=elapsed_ms,
            summary=report.summary,
            engine=report.engine,
            warnings=report.warnings,
            vital_monitoring=report.vital_monitoring,
            triage_classification=report.triage_classification,
            critical_event_detection=report.critical_event_detection,
            icu_requirement=report.icu_requirement,
            emergency_alerts=report.emergency_alerts,
            patient_priority=report.patient_priority,
            emergency_result=EmergencyResultOut.model_validate(row),
        )

    def result(self, patient_id: UUID) -> EmergencyResultOut:
        row = self._results.get_latest_for_patient(patient_id)
        if not row:
            raise HTTPException(
                status_code=404,
                detail="No Emergency Agent result found for this patient. Run the Emergency Agent first.",
            )
        return EmergencyResultOut.model_validate(row)

    def history(self, patient_id: UUID, limit: int = 20) -> list[EmergencyHistoryItemOut]:
        rows = self._results.list_for_patient(patient_id, limit=limit)
        return [
            EmergencyHistoryItemOut(
                id=row["id"],
                created_at=row["created_at"],
                triage_category=(row.get("triage_classification_json") or {}).get("category"),
                triage_score=(row.get("triage_classification_json") or {}).get("score"),
                priority_level=(row.get("patient_priority_json") or {}).get("priority_level"),
                priority_score=(row.get("patient_priority_json") or {}).get("priority_score"),
                alert_count=(row.get("emergency_alerts_json") or {}).get("alert_count", 0),
                status=row.get("status") or "Completed",
            )
            for row in rows
        ]


def get_emergency_service() -> EmergencyService:
    return EmergencyService()
