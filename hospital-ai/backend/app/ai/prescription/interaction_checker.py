"""
Prescription Agent — Stage 2: Drug Interaction Check.

Analyzes current medications + suggested medications for known
interactions, severity, and contraindications via the AI Orchestrator
(`prescription` agent, `drug_interaction_check` task). Explains every
interaction found.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.ai.prescription.knowledge_base import DrugKnowledgeBase
from app.ai.prescription.models import DrugInteraction

_SEVERITY_RANK = {"Critical": 0, "Major": 1, "Moderate": 2, "Minor": 3}


class _DrugInteractionList(BaseModel):
    items: List[DrugInteraction] = Field(default_factory=list)


class DrugInteractionChecker(OrchestratorCallMixin):
    """
    Pairwise interaction analysis across current + suggested medications,
    via the AI Orchestrator. `DrugKnowledgeBase.DRUG_INTERACTIONS` stays
    available as grounding data for known interaction pairs.
    """

    def __init__(self, knowledge_base: DrugKnowledgeBase) -> None:
        self._kb = knowledge_base

    def check(
        self,
        current_drugs: List[str],
        suggested_drugs: List[str],
        *,
        patient_id: Optional[UUID] = None,
    ) -> List[DrugInteraction]:
        all_drugs = list(dict.fromkeys([d for d in (current_drugs + suggested_drugs) if d]))
        if len(all_drugs) < 2:
            return []
        data = self._call(
            agent="prescription",
            task="drug_interaction_check",
            patient_id=patient_id,
            response_model=_DrugInteractionList,
            extra_vars={
                "medications": current_drugs,
                "suggested_medications": suggested_drugs,
            },
        )
        interactions = _DrugInteractionList.model_validate(data).items
        interactions.sort(key=lambda i: _SEVERITY_RANK.get(i.interaction_level, 4))
        return interactions
