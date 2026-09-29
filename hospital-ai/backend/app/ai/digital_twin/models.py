"""Typed models for the Hospital Digital Twin."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from pydantic import BaseModel, Field


class ResourceTwinState(BaseModel):
    resource_type: str
    total_quantity: int = Field(ge=0)
    available_quantity: int = Field(ge=0)
    in_use_quantity: int = Field(ge=0)
    maintenance_quantity: int = Field(ge=0)
    out_of_service_quantity: int = Field(ge=0)
    utilization_percent: float = Field(ge=0, le=100)


class StaffTwinState(BaseModel):
    total_doctors: int = Field(ge=0)
    available_doctors: int = Field(ge=0)
    busy_doctors: int = Field(ge=0)
    on_leave_doctors: int = Field(ge=0)
    utilization_percent: float = Field(ge=0, le=100)


class FlowTwinState(BaseModel):
    appointments_next_24h: int = Field(ge=0)
    appointments_next_7d: int = Field(ge=0)
    emergency_results_last_24h: int = Field(ge=0)
    high_or_critical_emergencies: int = Field(ge=0)
    icu_signals_last_24h: int = Field(ge=0)
    scheduling_runs_last_24h: int = Field(ge=0)
    allocation_runs_last_24h: int = Field(ge=0)
    allocation_conflicts_last_24h: int = Field(ge=0)


class HospitalTwinState(BaseModel):
    captured_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resources: List[ResourceTwinState] = Field(default_factory=list)
    staff: StaffTwinState
    flow: FlowTwinState
    operational_pressure: float = Field(ge=0, le=100)
    source_status: Dict[str, bool] = Field(default_factory=dict)
    source_timestamps: Dict[str, str] = Field(default_factory=dict)


class DigitalTwinScenario(BaseModel):
    horizon_hours: int = Field(default=24, ge=1, le=168)
    emergency_arrivals: int = Field(default=0, ge=0, le=1000)
    planned_admissions: int = Field(default=0, ge=0, le=1000)
    expected_discharges: int = Field(default=0, ge=0, le=1000)
    icu_admissions: int = Field(default=0, ge=0, le=500)
    icu_discharges: int = Field(default=0, ge=0, le=500)
    ventilator_demand: int = Field(default=0, ge=0, le=500)
    additional_theatre_demand: int = Field(default=0, ge=0, le=100)
    staff_absent: int = Field(default=0, ge=0, le=1000)
    additional_appointments: int = Field(default=0, ge=0, le=5000)


class ProjectionMetric(BaseModel):
    resource_type: str
    baseline_available: int = Field(ge=0)
    projected_available: int = Field(ge=0)
    projected_utilization_percent: float = Field(ge=0, le=100)
    shortage: int = Field(ge=0)
    status: str


class FlowProjection(BaseModel):
    projected_appointments: int = Field(ge=0)
    projected_emergency_arrivals: int = Field(ge=0)
    net_admissions: int
    projected_operational_pressure: float = Field(ge=0, le=100)


class BottleneckSignal(BaseModel):
    resource_type: str
    severity: str
    message: str
    current_utilization_percent: float = Field(ge=0, le=100)
    projected_utilization_percent: float = Field(ge=0, le=100)
    shortage: int = Field(ge=0)


class TwinFeedbackSignal(BaseModel):
    target_agent: str
    signal: str
    recommended_action: str
    severity: str


class DigitalTwinSimulation(BaseModel):
    scenario: DigitalTwinScenario
    resource_projections: List[ProjectionMetric] = Field(default_factory=list)
    flow_projection: FlowProjection
    bottlenecks: List[BottleneckSignal] = Field(default_factory=list)
    feedback_signals: List[TwinFeedbackSignal] = Field(default_factory=list)
    summary: str
    safety_notes: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DigitalTwinRun(BaseModel):
    id: str
    created_at: str
    status: str
    engine: str
    baseline_state: HospitalTwinState
    simulation: DigitalTwinSimulation
    processing_time_ms: int
