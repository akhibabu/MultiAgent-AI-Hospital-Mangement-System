"""Pydantic schemas for the Medical Report Agent."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.ai_orchestrator import OrchestratorDebugInfoOut


class MedicalReportStartRequest(BaseModel):
    patient_id: UUID
    diagnosis_result_id: Optional[UUID] = None
    research_result_id: Optional[UUID] = None
    prescription_result_id: Optional[UUID] = None
    receiving_specialist: Optional[str] = None


class ClinicalSummaryOut(BaseModel):
    patient_overview: str = ""
    chief_complaint: str = ""
    history: str = ""
    diagnosis_summary: str = ""
    current_status: str = ""
    key_findings: List[str] = Field(default_factory=list)


class DoctorNotesOut(BaseModel):
    subjective: str = ""
    objective: str = ""
    assessment: str = ""
    plan: str = ""
    clinical_reasoning: str = ""


class DischargeSummaryOut(BaseModel):
    admission_reason: str = ""
    hospital_course: str = ""
    procedures: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    condition_on_discharge: str = ""
    follow_up: str = ""
    emergency_instructions: str = ""


class ReferralLetterOut(BaseModel):
    id: Optional[UUID] = None
    receiving_specialist: str = ""
    reason: str = ""
    history: str = ""
    important_findings: List[str] = Field(default_factory=list)
    investigations: List[str] = Field(default_factory=list)
    requested_evaluation: str = ""
    letter_body: str = ""


class InsuranceDocumentationOut(BaseModel):
    id: Optional[UUID] = None
    diagnosis_codes: List[Dict[str, str]] = Field(default_factory=list)
    procedure_codes: List[Dict[str, str]] = Field(default_factory=list)
    supporting_documents: List[str] = Field(default_factory=list)
    medical_necessity: str = ""
    claim_summary: str = ""
    supporting_evidence: List[str] = Field(default_factory=list)


class FAQItemOut(BaseModel):
    question: str
    answer: str


class PatientReportOut(BaseModel):
    diagnosis_summary: str = ""
    treatment_summary: str = ""
    current_medicines: List[str] = Field(default_factory=list)
    lifestyle_advice: List[str] = Field(default_factory=list)
    diet: List[str] = Field(default_factory=list)
    exercise: List[str] = Field(default_factory=list)
    follow_up: str = ""
    emergency_contact_instructions: str = ""
    faq: List[FAQItemOut] = Field(default_factory=list)


class GeneratedMedicalReportOut(BaseModel):
    id: UUID
    patient_id: UUID
    diagnosis_result_id: Optional[UUID] = None
    research_result_id: Optional[UUID] = None
    prescription_result_id: Optional[UUID] = None
    clinical_summary_json: Dict[str, Any] = Field(default_factory=dict)
    doctor_notes_json: Dict[str, Any] = Field(default_factory=dict)
    discharge_summary_json: Dict[str, Any] = Field(default_factory=dict)
    referral_letter_json: Dict[str, Any] = Field(default_factory=dict)
    insurance_documentation_json: Dict[str, Any] = Field(default_factory=dict)
    patient_report_json: Dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None
    engine: str = "template_based"
    version: int = 1
    status: str = "Completed"
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class MedicalReportStartResponse(BaseModel):
    patient_id: UUID
    diagnosis_result_id: Optional[UUID] = None
    research_result_id: Optional[UUID] = None
    prescription_result_id: Optional[UUID] = None
    status: str = "Completed"
    processing_time_ms: int
    summary: str
    engine: str
    version: int
    warnings: List[str] = Field(default_factory=list)
    clinical_summary: ClinicalSummaryOut
    doctor_notes: DoctorNotesOut
    discharge_summary: DischargeSummaryOut
    referral_letter: ReferralLetterOut
    insurance_documentation: InsuranceDocumentationOut
    patient_report: PatientReportOut
    generated_report: GeneratedMedicalReportOut
    ai_debug: List[OrchestratorDebugInfoOut] = Field(default_factory=list)


class MedicalReportHistoryItemOut(BaseModel):
    id: UUID
    created_at: datetime
    version: int = 1
    summary: Optional[str] = None
    status: str = "Completed"


class MedicalReportStatusOut(BaseModel):
    """Lightweight status summary — mirrors the Intake Agent's status shape."""

    patient_id: UUID
    has_result: bool = False
    status: str = "Not Started"
    version: Optional[int] = None
    summary: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: Optional[datetime] = None
