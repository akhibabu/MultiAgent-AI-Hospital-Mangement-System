"""Pydantic schemas for the Diagnosis Agent."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DiagnosisStartRequest(BaseModel):
    patient_id: UUID
    chief_complaint: Optional[str] = None
    focus_symptoms: List[str] = Field(default_factory=list)


class SymptomClusterOut(BaseModel):
    body_system: str
    symptoms: List[str] = Field(default_factory=list)
    duration_hint: Optional[str] = None
    severity_hint: Optional[str] = None
    related_conditions: List[str] = Field(default_factory=list)


class SymptomAnalysisOut(BaseModel):
    clusters: List[SymptomClusterOut] = Field(default_factory=list)
    total_symptoms: int = 0
    notable_vitals: List[Dict[str, Any]] = Field(default_factory=list)
    notable_labs: List[Dict[str, Any]] = Field(default_factory=list)
    narrative: str = ""


class DifferentialDiagnosisOut(BaseModel):
    condition: str
    confidence: float = 0.0
    supporting_symptoms: List[str] = Field(default_factory=list)
    supporting_labs: List[str] = Field(default_factory=list)
    supporting_history: List[str] = Field(default_factory=list)
    contradicting_evidence: List[str] = Field(default_factory=list)
    recommended_specialists: List[str] = Field(default_factory=list)
    body_system: Optional[str] = None


class DiseaseProbabilityOut(BaseModel):
    condition: str
    probability_pct: float = 0.0
    confidence: float = 0.0
    evidence_used: List[str] = Field(default_factory=list)
    risk_contribution: float = 0.0
    risk_category: Optional[str] = None


class SeverityAssessmentOut(BaseModel):
    level: str = "Very Low"
    score: float = 0.0
    explanation: str = ""
    contributing_factors: List[str] = Field(default_factory=list)


class TreatmentPathOut(BaseModel):
    recommended_specialists: List[str] = Field(default_factory=list)
    recommended_department: Optional[str] = None
    diagnostic_tests: List[str] = Field(default_factory=list)
    imaging: List[str] = Field(default_factory=list)
    urgency: str = "Routine"
    notes: str = ""


class ClinicalDecisionSupportOut(BaseModel):
    possible_diagnoses: List[str] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    suggested_tests: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    relevant_history: List[str] = Field(default_factory=list)
    clinical_notes: List[str] = Field(default_factory=list)
    disclaimer: str = ""


class DiagnosisResultOut(BaseModel):
    id: UUID
    patient_id: UUID
    processing_job_id: Optional[UUID] = None
    chief_complaint: Optional[str] = None
    focus_symptoms_json: List[str] = Field(default_factory=list)
    symptom_analysis_json: Dict[str, Any] = Field(default_factory=dict)
    differential_diagnoses_json: List[Any] = Field(default_factory=list)
    probability_scores_json: List[Any] = Field(default_factory=list)
    severity_assessment_json: Dict[str, Any] = Field(default_factory=dict)
    treatment_path_json: Dict[str, Any] = Field(default_factory=dict)
    clinical_decision_support_json: Dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None
    engine: str = "rule_based"
    status: str = "Completed"
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class DiagnosisStartResponse(BaseModel):
    patient_id: UUID
    status: str = "Completed"
    processing_time_ms: int
    summary: str
    engine: str
    warnings: List[str] = Field(default_factory=list)
    symptom_analysis: SymptomAnalysisOut
    differential_diagnoses: List[DifferentialDiagnosisOut] = Field(default_factory=list)
    probability_scores: List[DiseaseProbabilityOut] = Field(default_factory=list)
    severity_assessment: SeverityAssessmentOut
    treatment_path: TreatmentPathOut
    clinical_decision_support: ClinicalDecisionSupportOut
    diagnosis_result: DiagnosisResultOut


class DiagnosisHistoryItemOut(BaseModel):
    id: UUID
    created_at: datetime
    summary: Optional[str] = None
    severity_level: Optional[str] = None
    top_condition: Optional[str] = None
    status: str = "Completed"
