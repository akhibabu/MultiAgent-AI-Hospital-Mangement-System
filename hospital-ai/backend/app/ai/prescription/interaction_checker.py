"""
Prescription Agent — Stage 2: Drug Interaction Check.

Analyzes current medications + suggested medications for known interactions,
severity, and contraindications. Explains every interaction found.
"""

from __future__ import annotations

from itertools import combinations
from typing import List

from app.ai.prescription.knowledge_base import DrugKnowledgeBase
from app.ai.prescription.models import DrugInteraction


class DrugInteractionChecker:
    """Pairwise interaction lookup across current + suggested medications."""

    def __init__(self, knowledge_base: DrugKnowledgeBase) -> None:
        self._kb = knowledge_base

    def check(
        self,
        current_drugs: List[str],
        suggested_drugs: List[str],
    ) -> List[DrugInteraction]:
        all_drugs = list(dict.fromkeys([d for d in (current_drugs + suggested_drugs) if d]))
        interactions: List[DrugInteraction] = []

        for drug_a, drug_b in combinations(all_drugs, 2):
            hit = self._kb.interaction_between(drug_a, drug_b)
            if not hit:
                continue
            level, explanation, recommendation = hit
            interactions.append(
                DrugInteraction(
                    drug_a=drug_a,
                    drug_b=drug_b,
                    interaction_level=level,
                    explanation=explanation,
                    recommendation=recommendation,
                )
            )

        # Highest severity first for clinician attention
        severity_rank = {"Critical": 0, "Major": 1, "Moderate": 2, "Minor": 3}
        interactions.sort(key=lambda i: severity_rank.get(i.interaction_level, 4))
        return interactions
