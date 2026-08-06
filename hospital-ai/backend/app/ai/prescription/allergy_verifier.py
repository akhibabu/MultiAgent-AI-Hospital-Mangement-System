"""
Prescription Agent — Stage 3: Allergy Verification.

Compares patient allergies against drug ingredients, drug classes, and
known cross-reactive classes via the AI Orchestrator (`prescription`
agent, `allergy_verification` task). Every result explains WHY it is
safe, a warning, or contraindicated.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.ai.prescription.knowledge_base import DrugKnowledgeBase
from app.ai.prescription.models import AllergyCheckItem


class _AllergyCheckList(BaseModel):
    items: List[AllergyCheckItem] = Field(default_factory=list)


class AllergyVerifier(OrchestratorCallMixin):
    """
    LLM-backed allergy / cross-reactivity screening. `DrugKnowledgeBase`
    (allergy classes, cross-reactive classes per drug) remains available
    as grounding data.
    """

    def __init__(self, knowledge_base: DrugKnowledgeBase) -> None:
        self._kb = knowledge_base

    def verify(
        self,
        patient_allergies: List[str],
        suggested_drugs: List[str],
        *,
        patient_id: Optional[UUID] = None,
    ) -> List[AllergyCheckItem]:
        if not suggested_drugs:
            return []
        data = self._call(
            agent="prescription",
            task="allergy_verification",
            patient_id=patient_id,
            response_model=_AllergyCheckList,
            extra_vars={
                "allergies": patient_allergies,
                "suggested_medications": list(dict.fromkeys(suggested_drugs)),
            },
        )
        return _AllergyCheckList.model_validate(data).items
