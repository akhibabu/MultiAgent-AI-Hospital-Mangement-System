"""Diagnosis Agent — Step 3: Disease Probability Scoring."""

from __future__ import annotations

from typing import List
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.diagnosis.knowledge_base import ConditionKnowledgeBase
from app.ai.diagnosis.models import DifferentialDiagnosis, DiseaseProbability
from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.repositories.patient_context_repository import PatientClinicalContext


class _DiseaseProbabilityList(BaseModel):
    items: List[DiseaseProbability] = Field(default_factory=list)


class DiseaseProbabilityScorer(OrchestratorCallMixin):
    """
    Converts differential-diagnosis confidence into calibrated probability
    scores via the AI Orchestrator (`diagnosis` agent,
    `disease_probability_scoring` task). `ConditionKnowledgeBase` is kept
    as grounding data (risk-category mapping) fed into the prompt context.
    """

    def __init__(self, knowledge_base: ConditionKnowledgeBase | None = None) -> None:
        self._kb = knowledge_base or ConditionKnowledgeBase()

    def score(
        self,
        context: PatientClinicalContext,
        differentials: List[DifferentialDiagnosis],
    ) -> List[DiseaseProbability]:
        if not differentials:
            return []
        data = self._call(
            agent="diagnosis",
            task="disease_probability_scoring",
            patient_id=UUID(context.patient_id),
            response_model=_DiseaseProbabilityList,
            extra_vars={
                "differentials": [d.model_dump(mode="json") for d in differentials],
            },
        )
        scores = _DiseaseProbabilityList.model_validate(data).items
        scores.sort(key=lambda s: s.probability_pct, reverse=True)
        return scores
