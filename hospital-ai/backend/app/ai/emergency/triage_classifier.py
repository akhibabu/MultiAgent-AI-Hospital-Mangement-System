"""Emergency Agent Stage 2: triage classification."""

from __future__ import annotations

from app.ai.emergency.models import CriticalEventDetectionResult, TriageClassification, VitalMonitoringResult


class EmergencyTriageClassifier:
    """Deterministic project-level acuity classifier.

    This is an internal scoring model, not a validated clinical triage scale.
    """

    def classify(
        self,
        *,
        monitoring: VitalMonitoringResult,
        events: CriticalEventDetectionResult,
        risk_score: float | None,
        risk_level: str | None,
    ) -> TriageClassification:
        score = 0.0
        reasons: list[str] = []
        evidence: list[str] = []

        if events.critical_event_count:
            score += min(60.0, events.critical_event_count * 30.0)
            reasons.append("Critical event signal(s) were detected.")
            evidence.extend(
                e.message for e in events.events if e.severity == "critical"
            )

        score += min(35.0, monitoring.critical_count * 18.0)
        score += min(20.0, monitoring.abnormal_count * 8.0)
        if monitoring.critical_count:
            reasons.append(f"{monitoring.critical_count} critical vital signal(s) detected.")
        elif monitoring.abnormal_count:
            reasons.append(f"{monitoring.abnormal_count} abnormal vital signal(s) detected.")

        if risk_score is not None:
            score += min(25.0, max(0.0, float(risk_score)) * 0.25)
            if risk_score >= 76:
                reasons.append("Existing Intake risk score is in the critical range.")
            elif risk_score >= 51:
                reasons.append("Existing Intake risk score is in the high range.")
            elif risk_score >= 31:
                reasons.append("Existing Intake risk score is in the moderate range.")

        level = (risk_level or "").strip().lower()
        if level == "critical":
            score += 20
        elif level == "high":
            score += 12
        elif level == "moderate":
            score += 6

        score = round(min(100.0, score), 1)

        if events.critical_event_count or score >= 70:
            category = "Critical"
        elif score >= 45:
            category = "Urgent"
        elif score >= 20:
            category = "Semi-Urgent"
        else:
            category = "Routine"

        if not reasons:
            reasons.append("No Emergency v1 high-acuity trigger was detected.")

        return TriageClassification(
            category=category,
            score=score,
            escalation_required=category in {"Critical", "Urgent"},
            reasons=reasons[:8],
            evidence=evidence[:10],
        )
