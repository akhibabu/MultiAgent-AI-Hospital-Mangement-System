"""Insurance Agent pipeline.

Patient + policy terms + clinical context
-> Policy Verification
-> Coverage Estimation
-> Claim Generation
-> Fraud Screening
-> Preauthorization Review.

The agent drafts and estimates only. It never contacts an insurer, makes a
binding coverage decision, files a claim, or declares fraud.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.insurance.claim_generator import ClaimGenerator
from app.ai.insurance.fraud_detector import FraudDetector
from app.ai.insurance.models import (
    InsurancePolicy,
    InsuranceReport,
)
from app.ai.insurance.preauthorization import PreauthorizationAdvisor
from app.ai.insurance.policy_engine import CoverageEstimator, PolicyVerifier
from app.ai.orchestrator.agent_helpers import collect_debug
from app.core.logging import get_logger
from app.repositories.intake_repositories import PatientRepository
from app.repositories.insurance_repository import InsuranceResultRepository

logger = get_logger("hospital_ai.insurance.pipeline")


def _service_match(service_name: str, values: List[str]) -> bool:
    normalized = service_name.strip().lower()
    return any(
        normalized == str(v).strip().lower()
        or normalized in str(v).strip().lower()
        or str(v).strip().lower() in normalized
        for v in values
        if str(v).strip()
    )


class InsurancePipeline:
    def __init__(
        self,
        *,
        patients: Optional[PatientRepository] = None,
        results: Optional[InsuranceResultRepository] = None,
        verifier: Optional[PolicyVerifier] = None,
        estimator: Optional[CoverageEstimator] = None,
        claim_generator: Optional[ClaimGenerator] = None,
        fraud_detector: Optional[FraudDetector] = None,
        preauthorization: Optional[PreauthorizationAdvisor] = None,
    ) -> None:
        self._patients = patients or PatientRepository()
        self._results = results or InsuranceResultRepository()
        self._verifier = verifier or PolicyVerifier()
        self._estimator = estimator or CoverageEstimator()
        self._claim = claim_generator or ClaimGenerator()
        self._fraud = fraud_detector or FraudDetector()
        self._preauth = preauthorization or PreauthorizationAdvisor()

    def run(
        self,
        *,
        patient_id: UUID,
        policy: InsurancePolicy,
        service_name: str,
        service_date: date,
        billed_amount: float,
        supporting_documents: Optional[List[str]] = None,
    ) -> InsuranceReport:
        patient = self._patients.get_full(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        if not service_name.strip():
            raise HTTPException(status_code=422, detail="Service name is required")

        warnings: List[str] = [
            "Insurance Agent outputs are decision-support drafts only.",
            "No live insurer eligibility, benefits, claim filing, or fraud registry is queried.",
            "Final coding, eligibility, coverage, claim submission, fraud review, and authorization "
            "must be completed by the appropriate human/insurer workflow.",
        ]

        verification = self._verifier.verify(
            policy=policy,
            service_name=service_name,
            service_date=service_date,
        )
        coverage = self._estimator.estimate(
            policy=policy,
            service_name=service_name,
            billed_amount=billed_amount,
            verification=verification,
        )

        clinical_context: Dict[str, Any] = {
            "patient": {
                "patient_id": str(patient_id),
                "patient_number": patient.get("patient_number"),
                "first_name": patient.get("first_name"),
                "last_name": patient.get("last_name"),
            },
            "insurance_provider_on_patient_record": patient.get("insurance_provider"),
            "insurance_number_on_patient_record": patient.get("insurance_number"),
            "medical_history": patient.get("medical_history"),
            "latest_diagnosis": patient.get("latest_diagnosis"),
            "service_name": service_name,
            "service_date": service_date.isoformat(),
            "billed_amount": billed_amount,
            "supporting_documents": supporting_documents or [],
        }

        claim = self._claim.generate(
            patient_id=patient_id,
            service_name=service_name,
            billed_amount=billed_amount,
            service_date=service_date.isoformat(),
            policy=policy.model_dump(mode="json"),
            verification=verification.model_dump(mode="json"),
            coverage=coverage.model_dump(mode="json"),
            extra_context=clinical_context,
        )

        prior_rows = self._results.list_for_patient(patient_id, limit=20)
        prior_claims = [row.get("request_json") or {} for row in prior_rows]

        rule_findings: List[str] = []
        if billed_amount <= 0:
            rule_findings.append("Billed amount is zero or negative.")
        if verification.issues:
            rule_findings.extend(f"Policy verification issue: {issue}" for issue in verification.issues)
        duplicate = any(
            str(item.get("service_name", "")).strip().lower() == service_name.strip().lower()
            and str(item.get("service_date", ""))[:10] == service_date.isoformat()
            for item in prior_claims
        )
        if duplicate:
            rule_findings.append(
                "A prior Insurance Agent run has the same service and service date; review for duplication."
            )
        if not supporting_documents:
            rule_findings.append("No supporting documents were supplied for this draft.")

        fraud = self._fraud.screen(
            patient_id=patient_id,
            service_name=service_name,
            billed_amount=billed_amount,
            service_date=service_date.isoformat(),
            policy=policy.model_dump(mode="json"),
            verification=verification.model_dump(mode="json"),
            rule_findings=rule_findings,
            prior_claims=prior_claims,
        )

        authorization_required = _service_match(
            service_name,
            policy.preauthorization_services,
        )

        preauth = self._preauth.review(
            patient_id=patient_id,
            service_name=service_name,
            estimated_cost=coverage.insurer_estimate,
            authorization_required=authorization_required,
            policy=policy.model_dump(mode="json"),
            verification=verification.model_dump(mode="json"),
            clinical_context={
                **clinical_context,
                "claim_draft": claim.model_dump(mode="json"),
                "fraud_screening": fraud.model_dump(mode="json"),
            },
        )

        if authorization_required and preauth.status == "not_required":
            preauth.status = "review_required"

        summary = (
            f"Insurance Agent prepared a draft for {service_name}: policy verification is "
            f"{'passed' if verification.verified else 'incomplete'}, estimated insurer share "
            f"is ₹{coverage.insurer_estimate:,.2f}, patient share is ₹{coverage.patient_estimate:,.2f}, "
            f"fraud-screening risk is {fraud.risk_level}, and preauthorization is "
            f"{preauth.status.replace('_', ' ')}. Human review is required."
        )

        return InsuranceReport(
            patient_id=str(patient_id),
            service_name=service_name,
            service_date=service_date,
            billed_amount=max(float(billed_amount), 0.0),
            policy=policy,
            policy_verification=verification,
            coverage_estimate=coverage,
            claim_draft=claim,
            fraud_screening=fraud,
            preauthorization=preauth,
            summary=summary,
            warnings=warnings,
            ai_debug=collect_debug(self._claim, self._fraud, self._preauth),
        )
