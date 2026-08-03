"""
Prescription Agent — Stage 4: Dosage Optimization.

Estimates dosage RANGES using age, weight, gender, kidney/liver function,
severity, and medical history. Never generates a final prescribed dose —
only starting / maintenance / maximum ranges plus adjustment notes.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.ai.prescription.knowledge_base import DrugKnowledgeBase
from app.ai.prescription.models import DosageRecommendation
from app.repositories.patient_context_repository import PatientClinicalContext

_RENAL_KEYWORDS = ("creatinine", "egfr")
_HEPATIC_KEYWORDS = ("alt", "ast", "sgpt", "sgot", "liver function")
_WEIGHT_KEYWORDS = ("weight",)


def _first_number(text: str) -> Optional[float]:
    match = re.search(r"-?\d+(?:\.\d+)?", text or "")
    return float(match.group()) if match else None


def _find_lab(labs: List[Dict[str, Any]], keywords: tuple) -> Optional[Dict[str, Any]]:
    for lab in labs:
        name = str(lab.get("name") or "").lower()
        if any(k in name for k in keywords):
            return lab
    return None


def _find_vital(vitals: List[Dict[str, Any]], keywords: tuple) -> Optional[Dict[str, Any]]:
    for vital in vitals:
        name = str(vital.get("name") or "").lower()
        if any(k in name for k in keywords):
            return vital
    return None


class DosageOptimizer:
    """Rule-based dosage range estimation with safety adjustment notes."""

    def __init__(self, knowledge_base: DrugKnowledgeBase) -> None:
        self._kb = knowledge_base

    def optimize(
        self,
        context: PatientClinicalContext,
        suggested_drugs: List[str],
        severity_level: Optional[str] = None,
    ) -> List[DosageRecommendation]:
        renal_lab = _find_lab(context.lab_values, _RENAL_KEYWORDS)
        hepatic_lab = _find_lab(context.lab_values, _HEPATIC_KEYWORDS)
        weight_vital = _find_vital(context.vitals, _WEIGHT_KEYWORDS)

        renal_value = _first_number(str(renal_lab.get("value"))) if renal_lab else None
        hepatic_value = _first_number(str(hepatic_lab.get("value"))) if hepatic_lab else None

        is_ckd_history = any(
            "kidney" in c.lower() for c in (context.conditions + context.previous_diagnoses)
        )
        renal_impaired = is_ckd_history or (renal_value is not None and renal_value > 1.3)

        is_liver_history = any(
            "liver" in c.lower() or "hepat" in c.lower()
            for c in (context.conditions + context.previous_diagnoses)
        )
        hepatic_impaired = is_liver_history or (hepatic_value is not None and hepatic_value > 55)

        recommendations: List[DosageRecommendation] = []
        for drug_name in dict.fromkeys(suggested_drugs):
            profile = self._kb.get(drug_name)
            if not profile:
                recommendations.append(
                    DosageRecommendation(
                        medication_name=drug_name,
                        dose_adjustment=[
                            "No dosage profile available in the knowledge base — "
                            "physician must determine dosing manually."
                        ],
                    )
                )
                continue

            adjustments: List[str] = []
            factors: List[str] = []

            if context.age_years is not None and context.age_years >= 65:
                adjustments.append(
                    "Consider a lower starting dose and slower titration — patient is 65 or older."
                )
                factors.append(f"Age {context.age_years}")

            if renal_impaired:
                adjustments.append(profile.renal_adjustment)
                factors.append(
                    f"Renal function: creatinine {renal_value}" if renal_value else "Renal impairment (history)"
                )

            if hepatic_impaired:
                adjustments.append(profile.hepatic_adjustment)
                factors.append(
                    f"Hepatic function: ALT/AST {hepatic_value}" if hepatic_value else "Hepatic impairment (history)"
                )

            if severity_level in {"High", "Critical"}:
                adjustments.append(
                    f"Severity assessed as {severity_level} — closer monitoring and follow-up recommended."
                )
                factors.append(f"Severity: {severity_level}")

            if weight_vital and weight_vital.get("value"):
                factors.append(f"Weight: {weight_vital['value']} {weight_vital.get('unit') or ''}".strip())
            else:
                adjustments.append(
                    "Weight not recorded — standard adult dosing assumed. Confirm weight for "
                    "pediatric, elderly, or extreme-BMI patients."
                )

            if context.gender:
                factors.append(f"Gender: {context.gender}")

            recommendations.append(
                DosageRecommendation(
                    medication_name=profile.name,
                    starting_dose=profile.starting_dose,
                    maintenance_dose=profile.maintenance_dose,
                    maximum_dose=profile.maximum_dose,
                    dose_adjustment=adjustments,
                    adjustment_factors=factors,
                )
            )

        return recommendations
