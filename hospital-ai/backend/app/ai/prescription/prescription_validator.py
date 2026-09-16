"""
Prescription Agent — Stage 6: Prescription Validation.

Final safety gate before physician review, via the AI Orchestrator
(`prescription` agent, `validation` task). Checks drug interactions,
duplicate drugs, contraindications, maximum dose flags, and allergy
conflicts, then produces a confidence score, warnings, and approval
status.

Approval status NEVER means "dispense" — a licensed physician must
always review and sign off.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.ai.prescription.models import (
    AllergyCheckItem,
    DosageRecommendation,
    DrugInteraction,
    MedicationRecommendation,
    PrescriptionValidation,
)


class PrescriptionValidator(OrchestratorCallMixin):
    """Aggregates all prior stage findings into a final validation report."""

    def validate(
        self,
        *,
        current_drugs: List[str],
        medications: List[MedicationRecommendation],
        interactions: List[DrugInteraction],
        allergy_checks: List[AllergyCheckItem],
        dosages: List[DosageRecommendation],
        patient_id: Optional[UUID] = None,
    ) -> PrescriptionValidation:
        if not medications:
            return PrescriptionValidation(
                approval_status="Requires Physician Review",
                confidence_score=0.0,
                notes=[
                    "No medications were recommended for the target conditions — "
                    "direct clinical evaluation is required."
                ],
            )
        data = self._call(
            agent="prescription",
            task="validation",
            patient_id=patient_id,
            response_model=PrescriptionValidation,
            extra_vars={
                "medications": current_drugs,
                "suggested_medications": [m.medication_name for m in medications],
                "interactions": [i.model_dump(mode="json") for i in interactions],
                "allergy_checks": [a.model_dump(mode="json") for a in allergy_checks],
                "dosages": [d.model_dump(mode="json") for d in dosages],
            },
        )
        return PrescriptionValidation.model_validate(data)
