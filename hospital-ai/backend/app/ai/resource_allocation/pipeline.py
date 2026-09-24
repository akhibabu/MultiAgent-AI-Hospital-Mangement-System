"""Resource Allocation Agent pipeline."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.resource_allocation.availability_assessor import AvailabilityAssessor
from app.ai.resource_allocation.conflict_detector import ConflictDetector
from app.ai.resource_allocation.context import ResourceAllocationContext
from app.ai.resource_allocation.models import ResourceAllocationReport
from app.ai.resource_allocation.priority_allocator import PriorityAllocator
from app.core.logging import get_logger
from app.repositories.resource_allocation_inventory_repository import ResourceAllocationInventoryRepository

logger = get_logger("hospital_ai.resource_allocation.pipeline")


class ResourceAllocationPipeline:
    def __init__(
        self,
        *,
        context: Optional[ResourceAllocationContext] = None,
        inventory: Optional[ResourceAllocationInventoryRepository] = None,
        assessor: Optional[AvailabilityAssessor] = None,
        priority: Optional[PriorityAllocator] = None,
        conflicts: Optional[ConflictDetector] = None,
    ) -> None:
        self.context = context or ResourceAllocationContext()
        self.inventory = inventory or ResourceAllocationInventoryRepository()
        self.assessor = assessor or AvailabilityAssessor()
        self.priority = priority or PriorityAllocator()
        self.conflicts = conflicts or ConflictDetector()

    def run(self, patient_id: UUID) -> ResourceAllocationReport:
        source = self.context.load(patient_id)
        patient = source.get("patient")
        if not getattr(patient, "patient_id", None):
            raise HTTPException(status_code=404, detail="Patient not found")

        derived = self.context.derive(source)
        scheduling = source.get("scheduling") or {}

        inventory = self.inventory.list_resources()
        doctors = self.inventory.list_doctors()
        selected_doctor_id = str(
            ((scheduling.get("doctor_assignment_json") or {}).get("selected_doctor_id")) or ""
        ) or None
        specialists = derived.get("specialists") or []
        # Scheduling persists specialist recommendations; keep the lookup resilient
        # to older rows that predate that field.
        if not specialists:
            specialists = _specialists_from_scheduling(scheduling)

        allocations = self.assessor.assess(
            requirements=derived["requirements"],
            resources=inventory,
            doctors=doctors,
            selected_doctor_id=selected_doctor_id,
            preferred_specialists=specialists,
        )
        allocations = self.priority.order(allocations)

        surgery_conflict = bool(scheduling.get("surgery_conflict"))
        conflicts = self.conflicts.detect(
            allocations=allocations,
            surgery_conflict=surgery_conflict,
            scheduling_available=derived["sources_available"]["scheduling"],
        )

        warnings = []
        for source_name, available in derived["sources_available"].items():
            if not available:
                warnings.append(
                    f"No {source_name.replace('_', ' ').title()} result is available; "
                    "allocation is based on the remaining upstream context."
                )
        if allocations:
            warnings.append(
                "Planning only: inventory quantities are not changed or reserved by this agent. "
                "A future transactional reservation step should validate availability again before commitment."
            )
        else:
            warnings.append(
                "No downstream resource requirements were found in the current upstream context."
            )

        score = self.priority.allocation_score(allocations)
        summary = self._summary(
            derived["patient_name"],
            derived["priority_level"],
            allocations,
            conflicts,
            score,
        )

        logger.info(
            "Resource allocation complete patient=%s requirements=%s score=%s conflicts=%s",
            patient_id,
            len(allocations),
            score,
            len(conflicts),
        )
        return ResourceAllocationReport(
            patient_id=str(patient_id),
            patient_name=derived["patient_name"],
            priority_level=derived["priority_level"],
            priority_score=derived["priority_score"],
            requirements=derived["requirements"],
            allocations=allocations,
            conflicts=conflicts,
            allocation_score=score,
            source_result_ids=derived["source_result_ids"],
            source_availability=derived["sources_available"],
            summary=summary,
            warnings=warnings,
        )

    @staticmethod
    def _summary(
        patient_name: str,
        priority_level: str,
        allocations,
        conflicts,
        score: float,
    ) -> str:
        allocated = sum(i.allocated_quantity for i in allocations)
        required = sum(i.required_quantity for i in allocations)
        return (
            f"{patient_name}: Resource Allocation Agent produced a planning-only resource plan "
            f"for a {priority_level} priority case. {allocated}/{required} requested units are "
            f"currently available for planning, giving an allocation score of {score}/100, "
            f"with {len(conflicts)} conflict(s) requiring attention."
        )


def _specialists_from_scheduling(scheduling):
    value = scheduling.get("derived_specialists_json") or []
    return [str(v).strip() for v in value if str(v).strip()] if isinstance(value, list) else []
