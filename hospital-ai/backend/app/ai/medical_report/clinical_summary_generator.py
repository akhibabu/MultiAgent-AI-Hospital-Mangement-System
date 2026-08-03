"""Medical Report Agent — Stage 1: Clinical Summary."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.ai.medical_report.models import ClinicalSummary
from app.repositories.patient_context_repository import PatientClinicalContext


class ClinicalSummaryGenerator:
    def generate(
        self,
        context: PatientClinicalContext,
        diagnosis_row: Optional[Dict[str, Any]],
    ) -> ClinicalSummary:
        age = f"{context.age_years}-year-old" if context.age_years is not None else "age not on record"
        gender = context.gender or "patient"
        patient_number_suffix = f" ({context.patient_number})" if context.patient_number else ""
        history_suffix = (
            f" with a history of {', '.join(context.conditions[:3])}" if context.conditions else ""
        )
        patient_overview = (
            f"{context.patient_name} is a {age} {gender.lower()}{patient_number_suffix}"
            f"{history_suffix}."
        )

        chief_complaint = (diagnosis_row or {}).get("chief_complaint") or (
            context.symptoms[0] if context.symptoms else "Not documented"
        )

        history = context.medical_history_summary or (
            f"Past conditions: {', '.join(context.previous_diagnoses)}"
            if context.previous_diagnoses
            else "No significant medical history on record."
        )

        diagnosis_summary = (diagnosis_row or {}).get("summary") or (
            "No Diagnosis Agent result on record for this patient."
        )

        severity = ((diagnosis_row or {}).get("severity_assessment_json") or {}).get("level")
        current_status = (
            f"Current severity assessment: {severity}."
            if severity
            else "Current clinical status not yet assessed by the Diagnosis Agent."
        )

        key_findings: List[str] = []
        probs = (diagnosis_row or {}).get("probability_scores_json") or []
        for p in probs[:3]:
            if isinstance(p, dict) and p.get("condition"):
                key_findings.append(
                    f"{p['condition']} (probability {round(float(p.get('probability_pct') or 0))}%)"
                )
        for vital in context.vitals[:3]:
            if isinstance(vital, dict) and vital.get("name"):
                key_findings.append(f"{vital['name']}: {vital.get('value')} {vital.get('unit') or ''}".strip())

        return ClinicalSummary(
            patient_overview=patient_overview,
            chief_complaint=str(chief_complaint),
            history=history,
            diagnosis_summary=diagnosis_summary,
            current_status=current_status,
            key_findings=key_findings or ["No key findings on record yet."],
        )
