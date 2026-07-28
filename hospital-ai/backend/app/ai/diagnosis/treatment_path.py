"""Diagnosis Agent — Step 5: Treatment Path Recommendation (pathways only, never medication)."""

from __future__ import annotations

from typing import List

from app.ai.diagnosis.knowledge_base import ConditionKnowledgeBase
from app.ai.diagnosis.models import (
    DifferentialDiagnosis,
    SeverityAssessment,
    TreatmentPathRecommendation,
)

_URGENCY_BY_LEVEL = {
    "Critical": "Immediate — Emergency Department",
    "High": "Urgent — within 24 hours",
    "Moderate": "Prompt — within a few days",
    "Low": "Routine follow-up",
    "Very Low": "Routine follow-up",
}


class TreatmentPathRecommender:
    """Recommends specialist/department/test pathways only — no medication."""

    def __init__(self, knowledge_base: ConditionKnowledgeBase | None = None) -> None:
        self._kb = knowledge_base or ConditionKnowledgeBase()

    def recommend(
        self,
        differentials: List[DifferentialDiagnosis],
        severity: SeverityAssessment,
    ) -> TreatmentPathRecommendation:
        specialists: List[str] = []
        tests: List[str] = []
        imaging: List[str] = []
        department = None

        top = differentials[:3]
        for diff in top:
            profile = self._kb.get(diff.condition)
            if not profile:
                continue
            for s in profile.specialists:
                if s not in specialists:
                    specialists.append(s)
            for t in profile.diagnostic_tests:
                if t not in tests:
                    tests.append(t)
            for i in profile.imaging:
                if i not in imaging:
                    imaging.append(i)
            if department is None:
                department = profile.department

        if severity.level in {"Critical", "High"} and "Emergency Department" not in specialists:
            specialists.insert(0, "Emergency Department")

        if not specialists:
            specialists.append("General Physician")
            department = department or "General Medicine"

        urgency = _URGENCY_BY_LEVEL.get(severity.level, "Routine follow-up")

        notes = (
            "Recommended pathway only — diagnostic tests and specialist referral "
            "suggestions. No medication is prescribed by this system; treatment "
            "decisions remain with the attending physician."
        )

        return TreatmentPathRecommendation(
            recommended_specialists=specialists[:5],
            recommended_department=department,
            diagnostic_tests=tests[:8],
            imaging=imaging[:5],
            urgency=urgency,
            notes=notes,
        )
