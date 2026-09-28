"""API schemas for the Insurance Agent."""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.insurance.models import (
    ClaimDraft,
    CoverageEstimate,
    FraudScreening,
    InsurancePolicy,
    PolicyVerification,
    PreauthorizationReview,
)
from app.schemas.ai_orchestrator import OrchestratorDebugInfoOut


class InsuranceStartRequest(BaseModel):
    patient_id: UUID
    service_name: str = Field(min_length=1, max_length=200)
    service_date: date
    billed_amount: float = Field(ge=0)
    supporting_documents: List[str] = Field(default_factory=list)
    policy: InsurancePolicy


class InsuranceResultOut(BaseModel):
    id: UUID
    patient_id: UUID
    service_name: str
    service_date: date
    billed_amount: float
    policy_json: InsurancePolicy
    policy_verification_json: PolicyVerification
    coverage_estimate_json: CoverageEstimate
    claim_draft_json: ClaimDraft
    fraud_screening_json: FraudScreening
    preauthorization_json: PreauthorizationReview
    summary: str
    engine: str
    status: str
    warnings_json: List[str] = Field(default_factory=list)
    processing_time_ms: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class InsuranceStartResponse(BaseModel):
    patient_id: UUID
    service_name: str
    service_date: date
    billed_amount: float
    status: str
    processing_time_ms: int
    summary: str
    policy: InsurancePolicy
    policy_verification: PolicyVerification
    coverage_estimate: CoverageEstimate
    claim_draft: ClaimDraft
    fraud_screening: FraudScreening
    preauthorization: PreauthorizationReview
    warnings: List[str] = Field(default_factory=list)
    insurance_result: InsuranceResultOut
    ai_debug: List[OrchestratorDebugInfoOut] = Field(default_factory=list)


class InsuranceHistoryItemOut(BaseModel):
    id: UUID
    created_at: datetime
    service_name: str
    billed_amount: float
    policy_number: str
    status: str
