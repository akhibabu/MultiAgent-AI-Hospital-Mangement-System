"""Pydantic schemas for the Scheduling Agent API."""
from __future__ import annotations
from datetime import date
from typing import Any, Dict, List
from uuid import UUID
from pydantic import BaseModel, Field
from app.ai.scheduling.models import (
    DoctorAssignmentResult, AppointmentSchedulingResult, SurgerySchedulingResult,
    FollowUpPlan, QueueOptimizationResult, WorkloadBalancingResult,
)

class SchedulingStartRequest(BaseModel):
    patient_id: UUID
    preferred_date: date = Field(default_factory=date.today)

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
    emergency_priority_level: str = "Routine"
    emergency_priority_score: float = 0.0
    visit_type: str = "Consultation"
    derived_department: str | None = None
    derived_specialists_json: List[str] = Field(default_factory=list)
    surgery_recommendation_json: List[str] = Field(default_factory=list)
    source_result_ids_json: Dict[str, str | None] = Field(default_factory=dict)
    source_availability_json: Dict[str, bool] = Field(default_factory=dict)
    recommended_tests_json: List[str] = Field(default_factory=list)
    recommended_imaging_json: List[str] = Field(default_factory=list)
    recommended_medications_json: List[str] = Field(default_factory=list)
    treatment_validation_status: str | None = None
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
    emergency_priority_level: str = "Routine"
    emergency_priority_score: float = 0.0
    visit_type: str = "Consultation"
    derived_department: str | None = None
    derived_specialists: List[str] = Field(default_factory=list)
    surgery_recommendation: List[str] = Field(default_factory=list)
    source_result_ids: Dict[str, str | None] = Field(default_factory=dict)
    source_availability: Dict[str, bool] = Field(default_factory=dict)
    recommended_tests: List[str] = Field(default_factory=list)
    recommended_imaging: List[str] = Field(default_factory=list)
    recommended_medications: List[str] = Field(default_factory=list)
    treatment_validation_status: str | None = None
    warnings: List[str] = Field(default_factory=list)
    doctor_assignment: DoctorAssignmentResult
    appointment_scheduling: AppointmentSchedulingResult
    surgery_scheduling: SurgerySchedulingResult
    follow_up_planning: FollowUpPlan
    queue_optimization: QueueOptimizationResult
    workload_balancing: WorkloadBalancingResult
    scheduling_result: SchedulingResultOut
