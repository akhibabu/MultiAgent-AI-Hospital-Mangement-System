"""Domain models for the Resource Allocation Agent."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ResourceRequirement(BaseModel):
    requirement: str
    resource_type: Optional[str] = None
    required_quantity: int = Field(default=1, ge=1)
    source: str
    rationale: str = ""
    priority: int = Field(default=50, ge=0, le=100)


class MatchedResource(BaseModel):
    resource_id: str
    resource_name: str
    resource_type: str
    available_quantity: int = Field(ge=0)
    location: Optional[str] = None


class ResourceAllocationItem(BaseModel):
    requirement: str
    resource_type: Optional[str] = None
    required_quantity: int = Field(default=1, ge=1)
    available_quantity: int = Field(default=0, ge=0)
    allocated_quantity: int = Field(default=0, ge=0)
    shortage_quantity: int = Field(default=0, ge=0)
    status: str = "Unavailable"
    priority: int = Field(default=50, ge=0, le=100)
    source: str
    rationale: str = ""
    matched_resources: List[MatchedResource] = Field(default_factory=list)


class AllocationConflict(BaseModel):
    code: str
    severity: str
    message: str
    requirement: Optional[str] = None
    recommended_action: str = ""


class ResourceAllocationReport(BaseModel):
    patient_id: str
    patient_name: str = "Patient"
    status: str = "Completed"
    engine: str = "deterministic_resource_allocation_rules_v1"
    planning_only: bool = True
    priority_level: str = "Routine"
    priority_score: float = Field(default=0.0, ge=0, le=100)
    requirements: List[ResourceRequirement] = Field(default_factory=list)
    allocations: List[ResourceAllocationItem] = Field(default_factory=list)
    conflicts: List[AllocationConflict] = Field(default_factory=list)
    allocation_score: float = Field(default=0.0, ge=0, le=100)
    source_result_ids: Dict[str, Optional[str]] = Field(default_factory=dict)
    source_availability: Dict[str, bool] = Field(default_factory=dict)
    summary: str = ""
    warnings: List[str] = Field(default_factory=list)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")
