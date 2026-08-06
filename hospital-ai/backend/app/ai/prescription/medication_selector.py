"""
Prescription Agent — Stage 1: Medication Selection.

Recommends medications supported by Diagnosis Agent output, Research Agent
evidence, clinical guidelines, and patient history — via the AI
Orchestrator (`prescription` agent, `medication_selection` task). Never a
final prescription — always subject to physician review.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.ai.prescription.knowledge_base import DrugKnowledgeBase
from app.ai.prescription.models import MedicationRecommendation
from app.repositories.patient_context_repository import PatientClinicalContext


class _MedicationRecommendationList(BaseModel):
    items: List[MedicationRecommendation] = Field(default_factory=list)


class MedicationSelectionStrategy(ABC):
    @abstractmethod
    def select(
        self,
        context: PatientClinicalContext,
        target_conditions: List[str],
        research_recommendations: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[MedicationRecommendation]:
        raise NotImplementedError


class LLMMedicationSelector(OrchestratorCallMixin, MedicationSelectionStrategy):
    """
    Delegates medication selection to the AI Orchestrator. The rule-based
    `DrugKnowledgeBase` (condition -> drug profiles) remains available as
    grounding data for other stages (dosage/interaction/allergy) but no
    longer makes this stage's recommendation itself.
    """

    def __init__(self, knowledge_base: DrugKnowledgeBase) -> None:
        self._kb = knowledge_base

    def select(
        self,
        context: PatientClinicalContext,
        target_conditions: List[str],
        research_recommendations: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[MedicationRecommendation]:
        if not target_conditions:
            return []
        data = self._call(
            agent="prescription",
            task="medication_selection",
            patient_id=UUID(context.patient_id),
            response_model=_MedicationRecommendationList,
            extra_vars={
                "target_conditions": target_conditions,
                "research_recommendations": research_recommendations or {},
            },
        )
        return _MedicationRecommendationList.model_validate(data).items
