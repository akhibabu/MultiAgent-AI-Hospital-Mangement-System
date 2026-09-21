"""Domain models for the Emergency Agent."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from pydantic import BaseModel, Field

EMERGENCY_DISCLAIMER = (
    "Clinical decision-support estimate only. This module does not diagnose, "
    "replace emergency protocols, or determine definitive treatment or ICU admission."
)

TRIAGE_LEVELS = ("Routine", "Semi-Urgent", "Urgent", "Critical")


class VitalObservation(BaseModel):
    name: str
    value: str
    unit: str = ""
    status: str = "unknown"
    severity: str = "normal"
    message: str = ""


class VitalMonitoringResult(BaseModel):
    observed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    observations: List[VitalObservation] = Field(default_factory=list)
    abnormal_count: int = 0
    critical_count: int = 0
    monitoring_status: str = "no_data"
    data_source: str = "intake_patient_context"
    limitations: List[str] = Field(default_factory=list)


class CriticalEvent(BaseModel):
    event_type: str
    severity: str
    detected: bool = True
    evidence: List[str] = Field(default_factory=list)
    message: str = ""


class CriticalEventDetectionResult(BaseModel):
    events: List[CriticalEvent] = Field(default_factory=list)
    detected_event_count: int = 0
    critical_event_count: int = 0
    detection_mode: str = "deterministic_rule_based"


class TriageClassification(BaseModel):
    category: str = "Routine"
    score: float = 0.0
    escalation_required: bool = False
    reasons: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    disclaimer: str = EMERGENCY_DISCLAIMER


class ICURequirementResult(BaseModel):
    signal: str = "Low"
    score: float = 0.0
    confidence: float = 0.0
    reasons: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    limitation: str = (
        "This is a project-level acuity signal, not a clinical ICU admission decision."
    )


class EmergencyAlert(BaseModel):
    code: str
    severity: str
    title: str
    message: str
    recommended_next_step: str
    requires_acknowledgement: bool = True


class EmergencyAlertGenerationResult(BaseModel):
    alerts: List[EmergencyAlert] = Field(default_factory=list)
    alert_count: int = 0
    highest_severity: str = "None"
    delivery_mode: str = "in_application_response_only"


class PatientPriorityRanking(BaseModel):
    priority_score: float = 0.0
    priority_level: str = "Routine"
    rank_basis: str = (
        "Single-patient emergency acuity score; this is not a queue position."
    )
    factors: List[str] = Field(default_factory=list)
    disclaimer: str = EMERGENCY_DISCLAIMER


class EmergencyReport(BaseModel):
    patient_id: str
    patient_name: str = "Patient"
    status: str = "Completed"
    engine: str = "deterministic_emergency_rules_v1"
    vital_monitoring: VitalMonitoringResult = Field(default_factory=VitalMonitoringResult)
    triage_classification: TriageClassification = Field(default_factory=TriageClassification)
    critical_event_detection: CriticalEventDetectionResult = Field(
        default_factory=CriticalEventDetectionResult
    )
    icu_requirement: ICURequirementResult = Field(default_factory=ICURequirementResult)
    emergency_alerts: EmergencyAlertGenerationResult = Field(
        default_factory=EmergencyAlertGenerationResult
    )
    patient_priority: PatientPriorityRanking = Field(
        default_factory=PatientPriorityRanking
    )
    summary: str = ""
    warnings: List[str] = Field(default_factory=list)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")
