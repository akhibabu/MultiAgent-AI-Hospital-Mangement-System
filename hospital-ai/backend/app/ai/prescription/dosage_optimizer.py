"""
Prescription Agent — Stage 4: Dosage Optimization.

Estimates dosage RANGES using age, weight, gender, kidney/liver function,
severity, and medical history via the AI Orchestrator (`prescription`
agent, `dosage_optimization` task). Never generates a final prescribed
dose — only starting / maintenance / maximum ranges plus adjustment
notes.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.ai.prescription.knowledge_base import DrugKnowledgeBase
from app.ai.prescription.models import DosageRecommendation
from app.repositories.patient_context_repository import PatientClinicalContext


class _DosageRecommendationList(BaseModel):
    items: List[DosageRecommendation] = Field(default_factory=list)


class DosageOptimizer(OrchestratorCallMixin):
    """
    LLM-backed dosage range estimation with safety adjustment notes.
    `DrugKnowledgeBase` (baseline dose ranges, renal/hepatic adjustment
    text) remains available as grounding data fed into the prompt.
    """

    def __init__(self, knowledge_base: DrugKnowledgeBase) -> None:
        self._kb = knowledge_base

    def optimize(
        self,
        context: PatientClinicalContext,
        suggested_drugs: List[str],
        severity_level: Optional[str] = None,
    ) -> List[DosageRecommendation]:
        if not suggested_drugs:
            return []
        data = self._call(
            agent="prescription",
            task="dosage_optimization",
            patient_id=UUID(context.patient_id),
            response_model=_DosageRecommendationList,
            extra_vars={
                "severity_level": severity_level,
                "suggested_medications": list(dict.fromkeys(suggested_drugs)),
            },
        )
        return _DosageRecommendationList.model_validate(data).items
