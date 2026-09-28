"""LLM-backed preauthorization review stage."""

from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from app.ai.insurance.models import PreauthorizationReview
from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin


class PreauthorizationAdvisor(OrchestratorCallMixin):
    def review(
        self,
        *,
        patient_id: UUID,
        service_name: str,
        estimated_cost: float,
        authorization_required: bool,
        policy: Dict[str, Any],
        verification: Dict[str, Any],
        clinical_context: Dict[str, Any],
    ) -> PreauthorizationReview:
        if not authorization_required:
            return PreauthorizationReview(
                authorization_required=False,
                status="not_required",
                service_name=service_name,
                estimated_cost=estimated_cost,
                recommendation=(
                    "No preauthorization requirement was listed for this service in the supplied "
                    "policy terms. This is not a carrier-side confirmation."
                ),
                review_required=True,
            )

        data = self._call(
            agent="insurance",
            task="preauthorization",
            patient_id=patient_id,
            response_model=PreauthorizationReview,
            extra_vars={
                "service_name": service_name,
                "estimated_cost": estimated_cost,
                "authorization_required": authorization_required,
                "policy": policy,
                "policy_verification": verification,
                "clinical_context": clinical_context,
            },
        )
        result = PreauthorizationReview.model_validate(data)
        result.authorization_required = True
        result.service_name = service_name
        result.estimated_cost = estimated_cost
        return result
