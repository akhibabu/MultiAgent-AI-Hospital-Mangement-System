"""Pydantic schemas for the Emergency Agent API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.emergency.models import (
    CriticalEventDetectionResult,
    EmergencyAlertGenerationResult,
    ICURequirementResult,
    PatientPriorityRanking,
    TriageClassification,
    VitalMonitoringResult,
)


class EmergencyStartRequest(BaseModel):
    patient_id: UUID


class EmergencyResultOut(BaseModel):
    id: UUID
    patient_id: UUID
    processing_job_id: UUID | None = None
    vital_monitoring_json: Dict[str, Any] = Field(default_factory=dict)
    triage_classification_json: Dict[str, Any] = Field(default_factory=dict)
    critical_event_detection_json: Dict[str, Any] = Field(default_factory=dict)
    icu_requirement_json: Dict[str, Any] = Field(default_factory=dict)
    emergency_alerts_json: Dict[str, Any] = Field(default_factory=dict)
    patient_priority_json: Dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None
    engine: str = "deterministic_emergency_rules_v1"
    status: str = "Completed"
    warnings_json: List[str] = Field(default_factory=list)
    processing_time_ms: int | None = None
    created_at: datetime
    updated_at: datetime | None = None


class EmergencyStartResponse(BaseModel):
    patient_id: UUID
    status: str = "Completed"
    processing_time_ms: int
    summary: str
    engine: str
    warnings: List[str] = Field(default_factory=list)
    vital_monitoring: VitalMonitoringResult
    triage_classification: TriageClassification
    critical_event_detection: CriticalEventDetectionResult
    icu_requirement: ICURequirementResult
    emergency_alerts: EmergencyAlertGenerationResult
    patient_priority: PatientPriorityRanking
    emergency_result: EmergencyResultOut


class EmergencyHistoryItemOut(BaseModel):
    id: UUID
    created_at: datetime
    triage_category: str | None = None
    triage_score: float | None = None
    priority_level: str | None = None
    priority_score: float | None = None
    alert_count: int = 0
    status: str = "Completed"
