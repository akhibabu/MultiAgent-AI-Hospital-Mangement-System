"""Diagnosis Agent — Step 6: Clinical Decision Support Report."""

from __future__ import annotations

from typing import List

from app.ai.diagnosis.models import (
    ClinicalDecisionSupport,
    DifferentialDiagnosis,
    DiseaseProbability,
    SeverityAssessment,
    SymptomAnalysis,
    TreatmentPathRecommendation,
    DIAGNOSIS_DISCLAIMER,
)
from app.repositories.patient_context_repository import PatientClinicalContext


class ClinicalDecisionSupportGenerator:
    """Assembles the final clinician-facing decision-support report."""

    def generate(
        self,
        context: PatientClinicalContext,
        symptom_analysis: SymptomAnalysis,
        differentials: List[DifferentialDiagnosis],
        probabilities: List[DiseaseProbability],
        severity: SeverityAssessment,
        treatment_path: TreatmentPathRecommendation,
    ) -> ClinicalDecisionSupport:
        possible_diagnoses = [p.condition for p in probabilities[:5]]

        supporting_evidence: List[str] = []
        for diff in differentials[:5]:
            bits = diff.supporting_symptoms + diff.supporting_labs + diff.supporting_history
            if bits:
                supporting_evidence.append(f"{diff.condition}: {', '.join(bits[:4])}")

        clinical_notes = [symptom_analysis.narrative] if symptom_analysis.narrative else []
        clinical_notes.append(severity.explanation)
        if context.validation_warnings:
            clinical_notes.extend(context.validation_warnings)

        return ClinicalDecisionSupport(
            possible_diagnoses=possible_diagnoses,
            supporting_evidence=supporting_evidence,
            suggested_tests=treatment_path.diagnostic_tests,
            risk_factors=context.risk_factors,
            relevant_history=context.previous_diagnoses or context.conditions,
            clinical_notes=[c for c in clinical_notes if c],
            disclaimer=DIAGNOSIS_DISCLAIMER,
        )

    @staticmethod
    def build_summary(report_condition_count: int, top_condition: str | None, severity_level: str) -> str:
        if not top_condition:
            return (
                "Insufficient recognized clinical data to generate a differential "
                "diagnosis. Recommend completing further Intake stages or direct "
                "clinical evaluation."
            )
        return (
            f"Diagnosis Agent identified {report_condition_count} candidate condition(s), "
            f"led by {top_condition}. Estimated severity: {severity_level}. "
            "Clinical decision-support output only — a physician must confirm."
        )
