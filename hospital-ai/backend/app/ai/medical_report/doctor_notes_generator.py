"""Medical Report Agent — Stage 2: Doctor Notes Generation (SOAP)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.ai.medical_report.models import DoctorNotes
from app.repositories.patient_context_repository import PatientClinicalContext


class DoctorNotesGenerator:
    def generate(
        self,
        context: PatientClinicalContext,
        diagnosis_row: Optional[Dict[str, Any]],
    ) -> DoctorNotes:
        symptom_analysis = (diagnosis_row or {}).get("symptom_analysis_json") or {}
        narrative = symptom_analysis.get("narrative") or ""
        symptoms_text = ", ".join(context.symptoms) or "No symptoms recorded"
        subjective = (
            f"Patient reports: {symptoms_text}. {narrative}".strip()
            or "No subjective complaints documented."
        )

        vitals_text = "; ".join(
            f"{v.get('name')}: {v.get('value')} {v.get('unit') or ''}".strip()
            for v in context.vitals
            if isinstance(v, dict) and v.get("name")
        )
        labs_text = "; ".join(
            f"{lab.get('name')}: {lab.get('value')} {lab.get('unit') or ''}".strip()
            for lab in context.lab_values
            if isinstance(lab, dict) and lab.get("name")
        )
        objective = (
            f"Vitals — {vitals_text or 'not recorded'}. Labs — {labs_text or 'not recorded'}."
        )

        differentials = (diagnosis_row or {}).get("differential_diagnoses_json") or []
        severity = ((diagnosis_row or {}).get("severity_assessment_json") or {}).get("level")
        top_conditions = ", ".join(
            d.get("condition") for d in differentials[:3] if isinstance(d, dict) and d.get("condition")
        )
        assessment = (
            f"Differential diagnosis: {top_conditions or 'not yet established'}. "
            f"Severity: {severity or 'not yet assessed'}."
        )

        treatment_path = (diagnosis_row or {}).get("treatment_path_json") or {}
        specialists = ", ".join(treatment_path.get("recommended_specialists") or [])
        tests = ", ".join(treatment_path.get("diagnostic_tests") or [])
        plan = (
            f"Recommended referral: {specialists or 'General Physician'}. "
            f"Recommended diagnostic tests: {tests or 'none specified'}. "
            f"Urgency: {treatment_path.get('urgency') or 'Routine'}."
        )

        cds = (diagnosis_row or {}).get("clinical_decision_support_json") or {}
        clinical_notes = cds.get("clinical_notes") or []
        clinical_reasoning = (
            " ".join(clinical_notes)
            or "Clinical reasoning pending — no Clinical Decision Support report available yet."
        )

        return DoctorNotes(
            subjective=subjective,
            objective=objective,
            assessment=assessment,
            plan=plan,
            clinical_reasoning=clinical_reasoning,
        )
