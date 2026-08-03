"""
Prescription Agent — Stage 6: Prescription Validation.

Final safety gate before physician review. Checks drug interactions,
duplicate drugs, contraindications, maximum dose flags, and allergy
conflicts, then produces a confidence score, warnings, and approval status.

Approval status NEVER means "dispense" — a licensed physician must always
review and sign off.
"""

from __future__ import annotations

from typing import List

from app.ai.prescription.models import (
    AllergyCheckItem,
    DosageRecommendation,
    DrugInteraction,
    MedicationRecommendation,
    PrescriptionValidation,
)

_CRITICAL_INTERACTION_PENALTY = 0.35
_MAJOR_INTERACTION_PENALTY = 0.2
_MODERATE_INTERACTION_PENALTY = 0.08
_CONTRAINDICATION_PENALTY = 0.3
_WARNING_PENALTY = 0.1
_DUPLICATE_PENALTY = 0.1


class PrescriptionValidator:
    """Aggregates all prior stage findings into a final validation report."""

    def validate(
        self,
        *,
        current_drugs: List[str],
        medications: List[MedicationRecommendation],
        interactions: List[DrugInteraction],
        allergy_checks: List[AllergyCheckItem],
        dosages: List[DosageRecommendation],
    ) -> PrescriptionValidation:
        suggested_names = [m.medication_name for m in medications]
        current_lower = {d.lower() for d in current_drugs}

        duplicate_drugs = sorted(
            {name for name in suggested_names if name.lower() in current_lower}
        )

        contraindications_found = [
            a.medication_name for a in allergy_checks if a.status == "Contraindicated"
        ]
        allergy_conflicts = list(contraindications_found)

        drug_warnings = [
            f"{a.medication_name}: {a.reason}" for a in allergy_checks if a.status == "Warning"
        ]
        for interaction in interactions:
            if interaction.interaction_level in {"Major", "Critical"}:
                drug_warnings.append(
                    f"{interaction.drug_a} + {interaction.drug_b} "
                    f"({interaction.interaction_level}): {interaction.explanation}"
                )

        # This mock knowledge base does not model exact patient-administered doses, so
        # "max dose exceeded" is only flagged when the SAME drug is duplicated across
        # current medications and new suggestions — a real max-dose engine would compare
        # actual prescribed totals against `profile.maximum_dose`.
        max_dose_exceeded = list(duplicate_drugs)

        confidence = 0.92
        notes: List[str] = []

        critical_count = sum(1 for i in interactions if i.interaction_level == "Critical")
        major_count = sum(1 for i in interactions if i.interaction_level == "Major")
        moderate_count = sum(1 for i in interactions if i.interaction_level == "Moderate")

        confidence -= critical_count * _CRITICAL_INTERACTION_PENALTY
        confidence -= major_count * _MAJOR_INTERACTION_PENALTY
        confidence -= moderate_count * _MODERATE_INTERACTION_PENALTY
        confidence -= len(contraindications_found) * _CONTRAINDICATION_PENALTY
        confidence -= sum(1 for a in allergy_checks if a.status == "Warning") * _WARNING_PENALTY
        confidence -= len(duplicate_drugs) * _DUPLICATE_PENALTY
        confidence = round(max(0.0, min(1.0, confidence)), 4)

        if contraindications_found or critical_count:
            approval_status = "Rejected"
            notes.append(
                "One or more medications are contraindicated or involved in a critical "
                "interaction — this recommendation set requires substitution before use."
            )
        elif major_count or duplicate_drugs or any(
            a.status == "Warning" for a in allergy_checks
        ):
            approval_status = "Requires Physician Review"
            notes.append(
                "Major interaction, duplicate therapy, or allergy warning detected — "
                "physician review required before proceeding."
            )
        else:
            approval_status = "Approved"
            notes.append(
                "No blocking safety issues detected by the Prescription Agent. A licensed "
                "physician must still review and sign off before any medication is "
                "prescribed or dispensed."
            )

        if not medications:
            notes.append("No medications were recommended for the target conditions.")

        return PrescriptionValidation(
            duplicate_drugs=duplicate_drugs,
            contraindications_found=contraindications_found,
            max_dose_exceeded=max_dose_exceeded,
            allergy_conflicts=allergy_conflicts,
            drug_warnings=drug_warnings,
            confidence_score=confidence,
            approval_status=approval_status,
            notes=notes,
        )
