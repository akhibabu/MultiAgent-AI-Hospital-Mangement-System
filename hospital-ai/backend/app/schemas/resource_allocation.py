"""API schemas for the Resource Allocation Agent."""
from __future__ import annotations

from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ResourceAllocationStartRequest(BaseModel):
    patient_id: UUID


class MatchedResourceOut(BaseModel):
    resource_id: str
    resource_name: str
    resource_type: str
    available_quantity: int = Field(ge=0)
    location: Optional[str] = None


class ResourceRequirementOut(BaseModel):
    requirement: str
    resource_type: Optional[str] = None
    required_quantity: int = Field(ge=1)
    source: str
    rationale: str
    priority: int = Field(ge=0, le=100)


class ResourceAllocationItemOut(BaseModel):
    requirement: str
    resource_type: Optional[str] = None
    required_quantity: int = Field(ge=1)
    available_quantity: int = Field(ge=0)
    allocated_quantity: int = Field(ge=0)
    shortage_quantity: int = Field(ge=0)
    status: str
    priority: int = Field(ge=0, le=100)
    source: str
    rationale: str
    matched_resources: List[MatchedResourceOut] = Field(default_factory=list)


class AllocationConflictOut(BaseModel):
    code: str
    severity: str
    message: str
    requirement: Optional[str] = None
    recommended_action: str = ""


class ResourceAllocationResponse(BaseModel):
    id: UUID
    patient_id: UUID
    status: str
    engine: str
    planning_only: bool
    priority_level: str
    priority_score: float
    requirements_json: List[ResourceRequirementOut]
    allocations_json: List[ResourceAllocationItemOut]
    conflicts_json: List[AllocationConflictOut]
    allocation_score: float
    source_result_ids_json: Dict[str, Optional[str]]
    source_availability_json: Dict[str, bool]
    summary: Optional[str] = None
    warnings_json: List[str] = Field(default_factory=list)
    processing_time_ms: Optional[int] = None
    created_at: str
    updated_at: Optional[str] = None


class ResourceAllocationStartResponse(BaseModel):
    patient_id: UUID
    status: str
    processing_time_ms: int
    summary: str
    engine: str
    planning_only: bool
    priority_level: str
    priority_score: float
    requirements: List[ResourceRequirementOut]
    allocations: List[ResourceAllocationItemOut]
    conflicts: List[AllocationConflictOut]
    allocation_score: float
    source_result_ids: Dict[str, Optional[str]]
    source_availability: Dict[str, bool]
    warnings: List[str]
    resource_allocation_result: ResourceAllocationResponse


class ResourceAllocationHistoryItemOut(BaseModel):
    id: UUID
    created_at: str
    priority_level: str
    priority_score: float
    allocation_score: float
    conflict_count: int
    status: str
