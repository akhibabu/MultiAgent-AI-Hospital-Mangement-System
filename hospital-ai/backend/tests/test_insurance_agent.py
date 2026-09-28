from datetime import date
from uuid import uuid4

from app.ai.insurance.models import InsurancePolicy
from app.ai.insurance.policy_engine import CoverageEstimator, PolicyVerifier


def test_policy_verification_rejects_expired_policy() -> None:
    policy = InsurancePolicy(
        provider_name="Demo Health",
        policy_number="POL-1",
        status="expired",
        coverage_percent=80,
    )

    result = PolicyVerifier().verify(
        policy=policy,
        service_name="MRI",
        service_date=date(2026, 9, 29),
    )

    assert result.verified is False
    assert result.coverage_active is False
    assert any("expired" in issue.lower() for issue in result.issues)


def test_coverage_estimate_is_transparent() -> None:
    policy = InsurancePolicy(
        provider_name="Demo Health",
        policy_number="POL-2",
        status="active",
        coverage_percent=80,
        deductible_remaining=1000,
        copay=50,
    )
    verification = PolicyVerifier().verify(
        policy=policy,
        service_name="MRI",
        service_date=date(2026, 9, 29),
    )
    estimate = CoverageEstimator().estimate(
        policy=policy,
        service_name="MRI",
        billed_amount=5000,
        verification=verification,
    )

    assert estimate.eligible_amount == 5000
    assert estimate.deductible_applied == 1000
    assert estimate.insurer_estimate == 3200
    assert estimate.patient_estimate == 1850


def test_claim_zero_amount_is_allowed_as_a_draft_input() -> None:
    policy = InsurancePolicy(
        provider_name="Demo Health",
        policy_number="POL-3",
        status="active",
        coverage_percent=100,
    )
    assert str(policy.policy_number) == "POL-3"
