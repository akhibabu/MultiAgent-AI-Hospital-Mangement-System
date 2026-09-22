"""Domain models for the Scheduling Agent."""
from __future__ import annotations
from datetime import date, time, datetime, timezone
from typing import List
from pydantic import BaseModel, Field

class DoctorCandidate(BaseModel):
    doctor_id: str
    doctor_name: str
    specialization: str
    department_id: str | None = None
    department_name: str | None = None
    availability_status: str = "Available"
    workload_count: int = 0
    score: float = 0.0
    reasons: List[str] = Field(default_factory=list)

class DoctorAssignmentResult(BaseModel):
    selected_doctor_id: str | None = None
    selected_doctor_name: str | None = None
    selection_score: float = 0.0
    candidates: List[DoctorCandidate] = Field(default_factory=list)
    rationale: List[str] = Field(default_factory=list)

class SlotRecommendation(BaseModel):
    doctor_id: str
    doctor_name: str
    appointment_date: str
    start_time: str
    end_time: str
    score: float
    reasons: List[str] = Field(default_factory=list)

class AppointmentSchedulingResult(BaseModel):
    recommended_slot: SlotRecommendation | None = None
    alternatives: List[SlotRecommendation] = Field(default_factory=list)
    booking_status: str = "Recommendation only"
    rationale: List[str] = Field(default_factory=list)

class SurgerySchedulingResult(BaseModel):
    required: bool = False
    recommended_slot: SlotRecommendation | None = None
    operation_theatre_status: str = "Not evaluated — Resource Allocation Agent is downstream."
    notes: List[str] = Field(default_factory=list)

class FollowUpPlan(BaseModel):
    recommended_date: str | None = None
    interval_days: int | None = None
    reason: str = ""
    planning_only: bool = True

class QueueItem(BaseModel):
    appointment_id: str
    patient_id: str
    patient_name: str
    start_time: str
    end_time: str
    priority_level: str = "Routine"
    priority_score: float = 0.0
    position: int = 0

class QueueOptimizationResult(BaseModel):
    doctor_id: str | None = None
    appointment_date: str | None = None
    ordered_queue: List[QueueItem] = Field(default_factory=list)
    changed_order_count: int = 0
    rationale: List[str] = Field(default_factory=list)

class DoctorWorkload(BaseModel):
    doctor_id: str
    doctor_name: str
    active_appointments: int = 0
    workload_score: float = 0.0
    availability_status: str = "Available"

class WorkloadBalancingResult(BaseModel):
    horizon_days: int = 7
    doctor_loads: List[DoctorWorkload] = Field(default_factory=list)
    balance_gap: float = 0.0
    recommendation: str = ""

class SchedulingReport(BaseModel):
    patient_id: str
    patient_name: str = "Patient"
    status: str = "Completed"
    engine: str = "deterministic_scheduling_rules_v1"
    doctor_assignment: DoctorAssignmentResult = Field(default_factory=DoctorAssignmentResult)
    appointment_scheduling: AppointmentSchedulingResult = Field(default_factory=AppointmentSchedulingResult)
    surgery_scheduling: SurgerySchedulingResult = Field(default_factory=SurgerySchedulingResult)
    follow_up_planning: FollowUpPlan = Field(default_factory=FollowUpPlan)
    queue_optimization: QueueOptimizationResult = Field(default_factory=QueueOptimizationResult)
    workload_balancing: WorkloadBalancingResult = Field(default_factory=WorkloadBalancingResult)
    summary: str = ""
    warnings: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
