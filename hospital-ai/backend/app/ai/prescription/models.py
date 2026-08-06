"""Prescription Agent domain models — physician-review treatment recommendations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.ai.orchestrator.models import OrchestratorDebugInfo

INTERACTION_LEVELS = ("Minor", "Moderate", "Major", "Critical")
ALLERGY_STATUSES = ("Safe", "Warning", "Contraindicated")
APPROVAL_STATUSES = ("Approved", "Requires Physician Review", "Rejected")

PRESCRIPTION_DISCLAIMER = (
    "Physician-review treatment recommendation only. Assists — never replaces "
    "— a physician's judgment. This is NOT a final prescription; a licensed "
    "physician must review, adjust, and sign off before any medication is "
    "dispensed or administered."
)


class MedicationRecommendation(BaseModel):
    """Single medication suggestion supported by diagnosis + evidence."""

    condition: str
    medication_name: str
    drug_class: str
    purpose: str = ""
    evidence_source: str = ""
    clinical_guideline: str = ""
    confidence: float = 0.0
    alternative_drugs: List[str] = Field(default_factory=list)
    expected_outcome: str = ""


class DrugInteraction(BaseModel):
    """Interaction between two medications (current + suggested, or suggested + suggested)."""

    drug_a: str
    drug_b: str
    interaction_level: str = "Minor"
    explanation: str = ""
    recommendation: str = ""


class AllergyCheckItem(BaseModel):
    """Cross-check of a suggested medication against patient allergies."""

    medication_name: str
    status: str = "Safe"
    reason: str = ""
    cross_reactivity: List[str] = Field(default_factory=list)


class DosageRecommendation(BaseModel):
    """Dosage RANGE only — never a final prescribed dose."""

    medication_name: str
    starting_dose: str = ""
    maintenance_dose: str = ""
    maximum_dose: str = ""
    dose_adjustment: List[str] = Field(default_factory=list)
    adjustment_factors: List[str] = Field(default_factory=list)


class TreatmentPlan(BaseModel):
    """Holistic plan synthesized from all prior stages."""

    medication_plan: List[str] = Field(default_factory=list)
    lifestyle_advice: List[str] = Field(default_factory=list)
    monitoring_plan: List[str] = Field(default_factory=list)
    recommended_lab_tests: List[str] = Field(default_factory=list)
    recommended_imaging: List[str] = Field(default_factory=list)
    recommended_specialists: List[str] = Field(default_factory=list)
    follow_up_interval: str = ""
    emergency_advice: str = ""


class PrescriptionValidation(BaseModel):
    """Final safety validation — the Prescription Agent's last gate before physician review."""

    duplicate_drugs: List[str] = Field(default_factory=list)
    contraindications_found: List[str] = Field(default_factory=list)
    max_dose_exceeded: List[str] = Field(default_factory=list)
    allergy_conflicts: List[str] = Field(default_factory=list)
    drug_warnings: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    approval_status: str = "Requires Physician Review"
    notes: List[str] = Field(default_factory=list)


class PrescriptionReport(BaseModel):
    """Aggregate result of the full 6-stage Prescription Agent pipeline."""

    patient_id: str
    diagnosis_result_id: Optional[str] = None
    research_result_id: Optional[str] = None
    target_conditions: List[str] = Field(default_factory=list)
    medication_recommendations: List[MedicationRecommendation] = Field(default_factory=list)
    drug_interactions: List[DrugInteraction] = Field(default_factory=list)
    allergy_checks: List[AllergyCheckItem] = Field(default_factory=list)
    dosage_recommendations: List[DosageRecommendation] = Field(default_factory=list)
    treatment_plan: TreatmentPlan = Field(default_factory=TreatmentPlan)
    validation: PrescriptionValidation = Field(default_factory=PrescriptionValidation)
    summary: str = ""
    engine: str = "ai_orchestrator"
    warnings: List[str] = Field(default_factory=list)
    ai_debug: List[OrchestratorDebugInfo] = Field(default_factory=list)
    disclaimer: str = PRESCRIPTION_DISCLAIMER
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")
