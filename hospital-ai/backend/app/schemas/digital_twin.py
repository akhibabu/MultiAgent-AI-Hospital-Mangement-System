"""Pydantic response models for the Hospital Digital Twin API."""
from __future__ import annotations
from typing import Dict, List
from pydantic import BaseModel, Field

class DigitalTwinScenarioRequest(BaseModel):
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

class ResourceTwinStateOut(BaseModel):
    resource_type: str
    total_quantity: int
    available_quantity: int
    in_use_quantity: int
    maintenance_quantity: int
    out_of_service_quantity: int
    utilization_percent: float

class StaffTwinStateOut(BaseModel):
    total_doctors: int
    available_doctors: int
    busy_doctors: int
    on_leave_doctors: int
    utilization_percent: float

class FlowTwinStateOut(BaseModel):
    appointments_next_24h: int
    appointments_next_7d: int
    emergency_results_last_24h: int
    high_or_critical_emergencies: int
    icu_signals_last_24h: int
    scheduling_runs_last_24h: int
    allocation_runs_last_24h: int
    allocation_conflicts_last_24h: int

class HospitalTwinStateOut(BaseModel):
    captured_at: str
    resources: List[ResourceTwinStateOut]
    staff: StaffTwinStateOut
    flow: FlowTwinStateOut
    operational_pressure: float
    source_status: Dict[str, bool]
    source_timestamps: Dict[str, str]

class ProjectionMetricOut(BaseModel):
    resource_type: str
    baseline_available: int
    projected_available: int
    projected_utilization_percent: float
    shortage: int
    status: str

class FlowProjectionOut(BaseModel):
    projected_appointments: int
    projected_emergency_arrivals: int
    net_admissions: int
    projected_operational_pressure: float

class BottleneckSignalOut(BaseModel):
    resource_type: str
    severity: str
    message: str
    current_utilization_percent: float
    projected_utilization_percent: float
    shortage: int

class TwinFeedbackSignalOut(BaseModel):
    target_agent: str
    signal: str
    recommended_action: str
    severity: str

class DigitalTwinSimulationOut(BaseModel):
    scenario: DigitalTwinScenarioRequest
    resource_projections: List[ProjectionMetricOut]
    flow_projection: FlowProjectionOut
    bottlenecks: List[BottleneckSignalOut]
    feedback_signals: List[TwinFeedbackSignalOut]
    summary: str
    safety_notes: List[str]
    generated_at: str

class DigitalTwinRunOut(BaseModel):
    id: str
    created_at: str
    status: str
    engine: str
    baseline_state: HospitalTwinStateOut
    simulation: DigitalTwinSimulationOut
    processing_time_ms: int

class DigitalTwinStateResponse(BaseModel):
    state: HospitalTwinStateOut

class DigitalTwinHistoryItemOut(BaseModel):
    id: str
    created_at: str
    status: str
    engine: str
    horizon_hours: int
    processing_time_ms: int | None = None
    summary: str
