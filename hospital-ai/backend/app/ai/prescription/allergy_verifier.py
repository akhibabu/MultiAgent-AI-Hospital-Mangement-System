"""
Prescription Agent — Stage 3: Allergy Verification.

Compares patient allergies against drug ingredients, drug classes, and
known cross-reactive classes. Every result explains WHY it is safe, a
warning, or contraindicated.
"""

from __future__ import annotations

from typing import List

from app.ai.prescription.knowledge_base import DrugKnowledgeBase
from app.ai.prescription.models import AllergyCheckItem


class AllergyVerifier:
    """Rule-based allergy / cross-reactivity screening."""

    def __init__(self, knowledge_base: DrugKnowledgeBase) -> None:
        self._kb = knowledge_base

    def verify(
        self,
        patient_allergies: List[str],
        suggested_drugs: List[str],
    ) -> List[AllergyCheckItem]:
        allergies = [a.strip().lower() for a in patient_allergies if a and a.strip()]
        results: List[AllergyCheckItem] = []

        for drug_name in dict.fromkeys(suggested_drugs):
            profile = self._kb.get(drug_name)
            if not profile:
                results.append(
                    AllergyCheckItem(
                        medication_name=drug_name,
                        status="Safe",
                        reason="No allergy data on record for this medication in the knowledge base.",
                    )
                )
                continue

            direct_hit = next(
                (
                    a
                    for a in allergies
                    if a in [c.lower() for c in profile.allergy_classes] or profile.name.lower() == a
                ),
                None,
            )
            if direct_hit:
                results.append(
                    AllergyCheckItem(
                        medication_name=drug_name,
                        status="Contraindicated",
                        reason=(
                            f"Patient has a documented allergy to '{direct_hit}', which directly "
                            f"matches {profile.name} ({profile.drug_class})."
                        ),
                        cross_reactivity=list(profile.cross_reactive_allergy_classes),
                    )
                )
                continue

            cross_hit = next(
                (
                    a
                    for a in allergies
                    if a in [c.lower() for c in profile.cross_reactive_allergy_classes]
                ),
                None,
            )
            if cross_hit:
                results.append(
                    AllergyCheckItem(
                        medication_name=drug_name,
                        status="Warning",
                        reason=(
                            f"Patient allergy to '{cross_hit}' has documented cross-reactivity "
                            f"potential with {profile.name} ({profile.drug_class}). Use with caution."
                        ),
                        cross_reactivity=list(profile.cross_reactive_allergy_classes),
                    )
                )
                continue

            results.append(
                AllergyCheckItem(
                    medication_name=drug_name,
                    status="Safe",
                    reason=(
                        f"No match found between patient allergies and {profile.name}'s allergy "
                        "classes or known cross-reactive classes."
                    ),
                )
            )

        return results
