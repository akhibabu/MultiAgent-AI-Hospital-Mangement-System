"""Pydantic schemas for Intake Stage 5 — Patient Risk Profiling."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.registration import ProcessingJobOut


class RiskStartRequest(BaseModel):
    job_id: UUID


class CategoryRiskOut(BaseModel):
    name: str
    level: str
    score: float
    reason: str
    evidence: List[str] = Field(default_factory=list)
    confidence: float = 0.7
    factors: List[str] = Field(default_factory=list)


class RiskAlertOut(BaseModel):
    severity: str
    message: str
    category: Optional[str] = None


class RiskProfileOut(BaseModel):
    id: UUID
    processing_job_id: UUID
    patient_id: UUID
    overall_level: str
    overall_score: float
    overall_confidence: Optional[float] = None
    categories_json: List[Any] = Field(default_factory=list)
    top_risk_factors_json: List[Any] = Field(default_factory=list)
    important_findings_json: List[Any] = Field(default_factory=list)
    alerts_json: List[Any] = Field(default_factory=list)
    distribution_json: Dict[str, Any] = Field(default_factory=dict)
    timeline_json: List[Any] = Field(default_factory=list)
    disclaimer: Optional[str] = None
    processing_time_ms: Optional[int] = None
    status: str = "Completed"
    error_message: Optional[str] = None
    created_at: datetime


class RiskStartResponse(BaseModel):
    job_id: UUID
    patient_id: UUID
    status: str
    current_stage: str
    next_stage: str = "Patient Knowledge Graph"
    overall_level: str
    overall_score: float
    overall_confidence: float
    processing_time_ms: int
    categories: List[CategoryRiskOut] = Field(default_factory=list)
    top_risk_factors: List[str] = Field(default_factory=list)
    important_findings: List[str] = Field(default_factory=list)
    alerts: List[RiskAlertOut] = Field(default_factory=list)
    distribution: Dict[str, int] = Field(default_factory=dict)
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    disclaimer: str
    warnings: List[str] = Field(default_factory=list)
    risk_profile: RiskProfileOut
    processing_job: ProcessingJobOut
    patient_context_version: int = 1


class RiskStatusResponse(BaseModel):
    job_id: UUID
    status: str
    current_stage: str
    next_stage: str
    progress_pct: int
    risk_completed: bool = False
    overall_level: Optional[str] = None
    overall_score: Optional[float] = None
    error_message: Optional[str] = None
    processing_job: ProcessingJobOut
