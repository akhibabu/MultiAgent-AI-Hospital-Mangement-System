"""Medical Report Agent — Stage 4: Referral Letter Creation."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from app.ai.medical_report.models import ReferralLetter
from app.repositories.patient_context_repository import PatientClinicalContext


class ReferralLetterGenerator:
    def generate(
        self,
        context: PatientClinicalContext,
        diagnosis_row: Optional[Dict[str, Any]],
        *,
        receiving_specialist: Optional[str] = None,
    ) -> ReferralLetter:
        treatment_path = (diagnosis_row or {}).get("treatment_path_json") or {}
        specialists = treatment_path.get("recommended_specialists") or []
        specialist = receiving_specialist or (specialists[0] if specialists else "General Physician")

        probs = (diagnosis_row or {}).get("probability_scores_json") or []
        top_condition = probs[0].get("condition") if probs and isinstance(probs[0], dict) else None
        chief_complaint = (diagnosis_row or {}).get("chief_complaint") or (
            context.symptoms[0] if context.symptoms else "unspecified complaint"
        )
        reason = (
            f"Referral for further evaluation of {top_condition or chief_complaint}."
        )

        history = context.medical_history_summary or (
            f"Relevant history: {', '.join(context.previous_diagnoses)}"
            if context.previous_diagnoses
            else "No significant medical history on record."
        )

        cds = (diagnosis_row or {}).get("clinical_decision_support_json") or {}
        important_findings: List[str] = list(cds.get("supporting_evidence") or [])
        if not important_findings and probs:
            important_findings = [
                f"{p.get('condition')}: {round(float(p.get('probability_pct') or 0))}% probability"
                for p in probs[:3]
                if isinstance(p, dict)
            ]

        investigations = list(treatment_path.get("diagnostic_tests") or []) + list(
            treatment_path.get("imaging") or []
        )
        requested_evaluation = (
            f"Please evaluate and advise on further management for {top_condition or chief_complaint}. "
            "Kindly share your findings and recommendations with our team."
        )

        letter_body = (
            f"Date: {date.today().isoformat()}\n\n"
            f"To: {specialist}\n\n"
            f"Re: {context.patient_name}"
            f"{f' ({context.patient_number})' if context.patient_number else ''}\n\n"
            f"Dear Colleague,\n\n"
            f"I am referring {context.patient_name} for your evaluation. {reason}\n\n"
            f"Relevant history: {history}\n\n"
            f"Key findings: {'; '.join(important_findings) or 'See attached clinical summary.'}\n\n"
            f"Investigations to date / recommended: {', '.join(investigations) or 'None recorded.'}\n\n"
            f"{requested_evaluation}\n\n"
            "Please do not hesitate to contact our team with any questions.\n\n"
            "Sincerely,\nHospital AI Care Team\n\n"
            "(Clinical decision support only — a licensed physician has reviewed or will "
            "review this referral before it is sent.)"
        )

        return ReferralLetter(
            receiving_specialist=specialist,
            reason=reason,
            history=history,
            important_findings=important_findings or ["No key findings on record yet."],
            investigations=investigations or ["None recorded."],
            requested_evaluation=requested_evaluation,
            letter_body=letter_body,
        )
