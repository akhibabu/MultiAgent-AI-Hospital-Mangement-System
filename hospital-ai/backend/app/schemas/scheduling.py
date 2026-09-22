"""Pydantic schemas for the Scheduling Agent API."""
from __future__ import annotations
from datetime import date
from typing import Any, Dict, List
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.appointment import VisitType
from app.ai.scheduling.models import (
    DoctorAssignmentResult, AppointmentSchedulingResult, SurgerySchedulingResult,
    FollowUpPlan, QueueOptimizationResult, WorkloadBalancingResult,
)

class SchedulingStartRequest(BaseModel):
    patient_id: UUID
    preferred_date: date = Field(default_factory=date.today)
    visit_type: VisitType = VisitType.CONSULTATION
    reason_for_visit: str | None = Field(default=None, max_length=2000)
    department_id: UUID | None = None
    preferred_doctor_id: UUID | None = None
    surgery_required: bool = False
    surgery_duration_minutes: int = Field(default=120, ge=30, le=480)
    follow_up_days: int = Field(default=14, ge=1, le=180)

class SchedulingResultOut(BaseModel):
    id: UUID
    patient_id: UUID
    processing_job_id: UUID | None = None
    doctor_assignment_json: Dict[str,Any] = Field(default_factory=dict)
    appointment_scheduling_json: Dict[str,Any] = Field(default_factory=dict)
    surgery_scheduling_json: Dict[str,Any] = Field(default_factory=dict)
    follow_up_planning_json: Dict[str,Any] = Field(default_factory=dict)
    queue_optimization_json: Dict[str,Any] = Field(default_factory=dict)
    workload_balancing_json: Dict[str,Any] = Field(default_factory=dict)
    summary: str | None = None
    engine: str = "deterministic_scheduling_rules_v1"
    status: str = "Completed"
    warnings_json: List[str] = Field(default_factory=list)
    processing_time_ms: int | None = None
    created_at: Any
    updated_at: Any = None

class SchedulingStartResponse(BaseModel):
    patient_id: UUID
    status: str = "Completed"
    processing_time_ms: int
    summary: str
    engine: str
    warnings: List[str] = Field(default_factory=list)
    doctor_assignment: DoctorAssignmentResult
    appointment_scheduling: AppointmentSchedulingResult
    surgery_scheduling: SurgerySchedulingResult
    follow_up_planning: FollowUpPlan
    queue_optimization: QueueOptimizationResult
    workload_balancing: WorkloadBalancingResult
    scheduling_result: SchedulingResultOut
