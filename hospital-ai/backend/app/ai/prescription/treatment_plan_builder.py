"""
Prescription Agent — Stage 5: Treatment Plan Creation.

Synthesizes the medication plan, lifestyle advice, monitoring plan,
recommended labs/imaging/specialists, follow-up interval, and emergency
advice from all prior stages plus the Diagnosis Agent's treatment path.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.ai.prescription.knowledge_base import DrugKnowledgeBase
from app.ai.prescription.models import (
    AllergyCheckItem,
    DosageRecommendation,
    MedicationRecommendation,
    TreatmentPlan,
)

_LIFESTYLE_ADVICE: Dict[str, List[str]] = {
    "Type 2 Diabetes Mellitus": [
        "Follow a low-glycemic-index, carbohydrate-controlled diet.",
        "Aim for at least 150 minutes/week of moderate aerobic activity.",
        "Monitor blood glucose as directed and maintain a glucose log.",
    ],
    "Hypertension": [
        "Reduce sodium intake to under 2,300 mg/day (ideally under 1,500 mg/day).",
        "Engage in regular aerobic exercise and maintain a healthy weight.",
        "Limit alcohol intake and avoid tobacco use.",
    ],
    "Coronary Artery Disease": [
        "Adopt a heart-healthy (e.g. Mediterranean-style) diet low in saturated fat.",
        "Engage in physician-approved cardiac rehabilitation / graded exercise.",
        "Strict tobacco cessation if applicable.",
    ],
    "Asthma / Reactive Airway Disease": [
        "Identify and avoid personal asthma triggers (allergens, smoke, cold air).",
        "Use a written asthma action plan and rescue inhaler as directed.",
    ],
    "Pneumonia / Respiratory Infection": [
        "Rest, maintain hydration, and complete the full antibiotic course if prescribed.",
        "Monitor for worsening breathing difficulty and seek care promptly if it occurs.",
    ],
    "Chronic Kidney Disease": [
        "Follow a renal-appropriate diet (protein, sodium, potassium as advised).",
        "Avoid nephrotoxic medications (e.g. long-term NSAID use) where possible.",
    ],
    "Urinary Tract Infection": [
        "Increase fluid intake and maintain good perineal hygiene.",
        "Complete the full prescribed antibiotic course even if symptoms improve.",
    ],
    "Anemia": [
        "Include iron-rich foods (leafy greens, legumes, lean meats) in the diet.",
        "Pair iron intake with vitamin C sources to improve absorption; avoid tea/coffee near iron doses.",
    ],
    "Thyroid Disorder": [
        "Take thyroid medication consistently, on an empty stomach, at the same time daily.",
        "Attend scheduled follow-up labs to titrate dosing.",
    ],
    "Gastritis / Peptic Ulcer Disease": [
        "Avoid NSAIDs, alcohol, and smoking, which can worsen mucosal irritation.",
        "Eat smaller, more frequent meals and avoid known trigger foods.",
    ],
    "Migraine / Neurological Headache Disorder": [
        "Maintain a headache diary to identify triggers (sleep, stress, diet, hormonal).",
        "Maintain regular sleep and meal schedules; stay well hydrated.",
    ],
    "Sepsis / Systemic Infection": [
        "Requires close inpatient monitoring — not appropriate for outpatient self-management alone.",
    ],
}

_DEFAULT_EMERGENCY_ADVICE = (
    "Seek immediate emergency care for chest pain, severe shortness of breath, signs of a severe "
    "allergic reaction (swelling of the face/throat, hives, difficulty breathing or swallowing), "
    "fainting, confusion, or rapidly worsening symptoms."
)

_FOLLOW_UP_BY_SEVERITY: Dict[str, str] = {
    "Critical": "24-48 hours (urgent follow-up)",
    "High": "3-5 days",
    "Moderate": "1-2 weeks",
    "Low": "4-6 weeks",
    "Very Low": "6-8 weeks (routine)",
}


class TreatmentPlanBuilder:
    """Assembles the holistic treatment plan for clinician review."""

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
    ) -> TreatmentPlan:
        contraindicated = {a.medication_name for a in allergy_checks if a.status == "Contraindicated"}
        dosage_by_drug = {d.medication_name: d for d in dosages}

        medication_plan: List[str] = []
        monitoring: List[str] = []
        for med in medications:
            if med.medication_name in contraindicated:
                medication_plan.append(
                    f"{med.medication_name} — EXCLUDED (allergy conflict). Consider alternative: "
                    f"{', '.join(med.alternative_drugs) or 'physician to determine'}."
                )
                continue
            dosage = dosage_by_drug.get(med.medication_name)
            dose_text = f" — starting dose {dosage.starting_dose}" if dosage and dosage.starting_dose else ""
            medication_plan.append(f"{med.medication_name} ({med.drug_class}) for {med.condition}{dose_text}.")

            profile = self._kb.get(med.medication_name)
            if profile:
                monitoring.extend(profile.monitoring)

        lifestyle: List[str] = []
        for condition in target_conditions:
            lifestyle.extend(_LIFESTYLE_ADVICE.get(condition, []))
        lifestyle = list(dict.fromkeys(lifestyle)) or [
            "No condition-specific lifestyle guidance available — advise routine healthy-living counseling."
        ]

        monitoring = list(dict.fromkeys(monitoring)) or [
            "Routine clinical follow-up recommended to assess treatment response."
        ]

        follow_up = _FOLLOW_UP_BY_SEVERITY.get(severity_level or "", "2-4 weeks (routine)")

        return TreatmentPlan(
            medication_plan=medication_plan
            or ["No medications recommended — clinical evaluation and monitoring advised."],
            lifestyle_advice=lifestyle,
            monitoring_plan=monitoring,
            recommended_lab_tests=list(dict.fromkeys(diagnosis_tests or [])),
            recommended_imaging=list(dict.fromkeys(diagnosis_imaging or [])),
            recommended_specialists=list(dict.fromkeys(diagnosis_specialists or [])),
            follow_up_interval=follow_up,
            emergency_advice=_DEFAULT_EMERGENCY_ADVICE,
        )
