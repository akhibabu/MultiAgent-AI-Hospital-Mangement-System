"""
Medical Report Agent — Stage 6: Patient Report Generation.

Plain-language, patient-friendly report. No medical jargon where avoidable.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.ai.medical_report.models import FAQItem, PatientReport
from app.repositories.patient_context_repository import PatientClinicalContext

_DIET_KEYWORDS = ("diet", "food", "sodium", "salt", "iron-rich", "meal", "hydrat", "alcohol", "caffeine")
_EXERCISE_KEYWORDS = ("exercise", "aerobic", "activity", "physical", "rehabilitation")


class PatientReportGenerator:
    def generate(
        self,
        context: PatientClinicalContext,
        diagnosis_row: Optional[Dict[str, Any]],
        prescription_row: Optional[Dict[str, Any]],
    ) -> PatientReport:
        probs = (diagnosis_row or {}).get("probability_scores_json") or []
        top_condition = probs[0].get("condition") if probs and isinstance(probs[0], dict) else None
        diagnosis_summary = (
            f"Based on your symptoms, vitals, and test results, our care team believes you may "
            f"have {top_condition}. This has not been confirmed with full certainty — your "
            "doctor will discuss this with you and may recommend more tests."
            if top_condition
            else "Your care team is still reviewing your results. Your doctor will discuss the "
            "findings with you at your next visit."
        )

        treatment_plan = (prescription_row or {}).get("treatment_plan_json") or {}
        treatment_summary = (
            "Your care plan may include medicine, lifestyle changes, and follow-up visits. "
            "Please review the medicine list below and ask your doctor or pharmacist if you "
            "have any questions."
            if treatment_plan
            else "Your treatment plan has not been finalized yet. Please follow up with your doctor."
        )

        current_medicines = [
            m for m in (treatment_plan.get("medication_plan") or []) if m
        ] or ["No new medicines have been recommended yet — please check with your doctor."]

        lifestyle_items = treatment_plan.get("lifestyle_advice") or []
        diet: List[str] = []
        exercise: List[str] = []
        lifestyle: List[str] = []
        for item in lifestyle_items:
            lower = item.lower()
            if any(k in lower for k in _DIET_KEYWORDS):
                diet.append(item)
            elif any(k in lower for k in _EXERCISE_KEYWORDS):
                exercise.append(item)
            else:
                lifestyle.append(item)

        follow_up = treatment_plan.get("follow_up_interval") or (
            "Please schedule a follow-up visit with your doctor."
        )
        emergency_contact_instructions = treatment_plan.get("emergency_advice") or (
            "If you feel much worse, have trouble breathing, chest pain, or a severe allergic "
            "reaction, go to the nearest emergency room or call emergency services right away."
        )

        faq = [
            FAQItem(
                question="What is my diagnosis?",
                answer=(
                    f"Our team believes you may have {top_condition}, but your doctor will "
                    "confirm this with you."
                    if top_condition
                    else "Your care team is still reviewing your results."
                ),
            ),
            FAQItem(
                question="Do I need to take any medicine?",
                answer=(
                    "Yes — see the 'Current Medicines' section above. Take them exactly as "
                    "instructed by your doctor."
                    if treatment_plan.get("medication_plan")
                    else "No new medicine has been recommended yet."
                ),
            ),
            FAQItem(
                question="What if I miss a dose of my medicine?",
                answer=(
                    "Take it as soon as you remember, unless it is almost time for your next "
                    "dose. Never take a double dose. Contact your pharmacist or doctor if unsure."
                ),
            ),
            FAQItem(
                question="When should I go to the emergency room?",
                answer=emergency_contact_instructions,
            ),
            FAQItem(
                question="When is my next appointment?",
                answer=f"Your recommended follow-up is: {follow_up}",
            ),
        ]

        return PatientReport(
            diagnosis_summary=diagnosis_summary,
            treatment_summary=treatment_summary,
            current_medicines=current_medicines,
            lifestyle_advice=lifestyle or ["Maintain a healthy lifestyle and attend regular check-ups."],
            diet=diet or ["No specific diet advice recorded — ask your doctor for guidance."],
            exercise=exercise or ["Light regular activity is generally recommended — confirm with your doctor."],
            follow_up=follow_up,
            emergency_contact_instructions=emergency_contact_instructions,
            faq=faq,
        )
