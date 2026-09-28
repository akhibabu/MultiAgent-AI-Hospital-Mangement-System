"""Domain models for the Insurance Agent."""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Literal

from pydantic import BaseModel, Field

from app.ai.orchestrator.models import OrchestratorDebugInfo

PolicyStatus = Literal["active", "inactive", "expired", "unknown"]
FraudRiskLevel = Literal["low", "medium", "high"]
PreauthorizationStatus = Literal[
    "not_required", "ready_for_review", "insufficient_information", "review_required"
]


class InsurancePolicy(BaseModel):
    provider_name: str = ""
    policy_number: str = ""
    member_id: Optional[str] = None
    plan_name: str = ""
    status: PolicyStatus = "unknown"
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    coverage_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    deductible_remaining: float = Field(default=0.0, ge=0.0)
    out_of_pocket_remaining: Optional[float] = Field(default=None, ge=0.0)
    annual_limit_remaining: Optional[float] = Field(default=None, ge=0.0)
    copay: float = Field(default=0.0, ge=0.0)
    covered_services: List[str] = Field(default_factory=list)
    excluded_services: List[str] = Field(default_factory=list)
    preauthorization_services: List[str] = Field(default_factory=list)


class PolicyVerification(BaseModel):
    verified: bool = False
    coverage_active: bool = False
    provider_name: str = ""
    policy_number: str = ""
    policy_status: str = "unknown"
    service_name: str = ""
    checked_on: date
    issues: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class CoverageEstimate(BaseModel):
    service_name: str = ""
    billed_amount: float = Field(default=0.0, ge=0.0)
    eligible_amount: float = Field(default=0.0, ge=0.0)
    deductible_applied: float = Field(default=0.0, ge=0.0)
    coverage_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    copay: float = Field(default=0.0, ge=0.0)
    insurer_estimate: float = Field(default=0.0, ge=0.0)
    patient_estimate: float = Field(default=0.0, ge=0.0)
    assumptions: List[str] = Field(default_factory=list)


class ClaimLine(BaseModel):
    service_name: str
    procedure_code: Optional[str] = None
    diagnosis_codes: List[str] = Field(default_factory=list)
    amount: float = Field(default=0.0, ge=0.0)
    documentation_required: List[str] = Field(default_factory=list)


class ClaimDraft(BaseModel):
    claim_status: str = "DRAFT — PHYSICIAN/BILLING REVIEW REQUIRED"
    claim_narrative: str = ""
    diagnosis_codes: List[str] = Field(default_factory=list)
    procedure_codes: List[str] = Field(default_factory=list)
    lines: List[ClaimLine] = Field(default_factory=list)
    supporting_documents: List[str] = Field(default_factory=list)
    missing_documents: List[str] = Field(default_factory=list)
    total_billed_amount: float = Field(default=0.0, ge=0.0)
    review_required: bool = True


class FraudScreening(BaseModel):
    risk_level: FraudRiskLevel = "low"
    risk_score: float = Field(default=0.0, ge=0.0, le=100.0)
    flags: List[str] = Field(default_factory=list)
    rule_findings: List[str] = Field(default_factory=list)
    rationale: str = ""
    recommendation: str = ""
    review_required: bool = True


class PreauthorizationReview(BaseModel):
    authorization_required: bool = False
    status: PreauthorizationStatus = "not_required"
    service_name: str = ""
    estimated_cost: float = Field(default=0.0, ge=0.0)
    clinical_necessity_summary: str = ""
    required_documents: List[str] = Field(default_factory=list)
    recommendation: str = ""
    review_required: bool = True


class InsuranceReport(BaseModel):
    patient_id: str
    service_name: str
    service_date: date
    billed_amount: float = Field(default=0.0, ge=0.0)
    policy: InsurancePolicy
    policy_verification: PolicyVerification
    coverage_estimate: CoverageEstimate
    claim_draft: ClaimDraft
    fraud_screening: FraudScreening
    preauthorization: PreauthorizationReview
    summary: str = ""
    engine: str = "ai_orchestrator"
    warnings: List[str] = Field(default_factory=list)
    ai_debug: List[OrchestratorDebugInfo] = Field(default_factory=list)

    @property
    def total_patient_estimate(self) -> float:
        return self.coverage_estimate.patient_estimate

    def as_json(self) -> Dict[str, object]:
        return self.model_dump(mode="json")
