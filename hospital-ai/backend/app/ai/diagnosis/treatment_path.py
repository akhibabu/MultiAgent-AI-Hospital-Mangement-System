"""Diagnosis Agent — Step 5: Treatment Path Recommendation (pathways only, never medication)."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from app.ai.diagnosis.knowledge_base import ConditionKnowledgeBase
from app.ai.diagnosis.models import (
    DifferentialDiagnosis,
    SeverityAssessment,
    TreatmentPathRecommendation,
)
from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin


class TreatmentPathRecommender(OrchestratorCallMixin):
    """
    Recommends a referral pathway ONLY — never a medication — via the AI
    Orchestrator (`diagnosis` agent, `treatment_path_recommendation`
    task). `ConditionKnowledgeBase` stays available as grounding data
    (specialist/department/test profiles per condition).
    """

    def __init__(self, knowledge_base: ConditionKnowledgeBase | None = None) -> None:
        self._kb = knowledge_base or ConditionKnowledgeBase()

    def recommend(
        self,
        differentials: List[DifferentialDiagnosis],
        severity: SeverityAssessment,
        *,
        patient_id: Optional[UUID] = None,
    ) -> TreatmentPathRecommendation:
        data = self._call(
            agent="diagnosis",
            task="treatment_path_recommendation",
            patient_id=patient_id,
            response_model=TreatmentPathRecommendation,
            extra_vars={
                "differentials": [d.model_dump(mode="json") for d in differentials[:3]],
                "severity": severity.model_dump(mode="json"),
            },
        )
        return TreatmentPathRecommendation.model_validate(data)
