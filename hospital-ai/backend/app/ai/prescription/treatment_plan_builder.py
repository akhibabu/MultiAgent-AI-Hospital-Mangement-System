"""
Prescription Agent — Stage 5: Treatment Plan Creation.

Synthesizes the medication plan, lifestyle advice, monitoring plan,
recommended labs/imaging/specialists, follow-up interval, and emergency
advice from all prior stages plus the Diagnosis Agent's treatment path —
via the AI Orchestrator (`prescription` agent, `treatment_plan` task).
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.ai.prescription.knowledge_base import DrugKnowledgeBase
from app.ai.prescription.models import (
    AllergyCheckItem,
    DosageRecommendation,
    MedicationRecommendation,
    TreatmentPlan,
)


class TreatmentPlanBuilder(OrchestratorCallMixin):
    """
    Assembles the holistic treatment plan for clinician review via the
    AI Orchestrator. `DrugKnowledgeBase.monitoring` profiles remain
    available as grounding data for the monitoring plan.
    """

    def __init__(self, knowledge_base: DrugKnowledgeBase) -> None:
        self._kb = knowledge_base

    def build(
        self,
        *,
        target_conditions: List[str],
        medications: List[MedicationRecommendation],
        allergy_checks: List[AllergyCheckItem],
        dosages: List[DosageRecommendation],
        severity_level: Optional[str] = None,
        diagnosis_specialists: Optional[List[str]] = None,
        diagnosis_tests: Optional[List[str]] = None,
        diagnosis_imaging: Optional[List[str]] = None,
        patient_id: Optional[UUID] = None,
    ) -> TreatmentPlan:
        data = self._call(
            agent="prescription",
            task="treatment_plan",
            patient_id=patient_id,
            response_model=TreatmentPlan,
            extra_vars={
                "target_conditions": target_conditions,
                "medications": [m.model_dump(mode="json") for m in medications],
                "allergy_checks": [a.model_dump(mode="json") for a in allergy_checks],
                "dosages": [d.model_dump(mode="json") for d in dosages],
                "severity_level": severity_level,
                "diagnosis_specialists": diagnosis_specialists or [],
                "diagnosis_tests": diagnosis_tests or [],
                "diagnosis_imaging": diagnosis_imaging or [],
            },
        )
        return TreatmentPlan.model_validate(data)
