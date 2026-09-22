"""Pydantic schemas for the Prescription Agent."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.ai_orchestrator import OrchestratorDebugInfoOut


class PrescriptionStartRequest(BaseModel):
    patient_id: UUID
    diagnosis_result_id: Optional[UUID] = None
    research_result_id: Optional[UUID] = None


class MedicationRecommendationOut(BaseModel):
    condition: str
    medication_name: str
    drug_class: str
    purpose: str = ""
    evidence_source: str = ""
    clinical_guideline: str = ""
    confidence: float = 0.0
    alternative_drugs: List[str] = Field(default_factory=list)
    expected_outcome: str = ""


class DrugInteractionOut(BaseModel):
    drug_a: str
    drug_b: str
    interaction_level: str = "Minor"
    explanation: str = ""
    recommendation: str = ""


class AllergyCheckItemOut(BaseModel):
    medication_name: str
    status: str = "Safe"
    reason: str = ""
    cross_reactivity: List[str] = Field(default_factory=list)


class DosageRecommendationOut(BaseModel):
    medication_name: str
    starting_dose: str = ""
    maintenance_dose: str = ""
    maximum_dose: str = ""
    dose_adjustment: List[str] = Field(default_factory=list)
    adjustment_factors: List[str] = Field(default_factory=list)


class TreatmentPlanOut(BaseModel):
    medication_plan: List[str] = Field(default_factory=list)
    lifestyle_advice: List[str] = Field(default_factory=list)
    monitoring_plan: List[str] = Field(default_factory=list)
    recommended_lab_tests: List[str] = Field(default_factory=list)
    recommended_imaging: List[str] = Field(default_factory=list)
    recommended_specialists: List[str] = Field(default_factory=list)
    follow_up_interval: str = ""
    emergency_advice: str = ""
    surgery_required: bool = False
    procedure_recommendations: List[str] = Field(default_factory=list)
    estimated_duration_minutes: Optional[int] = Field(default=None, ge=30, le=480)


class PrescriptionValidationOut(BaseModel):
    duplicate_drugs: List[str] = Field(default_factory=list)
    contraindications_found: List[str] = Field(default_factory=list)
    max_dose_exceeded: List[str] = Field(default_factory=list)
    allergy_conflicts: List[str] = Field(default_factory=list)
    drug_warnings: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    approval_status: str = "Requires Physician Review"
    notes: List[str] = Field(default_factory=list)


class PrescriptionResultOut(BaseModel):
    id: UUID
    patient_id: UUID
    diagnosis_result_id: Optional[UUID] = None
    research_result_id: Optional[UUID] = None
    target_conditions_json: List[str] = Field(default_factory=list)
    medication_recommendations_json: List[Any] = Field(default_factory=list)
    drug_interactions_json: List[Any] = Field(default_factory=list)
    allergy_checks_json: List[Any] = Field(default_factory=list)
    dosage_recommendations_json: List[Any] = Field(default_factory=list)
    treatment_plan_json: Dict[str, Any] = Field(default_factory=dict)
    validation_summary_json: Dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None
    engine: str = "rule_based"
    status: str = "Completed"
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class PrescriptionStartResponse(BaseModel):
    patient_id: UUID
    diagnosis_result_id: Optional[UUID] = None
    research_result_id: Optional[UUID] = None
    status: str = "Completed"
    processing_time_ms: int
    summary: str
    engine: str
    warnings: List[str] = Field(default_factory=list)
    target_conditions: List[str] = Field(default_factory=list)
    medication_recommendations: List[MedicationRecommendationOut] = Field(default_factory=list)
    drug_interactions: List[DrugInteractionOut] = Field(default_factory=list)
    allergy_checks: List[AllergyCheckItemOut] = Field(default_factory=list)
    dosage_recommendations: List[DosageRecommendationOut] = Field(default_factory=list)
    treatment_plan: TreatmentPlanOut
    validation: PrescriptionValidationOut
    prescription_result: PrescriptionResultOut
    ai_debug: List[OrchestratorDebugInfoOut] = Field(default_factory=list)


class PrescriptionHistoryItemOut(BaseModel):
    id: UUID
    created_at: datetime
    summary: Optional[str] = None
    approval_status: Optional[str] = None
    target_conditions: List[str] = Field(default_factory=list)
    status: str = "Completed"


class PrescriptionStatusOut(BaseModel):
    """Lightweight status summary — mirrors the Intake Agent's status shape."""

    patient_id: UUID
    has_result: bool = False
    status: str = "Not Started"
    approval_status: Optional[str] = None
    confidence_score: Optional[float] = None
    target_conditions: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: Optional[datetime] = None
