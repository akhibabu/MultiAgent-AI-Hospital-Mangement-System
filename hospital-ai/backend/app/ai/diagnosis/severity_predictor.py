"""Diagnosis Agent — Step 4: Severity Prediction."""

from __future__ import annotations

from uuid import UUID

from app.ai.diagnosis.models import SeverityAssessment
from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.repositories.patient_context_repository import PatientClinicalContext


class SeverityPredictor(OrchestratorCallMixin):
    """
    Estimates Very Low -> Critical severity via the AI Orchestrator
    (`diagnosis` agent, `severity_prediction` task), grounded in vitals,
    labs, risk profile, and the leading differential diagnoses.
    """

    def predict(
        self,
        context: PatientClinicalContext,
        top_condition_weight: float = 0.0,
        *,
        differentials: list | None = None,
    ) -> SeverityAssessment:
        data = self._call(
            agent="diagnosis",
            task="severity_prediction",
            patient_id=UUID(context.patient_id),
            response_model=SeverityAssessment,
            extra_vars={
                "differentials": differentials or [],
                "top_condition_weight": top_condition_weight,
            },
        )
        return SeverityAssessment.model_validate(data)
