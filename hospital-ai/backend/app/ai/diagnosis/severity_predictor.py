"""Diagnosis Agent — Step 4: Severity Prediction."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.ai.diagnosis.models import SeverityAssessment, SEVERITY_LEVELS
from app.repositories.patient_context_repository import PatientClinicalContext

_CRITICAL_SYMPTOM_KEYWORDS = ("severe", "acute", "unresponsive", "confusion", "collapse")

_VITAL_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "heart rate": {"low": 50, "high": 120},
    "respiratory rate": {"low": 10, "high": 28},
    "temperature": {"low": 35.0, "high": 39.0},
    "oxygen saturation": {"low": 92, "high": 100},
}


def _extract_numeric(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        match = re.search(r"-?\d+(\.\d+)?", str(value))
        return float(match.group()) if match else None


class SeverityPredictor:
    """Estimates Very Low -> Critical severity with an explanation."""

    def predict(
        self,
        context: PatientClinicalContext,
        top_condition_weight: float = 0.0,
    ) -> SeverityAssessment:
        score = 0.0
        factors: List[str] = []

        # Vitals
        for vital in context.vitals:
            if not isinstance(vital, dict):
                continue
            name = str(vital.get("name", "")).lower()
            numeric = _extract_numeric(vital.get("value"))
            thresholds = next(
                (t for key, t in _VITAL_THRESHOLDS.items() if key in name), None
            )
            if numeric is not None and thresholds:
                if numeric < thresholds["low"] or numeric > thresholds["high"]:
                    score += 18
                    factors.append(
                        f"Abnormal {vital.get('name')}: {vital.get('value')} {vital.get('unit', '')}".strip()
                    )

        # Labs — flag anything explicitly marked abnormal/high/low if present
        for lab in context.lab_values:
            if not isinstance(lab, dict):
                continue
            flag = str(lab.get("flag") or lab.get("status") or "").lower()
            if flag in {"high", "low", "abnormal", "critical"}:
                score += 12
                factors.append(f"Abnormal lab: {lab.get('name')} = {lab.get('value')}")

        # Risk profile
        if context.risk_overall_score is not None:
            score += float(context.risk_overall_score) * 0.35
            if context.risk_overall_level in {"High", "Critical"}:
                factors.append(
                    f"Overall risk profile: {context.risk_overall_level} "
                    f"({context.risk_overall_score:.0f}/100)"
                )

        # History — chronic conditions raise baseline severity slightly
        if len(context.conditions) >= 2:
            score += 8
            factors.append(
                f"Multiple pre-existing conditions on record: {', '.join(context.conditions[:3])}"
            )

        # Symptom keyword scan
        history_text = " ".join(context.symptoms).lower()
        if any(word in history_text for word in _CRITICAL_SYMPTOM_KEYWORDS):
            score += 20
            factors.append("Symptom description includes acute/severe descriptors")

        # Top differential condition contributes its own severity weight
        score += top_condition_weight * 30
        if top_condition_weight >= 0.8:
            factors.append("Leading differential diagnosis carries high inherent severity")

        score = max(0.0, min(100.0, score))
        level = self._score_to_level(score)

        if not factors:
            factors.append(
                "No abnormal vitals, labs, or high-risk indicators identified in available data"
            )

        explanation = (
            f"Severity estimated as {level} (score {score:.0f}/100) based on "
            f"{len(factors)} contributing factor(s): " + "; ".join(factors[:4]) + "."
        )

        return SeverityAssessment(
            level=level,
            score=round(score, 1),
            explanation=explanation,
            contributing_factors=factors,
        )

    @staticmethod
    def _score_to_level(score: float) -> str:
        if score >= 76:
            return SEVERITY_LEVELS[4]
        if score >= 51:
            return SEVERITY_LEVELS[3]
        if score >= 31:
            return SEVERITY_LEVELS[2]
        if score >= 16:
            return SEVERITY_LEVELS[1]
        return SEVERITY_LEVELS[0]
