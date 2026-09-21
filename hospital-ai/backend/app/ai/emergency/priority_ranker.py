"""Emergency Agent Stage 6: patient priority ranking score."""

from __future__ import annotations

from app.ai.emergency.models import (
    CriticalEventDetectionResult,
    PatientPriorityRanking,
    TriageClassification,
    VitalMonitoringResult,
)


class PatientPriorityRanker:
    """Produce a normalized emergency acuity score for downstream queueing.

    The result is a score for one patient, not a global queue position.
    A future scheduler can sort multiple patient scores without changing this
    component.
    """

    def rank(
        self,
        *,
        triage: TriageClassification,
        monitoring: VitalMonitoringResult,
        events: CriticalEventDetectionResult,
        icu_signal: str,
    ) -> PatientPriorityRanking:
        score = triage.score
        factors = list(triage.reasons)

        score += min(15.0, events.critical_event_count * 7.5)
        score += min(10.0, monitoring.critical_count * 5.0)
        if icu_signal == "High":
            score += 8
            factors.append("High ICU requirement signal.")
        elif icu_signal == "Moderate":
            score += 4
            factors.append("Moderate ICU requirement signal.")

        score = round(min(100.0, score), 1)

        if score >= 70:
            level = "Critical"
        elif score >= 45:
            level = "Urgent"
        elif score >= 20:
            level = "Semi-Urgent"
        else:
            level = "Routine"

        return PatientPriorityRanking(
            priority_score=score,
            priority_level=level,
            factors=factors[:10],
        )
