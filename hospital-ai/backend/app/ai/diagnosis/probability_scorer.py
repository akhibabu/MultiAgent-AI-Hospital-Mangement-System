"""Diagnosis Agent — Step 3: Disease Probability Scoring."""

from __future__ import annotations

from typing import List

from app.ai.diagnosis.knowledge_base import ConditionKnowledgeBase
from app.ai.diagnosis.models import DifferentialDiagnosis, DiseaseProbability
from app.repositories.patient_context_repository import PatientClinicalContext


class DiseaseProbabilityScorer:
    """Converts differential-diagnosis confidence into calibrated probabilities."""

    def __init__(self, knowledge_base: ConditionKnowledgeBase | None = None) -> None:
        self._kb = knowledge_base or ConditionKnowledgeBase()

    def score(
        self,
        context: PatientClinicalContext,
        differentials: List[DifferentialDiagnosis],
    ) -> List[DiseaseProbability]:
        risk_categories = {
            str(c.get("name")): c
            for c in context.risk_categories
            if isinstance(c, dict) and c.get("name")
        }

        scores: List[DiseaseProbability] = []
        for diff in differentials:
            profile = self._kb.get(diff.condition)
            risk_contribution = 0.0
            risk_category_name = profile.risk_category if profile else None
            if risk_category_name and risk_category_name in risk_categories:
                cat = risk_categories[risk_category_name]
                risk_contribution = round(float(cat.get("score") or 0.0) / 100.0, 3)
            elif context.risk_overall_score is not None:
                risk_contribution = round(float(context.risk_overall_score) / 200.0, 3)

            evidence_used = (
                diff.supporting_symptoms + diff.supporting_labs + diff.supporting_history
            )

            probability = diff.confidence * 0.75 + risk_contribution * 0.25
            probability_pct = round(min(99.0, max(1.0, probability * 100)), 1)

            confidence = round(
                min(0.97, diff.confidence * 0.8 + (0.2 if evidence_used else 0.0)), 3
            )

            scores.append(
                DiseaseProbability(
                    condition=diff.condition,
                    probability_pct=probability_pct,
                    confidence=confidence,
                    evidence_used=evidence_used,
                    risk_contribution=risk_contribution,
                    risk_category=risk_category_name,
                )
            )

        scores.sort(key=lambda s: s.probability_pct, reverse=True)
        return scores
