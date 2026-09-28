"""LLM-backed fraud-screening stage with deterministic findings as guardrails."""

from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from app.ai.insurance.models import FraudScreening
from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin


class FraudDetector(OrchestratorCallMixin):
    def screen(
        self,
        *,
        patient_id: UUID,
        service_name: str,
        billed_amount: float,
        service_date: str,
        policy: Dict[str, Any],
        verification: Dict[str, Any],
        rule_findings: list[str],
        prior_claims: list[Dict[str, Any]],
    ) -> FraudScreening:
        data = self._call(
            agent="insurance",
            task="fraud_detection",
            patient_id=patient_id,
            response_model=FraudScreening,
            extra_vars={
                "service_name": service_name,
                "billed_amount": billed_amount,
                "service_date": service_date,
                "policy": policy,
                "policy_verification": verification,
                "rule_findings": rule_findings,
                "prior_claims": prior_claims[-10:],
            },
        )
        result = FraudScreening.model_validate(data)
        # LLM output cannot erase deterministic evidence.
        result.rule_findings = list(dict.fromkeys(rule_findings + result.rule_findings))
        return result
