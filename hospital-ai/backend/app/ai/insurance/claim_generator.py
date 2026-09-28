"""LLM-backed insurance claim draft generation."""

from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from app.ai.insurance.models import ClaimDraft
from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin


class ClaimGenerator(OrchestratorCallMixin):
    def generate(
        self,
        *,
        patient_id: UUID,
        service_name: str,
        billed_amount: float,
        service_date: str,
        policy: Dict[str, Any],
        verification: Dict[str, Any],
        coverage: Dict[str, Any],
        extra_context: Dict[str, Any] | None = None,
    ) -> ClaimDraft:
        data = self._call(
            agent="insurance",
            task="claim_generation",
            patient_id=patient_id,
            response_model=ClaimDraft,
            extra_vars={
                "service_name": service_name,
                "billed_amount": billed_amount,
                "service_date": service_date,
                "policy": policy,
                "policy_verification": verification,
                "coverage_estimate": coverage,
                "clinical_context": extra_context or {},
            },
        )
        return ClaimDraft.model_validate(data)
