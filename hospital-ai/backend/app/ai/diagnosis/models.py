"""Diagnosis Agent domain models — Clinical Decision Support output shapes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.ai.orchestrator.models import OrchestratorDebugInfo

SEVERITY_LEVELS = ("Very Low", "Low", "Moderate", "High", "Critical")

DIAGNOSIS_DISCLAIMER = (
    "Clinical decision-support output only. Assists — never replaces — a "
    "physician's judgment. Does not prescribe medication and does not "
    "diagnose with certainty."
)


class SymptomCluster(BaseModel):
    """Group of related symptoms mapped to a body system."""

    body_system: str
    symptoms: List[str] = Field(default_factory=list)
    duration_hint: Optional[str] = None
    severity_hint: Optional[str] = None
    related_conditions: List[str] = Field(default_factory=list)


class SymptomAnalysis(BaseModel):
    clusters: List[SymptomCluster] = Field(default_factory=list)
    total_symptoms: int = 0
    notable_vitals: List[Dict[str, Any]] = Field(default_factory=list)
    notable_labs: List[Dict[str, Any]] = Field(default_factory=list)
    narrative: str = ""


class DifferentialDiagnosis(BaseModel):
    """Single candidate condition with evidence for and against."""

    condition: str
    confidence: float = 0.0
    supporting_symptoms: List[str] = Field(default_factory=list)
    supporting_labs: List[str] = Field(default_factory=list)
    supporting_history: List[str] = Field(default_factory=list)
    contradicting_evidence: List[str] = Field(default_factory=list)
    recommended_specialists: List[str] = Field(default_factory=list)
    body_system: Optional[str] = None


class DiseaseProbability(BaseModel):
    """Calibrated probability score for one candidate condition."""

    condition: str
    probability_pct: float = 0.0
    confidence: float = 0.0
    evidence_used: List[str] = Field(default_factory=list)
    risk_contribution: float = 0.0
    risk_category: Optional[str] = None


class SeverityAssessment(BaseModel):
    level: str = "Very Low"
    score: float = 0.0
    explanation: str = ""
    contributing_factors: List[str] = Field(default_factory=list)


class TreatmentPathRecommendation(BaseModel):
    """Referral pathway only — never medication."""

    recommended_specialists: List[str] = Field(default_factory=list)
    recommended_department: Optional[str] = None
    diagnostic_tests: List[str] = Field(default_factory=list)
    imaging: List[str] = Field(default_factory=list)
    urgency: str = "Routine"
    notes: str = ""


class ClinicalDecisionSupport(BaseModel):
    """Final clinician-facing decision-support report."""

    possible_diagnoses: List[str] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    suggested_tests: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    relevant_history: List[str] = Field(default_factory=list)
    clinical_notes: List[str] = Field(default_factory=list)
    disclaimer: str = DIAGNOSIS_DISCLAIMER


class DiagnosisReport(BaseModel):
    """Aggregate result of the full 6-stage Diagnosis Agent pipeline."""

    patient_id: str
    chief_complaint: Optional[str] = None
    focus_symptoms: List[str] = Field(default_factory=list)
    symptom_analysis: SymptomAnalysis = Field(default_factory=SymptomAnalysis)
    differential_diagnoses: List[DifferentialDiagnosis] = Field(default_factory=list)
    probability_scores: List[DiseaseProbability] = Field(default_factory=list)
    severity_assessment: SeverityAssessment = Field(default_factory=SeverityAssessment)
    treatment_path: TreatmentPathRecommendation = Field(
        default_factory=TreatmentPathRecommendation
    )
    clinical_decision_support: ClinicalDecisionSupport = Field(
        default_factory=ClinicalDecisionSupport
    )
    summary: str = ""
    engine: str = "ai_orchestrator"
    warnings: List[str] = Field(default_factory=list)
    ai_debug: List[OrchestratorDebugInfo] = Field(default_factory=list)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")
