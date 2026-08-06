"""Diagnosis Agent — Step 6: Clinical Decision Support Report."""

from __future__ import annotations

from typing import List
from uuid import UUID

from app.ai.diagnosis.models import (
    ClinicalDecisionSupport,
    DIAGNOSIS_DISCLAIMER,
    DifferentialDiagnosis,
    DiseaseProbability,
    SeverityAssessment,
    SymptomAnalysis,
    TreatmentPathRecommendation,
)
from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.repositories.patient_context_repository import PatientClinicalContext


class ClinicalDecisionSupportGenerator(OrchestratorCallMixin):
    """
    Assembles the final clinician-facing decision-support report via the
    AI Orchestrator (`diagnosis` agent, `clinical_decision_support` task).
    """

    def generate(
        self,
        context: PatientClinicalContext,
        symptom_analysis: SymptomAnalysis,
        differentials: List[DifferentialDiagnosis],
        probabilities: List[DiseaseProbability],
        severity: SeverityAssessment,
        treatment_path: TreatmentPathRecommendation,
    ) -> ClinicalDecisionSupport:
        data = self._call(
            agent="diagnosis",
            task="clinical_decision_support",
            patient_id=UUID(context.patient_id),
            response_model=ClinicalDecisionSupport,
            extra_vars={
                "symptom_analysis": symptom_analysis.model_dump(mode="json"),
                "differentials": [d.model_dump(mode="json") for d in differentials[:5]],
                "probabilities": [p.model_dump(mode="json") for p in probabilities[:5]],
                "severity": severity.model_dump(mode="json"),
                "treatment_path": treatment_path.model_dump(mode="json"),
            },
        )
        cds = ClinicalDecisionSupport.model_validate(data)
        cds.disclaimer = DIAGNOSIS_DISCLAIMER
        return cds

    @staticmethod
    def build_summary(
        report_condition_count: int, top_condition: str | None, severity_level: str
    ) -> str:
        if not top_condition:
            return (
                "Insufficient recognized clinical data to generate a differential "
                "diagnosis. Recommend completing further Intake stages or direct "
                "clinical evaluation."
            )
        return (
            f"Diagnosis Agent (AI Orchestrator) identified {report_condition_count} "
            f"candidate condition(s), led by {top_condition}. Estimated severity: "
            f"{severity_level}. Clinical decision-support output only — a physician "
            "must confirm."
        )
