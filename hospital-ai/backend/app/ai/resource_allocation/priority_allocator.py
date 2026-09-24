"""Priority-aware ordering and scoring for resource allocation."""
from __future__ import annotations

from typing import List

from app.ai.resource_allocation.models import ResourceAllocationItem


class PriorityAllocator:
    def order(self, items: List[ResourceAllocationItem]) -> List[ResourceAllocationItem]:
        return sorted(
            items,
            key=lambda item: (item.priority, item.shortage_quantity == 0),
            reverse=True,
        )

    def allocation_score(self, items: List[ResourceAllocationItem]) -> float:
        if not items:
            return 100.0
        weighted_required = sum(item.required_quantity * max(item.priority, 1) for item in items)
        weighted_allocated = sum(item.allocated_quantity * max(item.priority, 1) for item in items)
        if weighted_required <= 0:
            return 100.0
        return round((weighted_allocated / weighted_required) * 100, 1)
