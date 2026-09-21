"""Emergency Agent Stage 4: ICU requirement signal."""

from __future__ import annotations

from app.ai.emergency.models import CriticalEventDetectionResult, ICURequirementResult, VitalMonitoringResult


class ICURequirementPredictor:
    """Create a transparent acuity signal for possible ICU-level attention."""

    def predict(
        self,
        *,
        monitoring: VitalMonitoringResult,
        events: CriticalEventDetectionResult,
        risk_score: float | None,
        risk_level: str | None,
    ) -> ICURequirementResult:
        score = 0.0
        reasons: list[str] = []
        evidence: list[str] = []

        score += min(45.0, monitoring.critical_count * 20.0)
        if monitoring.critical_count:
            reasons.append("Critical vital signal(s) are present.")
            evidence.extend(
                f"{o.name}: {o.value} {o.unit}".strip()
                for o in monitoring.observations
                if o.severity == "critical"
            )

        score += min(60.0, events.critical_event_count * 25.0)
        if events.critical_event_count:
            reasons.append("Critical event signal(s) are present.")
            evidence.extend(
                e.message for e in events.events if e.severity == "critical"
            )

        if risk_score is not None:
            score += min(25.0, max(0.0, float(risk_score)) * 0.25)

        level = (risk_level or "").lower()
        if level == "critical":
            score += 15
            reasons.append("Existing Intake risk level is Critical.")
        elif level == "high":
            score += 8
            reasons.append("Existing Intake risk level is High.")

        score = round(min(100.0, score), 1)
        if score >= 60:
            signal = "High"
            confidence = 0.82
        elif score >= 30:
            signal = "Moderate"
            confidence = 0.68
        else:
            signal = "Low"
            confidence = 0.55

        if not reasons:
            reasons.append("No ICU-oriented Emergency v1 signal was detected.")

        return ICURequirementResult(
            signal=signal,
            score=score,
            confidence=confidence,
            reasons=reasons[:8],
            evidence=evidence[:10],
        )
