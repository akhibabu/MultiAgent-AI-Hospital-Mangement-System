"""
Prescription Agent — Stage 1: Medication Selection.

Recommends medications supported by Diagnosis Agent output, Research Agent
evidence, clinical guidelines, and patient history. Never a final
prescription — always subject to physician review.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.ai.prescription.knowledge_base import DrugKnowledgeBase
from app.ai.prescription.models import MedicationRecommendation
from app.repositories.patient_context_repository import PatientClinicalContext

_MAX_DRUGS_PER_CONDITION = 2


class MedicationSelectionStrategy(ABC):
    @abstractmethod
    def select(
        self,
        context: PatientClinicalContext,
        target_conditions: List[str],
        research_recommendations: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[MedicationRecommendation]:
        raise NotImplementedError


class RuleBasedMedicationSelector(MedicationSelectionStrategy):
    """Matches target conditions against the rule-based drug knowledge base."""

    def __init__(self, knowledge_base: DrugKnowledgeBase) -> None:
        self._kb = knowledge_base

    def select(
        self,
        context: PatientClinicalContext,
        target_conditions: List[str],
        research_recommendations: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[MedicationRecommendation]:
        research_recommendations = research_recommendations or {}
        recommendations: List[MedicationRecommendation] = []

        for condition in target_conditions:
            profiles = self._kb.drugs_for_condition(condition)[:_MAX_DRUGS_PER_CONDITION]
            research = research_recommendations.get(condition) or {}
            evidence_boost = float(research.get("confidence_score") or 0.0)
            literature = research.get("supporting_literature") or []
            guidelines = research.get("clinical_guidelines") or []

            for profile in profiles:
                confidence = profile.confidence
                if evidence_boost:
                    confidence = round((confidence + evidence_boost) / 2, 4)

                evidence_source = profile.evidence_source
                if literature:
                    evidence_source = f"{profile.evidence_source}; {literature[0]}"

                clinical_guideline = profile.clinical_guideline
                if guidelines:
                    clinical_guideline = f"{profile.clinical_guideline}; {guidelines[0]}"

                recommendations.append(
                    MedicationRecommendation(
                        condition=condition,
                        medication_name=profile.name,
                        drug_class=profile.drug_class,
                        purpose=profile.purpose,
                        evidence_source=evidence_source,
                        clinical_guideline=clinical_guideline,
                        confidence=confidence,
                        alternative_drugs=list(profile.alternative_drugs),
                        expected_outcome=profile.expected_outcome,
                    )
                )

        return recommendations
