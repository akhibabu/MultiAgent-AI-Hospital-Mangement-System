"""Medical Report Agent — Stage 3: Discharge Summary."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.ai.medical_report.models import DischargeSummary
from app.repositories.patient_context_repository import PatientClinicalContext

_CONDITION_TEXT_BY_SEVERITY: Dict[str, str] = {
    "Critical": "Critical — transferred/continuing under close inpatient monitoring",
    "High": "Guarded — improving but requires close follow-up",
    "Moderate": "Stable, improving",
    "Low": "Stable",
    "Very Low": "Stable, no acute concerns",
}


class DischargeSummaryGenerator:
    def generate(
        self,
        context: PatientClinicalContext,
        diagnosis_row: Optional[Dict[str, Any]],
        prescription_row: Optional[Dict[str, Any]],
    ) -> DischargeSummary:
        admission_reason = (diagnosis_row or {}).get("chief_complaint") or (
            context.symptoms[0] if context.symptoms else "Not documented"
        )

        severity = ((diagnosis_row or {}).get("severity_assessment_json") or {}).get("level")
        treatment_path = (diagnosis_row or {}).get("treatment_path_json") or {}
        specialists = treatment_path.get("recommended_specialists") or []
        hospital_course = (
            f"Patient presented with {admission_reason}. Diagnostic workup and clinical decision "
            f"support assessed severity as {severity or 'not yet determined'}. "
            f"Referred to: {', '.join(specialists) or 'General Physician'}. "
            f"{(diagnosis_row or {}).get('summary') or ''}"
        ).strip()

        treatment_plan = (prescription_row or {}).get("treatment_plan_json") or {}
        medications: List[str] = treatment_plan.get("medication_plan") or [
            m.get("name") if isinstance(m, dict) else str(m) for m in context.medications
        ]

        condition_on_discharge = _CONDITION_TEXT_BY_SEVERITY.get(
            severity or "", "Condition on discharge pending physician assessment"
        )

        follow_up = treatment_plan.get("follow_up_interval") or "Follow up with primary care in 2-4 weeks."
        emergency_instructions = treatment_plan.get("emergency_advice") or (
            "Seek immediate emergency care for worsening symptoms, chest pain, severe shortness "
            "of breath, or any signs of a severe allergic reaction."
        )

        return DischargeSummary(
            admission_reason=str(admission_reason),
            hospital_course=hospital_course or "Hospital course not yet documented.",
            procedures=list(context.procedures) or ["No procedures on record."],
            medications=[m for m in medications if m] or ["No medications on record."],
            condition_on_discharge=condition_on_discharge,
            follow_up=follow_up,
            emergency_instructions=emergency_instructions,
        )
