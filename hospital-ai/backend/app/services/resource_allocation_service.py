"""Resource Allocation Agent service facade."""
from __future__ import annotations

import time
from typing import Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.resource_allocation.models import ResourceAllocationReport
from app.ai.resource_allocation.pipeline import ResourceAllocationPipeline
from app.core.logging import get_logger
from app.repositories.intake_repositories import DocumentProcessingJobRepository
from app.repositories.resource_allocation_repository import ResourceAllocationResultRepository
from app.schemas.resource_allocation import (
    AllocationConflictOut,
    MatchedResourceOut,
    ResourceAllocationHistoryItemOut,
    ResourceAllocationResponse,
    ResourceAllocationStartRequest,
    ResourceAllocationStartResponse,
    ResourceAllocationItemOut,
    ResourceRequirementOut,
)

logger = get_logger("hospital_ai.resource_allocation.service")


class ResourceAllocationService:
    def __init__(
        self,
        pipeline: Optional[ResourceAllocationPipeline] = None,
        results: Optional[ResourceAllocationResultRepository] = None,
    ) -> None:
        self._pipeline = pipeline or ResourceAllocationPipeline()
        self._results = results or ResourceAllocationResultRepository()

    def start(self, request: ResourceAllocationStartRequest) -> ResourceAllocationStartResponse:
        started = time.perf_counter()
        try:
            report: ResourceAllocationReport = self._pipeline.run(request.patient_id)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Resource allocation failed patient=%s", request.patient_id)
            raise HTTPException(
                status_code=500, detail=f"Resource Allocation Agent failed: {exc}"
            ) from exc

        elapsed = int((time.perf_counter() - started) * 1000)
        latest_job = DocumentProcessingJobRepository().latest_for_patient(request.patient_id)
        row = self._results.create(
            {
                "patient_id": str(request.patient_id),
                "processing_job_id": str(latest_job["id"]) if latest_job else None,
                "status": report.status,
                "engine": report.engine,
                "planning_only": report.planning_only,
                "priority_level": report.priority_level,
                "priority_score": report.priority_score,
                "requirements_json": [r.model_dump(mode="json") for r in report.requirements],
                "allocations_json": [a.model_dump(mode="json") for a in report.allocations],
                "conflicts_json": [c.model_dump(mode="json") for c in report.conflicts],
                "allocation_score": report.allocation_score,
                "source_result_ids_json": report.source_result_ids,
                "source_availability_json": report.source_availability,
                "summary": report.summary,
                "warnings_json": report.warnings,
                "processing_time_ms": elapsed,
            }
        )

        result = ResourceAllocationResponse.model_validate(row)
        return ResourceAllocationStartResponse(
            patient_id=request.patient_id,
            status=report.status,
            processing_time_ms=elapsed,
            summary=report.summary,
            engine=report.engine,
            planning_only=report.planning_only,
            priority_level=report.priority_level,
            priority_score=report.priority_score,
            requirements=_requirements(report),
            allocations=_allocations(report),
            conflicts=_conflicts(report),
            allocation_score=report.allocation_score,
            source_result_ids=report.source_result_ids,
            source_availability=report.source_availability,
            warnings=report.warnings,
            resource_allocation_result=result,
        )

    def result(self, patient_id: UUID) -> ResourceAllocationResponse:
        row = self._results.get_latest_for_patient(patient_id)
        if not row:
            raise HTTPException(
                status_code=404,
                detail="No Resource Allocation Agent result found for this patient. Run the agent first.",
            )
        return ResourceAllocationResponse.model_validate(row)

    def history(self, patient_id: UUID, limit: int = 20) -> list[ResourceAllocationHistoryItemOut]:
        rows = self._results.list_for_patient(patient_id, limit=limit)
        return [
            ResourceAllocationHistoryItemOut(
                id=row["id"],
                created_at=row["created_at"],
                priority_level=row.get("priority_level") or "Routine",
                priority_score=float(row.get("priority_score") or 0),
                allocation_score=float(row.get("allocation_score") or 0),
                conflict_count=len(row.get("conflicts_json") or []),
                status=row.get("status") or "Completed",
            )
            for row in rows
        ]


def _requirements(report: ResourceAllocationReport):
    return [ResourceRequirementOut.model_validate(r.model_dump(mode="json")) for r in report.requirements]


def _allocations(report: ResourceAllocationReport):
    return [ResourceAllocationItemOut.model_validate(a.model_dump(mode="json")) for a in report.allocations]


def _conflicts(report: ResourceAllocationReport):
    return [AllocationConflictOut.model_validate(c.model_dump(mode="json")) for c in report.conflicts]


def get_resource_allocation_service() -> ResourceAllocationService:
    return ResourceAllocationService()
