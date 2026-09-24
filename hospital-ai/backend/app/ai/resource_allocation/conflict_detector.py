"""Detect resource shortages and cross-agent conflicts."""
from __future__ import annotations

from typing import List

from app.ai.resource_allocation.models import AllocationConflict, ResourceAllocationItem


class ConflictDetector:
    def detect(
        self,
        *,
        allocations: List[ResourceAllocationItem],
        surgery_conflict: bool = False,
        scheduling_available: bool = True,
    ) -> List[AllocationConflict]:
        conflicts: List[AllocationConflict] = []
        for item in allocations:
            if item.shortage_quantity <= 0:
                continue
            severity = "Critical" if item.priority >= 90 else "High" if item.priority >= 70 else "Moderate"
            conflicts.append(
                AllocationConflict(
                    code="RESOURCE_SHORTAGE",
                    severity=severity,
                    message=(
                        f"{item.requirement} has a shortage of {item.shortage_quantity} "
                        f"unit(s) after checking current availability."
                    ),
                    requirement=item.requirement,
                    recommended_action="Escalate to hospital operations and consider an alternative resource or schedule.",
                )
            )
        if surgery_conflict:
            conflicts.append(
                AllocationConflict(
                    code="UPSTREAM_SURGERY_CONFLICT",
                    severity="High",
                    message="Scheduling contains conflicting structured surgery recommendations from upstream agents.",
                    recommended_action="Require clinician review before committing theatre, equipment, or bed resources.",
                )
            )
        if not scheduling_available:
            conflicts.append(
                AllocationConflict(
                    code="MISSING_SCHEDULING_CONTEXT",
                    severity="Moderate",
                    message="No Scheduling Agent result is available, so downstream resource requirements are incomplete.",
                    recommended_action="Run Scheduling Agent after upstream clinical workflows before final allocation.",
                )
            )
        return conflicts
