"""Deterministic policy verification and coverage estimation."""

from __future__ import annotations

from datetime import date
import re

from app.ai.insurance.models import CoverageEstimate, InsurancePolicy, PolicyVerification


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _matches_service(service_name: str, values: list[str]) -> bool:
    service = _norm(service_name)
    return any(
        service == _norm(value)
        or service in _norm(value)
        or _norm(value) in service
        for value in values
        if _norm(value)
    )


class PolicyVerifier:
    """Checks consistency of the policy snapshot supplied by hospital staff."""

    def verify(
        self,
        *,
        policy: InsurancePolicy,
        service_name: str,
        service_date: date,
        checked_on: date | None = None,
    ) -> PolicyVerification:
        checked_on = checked_on or date.today()
        issues: list[str] = []
        notes: list[str] = []

        if not policy.provider_name.strip():
            issues.append("Insurance provider is missing.")
        if not policy.policy_number.strip():
            issues.append("Policy number is missing.")

        if policy.status == "expired":
            issues.append("Policy is marked expired.")
        elif policy.status == "inactive":
            issues.append("Policy is marked inactive.")
        elif policy.status == "unknown":
            issues.append("Policy status was not supplied.")
        elif policy.status != "active":
            issues.append("Policy is not marked active.")

        if policy.effective_from and service_date < policy.effective_from:
            issues.append("Service date is before the policy effective date.")
        if policy.effective_to and service_date > policy.effective_to:
            issues.append("Service date is after the policy termination date.")

        if _matches_service(service_name, policy.excluded_services):
            issues.append("Requested service is listed as excluded.")

        if policy.covered_services and not _matches_service(service_name, policy.covered_services):
            notes.append(
                "The service is not explicitly listed in the supplied covered-service list; "
                "carrier policy wording must be checked."
            )
        elif not policy.covered_services:
            notes.append("No explicit covered-service list was supplied.")

        if policy.coverage_percent <= 0:
            notes.append("Coverage percentage is zero or not supplied.")

        coverage_active = policy.status == "active" and not issues

        return PolicyVerification(
            verified=not issues,
            coverage_active=coverage_active,
            provider_name=policy.provider_name,
            policy_number=policy.policy_number,
            policy_status=policy.status,
            service_name=service_name,
            checked_on=checked_on,
            issues=issues,
            notes=notes,
        )


class CoverageEstimator:
    """Calculates a transparent estimate from the supplied policy terms."""

    def estimate(
        self,
        *,
        policy: InsurancePolicy,
        service_name: str,
        billed_amount: float,
        verification: PolicyVerification,
    ) -> CoverageEstimate:
        billed = max(float(billed_amount), 0.0)
        eligible = (
            billed
            if verification.coverage_active and not _matches_service(service_name, policy.excluded_services)
            else 0.0
        )

        deductible = min(max(policy.deductible_remaining, 0.0), eligible)
        after_deductible = max(eligible - deductible, 0.0)
        insurer = after_deductible * (policy.coverage_percent / 100.0)
        patient_share = deductible + max(after_deductible - insurer, 0.0) + policy.copay
        patient = min(billed, max(patient_share, 0.0))

        assumptions = [
            "Estimate uses only policy terms entered into the hospital system.",
            "Final eligibility, coding, pricing, and reimbursement may differ.",
            "No live insurer eligibility or benefits API is contacted by this agent.",
        ]
        if policy.annual_limit_remaining is not None:
            assumptions.append("Annual benefit limits are displayed as supplied but not modeled.")
        if policy.out_of_pocket_remaining is not None:
            assumptions.append("Out-of-pocket accumulators are displayed as supplied but not modeled.")

        return CoverageEstimate(
            service_name=service_name,
            billed_amount=round(billed, 2),
            eligible_amount=round(eligible, 2),
            deductible_applied=round(deductible, 2),
            coverage_percent=policy.coverage_percent,
            copay=round(policy.copay, 2),
            insurer_estimate=round(max(insurer, 0.0), 2),
            patient_estimate=round(patient, 2),
            assumptions=assumptions,
        )
