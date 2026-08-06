"""Medical Report Agent domain models — professional hospital documentation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.ai.orchestrator.models import OrchestratorDebugInfo

MEDICAL_REPORT_DISCLAIMER = (
    "Generated documentation synthesized from Intake, Diagnosis, Research, and "
    "Prescription Agent output. Assists — never replaces — clinician review. "
    "All content must be verified and signed off by a licensed physician "
    "before use in a patient's official medical record, referral, or claim."
)


class FAQItem(BaseModel):
    question: str
    answer: str


class ClinicalSummary(BaseModel):
    """Stage 1 — Clinical Summary."""

    patient_overview: str = ""
    chief_complaint: str = ""
    history: str = ""
    diagnosis_summary: str = ""
    current_status: str = ""
    key_findings: List[str] = Field(default_factory=list)


class DoctorNotes(BaseModel):
    """Stage 2 — Doctor Notes Generation (SOAP)."""

    subjective: str = ""
    objective: str = ""
    assessment: str = ""
    plan: str = ""
    clinical_reasoning: str = ""


class DischargeSummary(BaseModel):
    """Stage 3 — Discharge Summary."""

    admission_reason: str = ""
    hospital_course: str = ""
    procedures: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    condition_on_discharge: str = ""
    follow_up: str = ""
    emergency_instructions: str = ""


class ReferralLetter(BaseModel):
    """Stage 4 — Referral Letter Creation."""

    receiving_specialist: str = ""
    reason: str = ""
    history: str = ""
    important_findings: List[str] = Field(default_factory=list)
    investigations: List[str] = Field(default_factory=list)
    requested_evaluation: str = ""
    letter_body: str = ""


class InsuranceDocumentation(BaseModel):
    """Stage 5 — Insurance Documentation."""

    diagnosis_codes: List[Dict[str, str]] = Field(default_factory=list)
    procedure_codes: List[Dict[str, str]] = Field(default_factory=list)
    supporting_documents: List[str] = Field(default_factory=list)
    medical_necessity: str = ""
    claim_summary: str = ""
    supporting_evidence: List[str] = Field(default_factory=list)


class PatientReport(BaseModel):
    """Stage 6 — Patient Report Generation. Plain language, no medical jargon."""

    diagnosis_summary: str = ""
    treatment_summary: str = ""
    current_medicines: List[str] = Field(default_factory=list)
    lifestyle_advice: List[str] = Field(default_factory=list)
    diet: List[str] = Field(default_factory=list)
    exercise: List[str] = Field(default_factory=list)
    follow_up: str = ""
    emergency_contact_instructions: str = ""
    faq: List[FAQItem] = Field(default_factory=list)


class MedicalReportBundle(BaseModel):
    """Aggregate result of the full 6-stage Medical Report Agent pipeline."""

    patient_id: str
    diagnosis_result_id: Optional[str] = None
    research_result_id: Optional[str] = None
    prescription_result_id: Optional[str] = None
    clinical_summary: ClinicalSummary = Field(default_factory=ClinicalSummary)
    doctor_notes: DoctorNotes = Field(default_factory=DoctorNotes)
    discharge_summary: DischargeSummary = Field(default_factory=DischargeSummary)
    referral_letter: ReferralLetter = Field(default_factory=ReferralLetter)
    insurance_documentation: InsuranceDocumentation = Field(default_factory=InsuranceDocumentation)
    patient_report: PatientReport = Field(default_factory=PatientReport)
    summary: str = ""
    engine: str = "ai_orchestrator"
    version: int = 1
    warnings: List[str] = Field(default_factory=list)
    ai_debug: List[OrchestratorDebugInfo] = Field(default_factory=list)
    disclaimer: str = MEDICAL_REPORT_DISCLAIMER
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")
