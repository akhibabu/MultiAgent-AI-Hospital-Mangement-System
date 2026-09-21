"""Emergency Agent Stage 5: alert generation."""

from __future__ import annotations

from app.ai.emergency.models import (
    CriticalEventDetectionResult,
    EmergencyAlert,
    EmergencyAlertGenerationResult,
    ICURequirementResult,
    TriageClassification,
    VitalMonitoringResult,
)


class EmergencyAlertGenerator:
    """Convert deterministic findings into auditable in-application alerts."""

    def generate(
        self,
        *,
        monitoring: VitalMonitoringResult,
        triage: TriageClassification,
        events: CriticalEventDetectionResult,
        icu: ICURequirementResult,
    ) -> EmergencyAlertGenerationResult:
        alerts: list[EmergencyAlert] = []

        if triage.category == "Critical":
            alerts.append(
                EmergencyAlert(
                    code="EMERGENCY_CRITICAL",
                    severity="critical",
                    title="Critical emergency acuity",
                    message="The current Emergency Agent snapshot contains critical acuity signals.",
                    recommended_next_step="Immediate clinician review and activation of the hospital's emergency protocol.",
                )
            )
        elif triage.category == "Urgent":
            alerts.append(
                EmergencyAlert(
                    code="EMERGENCY_URGENT",
                    severity="high",
                    title="Urgent emergency acuity",
                    message="The current Emergency Agent snapshot contains urgent acuity signals.",
                    recommended_next_step="Prompt clinician assessment and escalation according to local protocol.",
                )
            )

        for event in events.events:
            if event.severity == "critical":
                alerts.append(
                    EmergencyAlert(
                        code=f"EVENT_{event.event_type.upper()}",
                        severity="critical",
                        title=event.event_type.replace("_", " ").title(),
                        message=event.message,
                        recommended_next_step="Review the supporting evidence and follow applicable emergency protocol.",
                    )
                )

        for observation in monitoring.observations:
            if observation.severity == "critical":
                alerts.append(
                    EmergencyAlert(
                        code="VITAL_CRITICAL",
                        severity="critical",
                        title=f"Critical vital: {observation.name}",
                        message=f"{observation.name}: {observation.value} {observation.unit}".strip(),
                        recommended_next_step="Recheck the measurement and escalate for clinician review.",
                    )
                )
            elif observation.severity == "warning":
                alerts.append(
                    EmergencyAlert(
                        code="VITAL_WARNING",
                        severity="warning",
                        title=f"Abnormal vital: {observation.name}",
                        message=f"{observation.name}: {observation.value} {observation.unit}".strip(),
                        recommended_next_step="Review the measurement in the patient chart and repeat as appropriate.",
                    )
                )

        if icu.signal == "High":
            alerts.append(
                EmergencyAlert(
                    code="ICU_SIGNAL_HIGH",
                    severity="high",
                    title="High ICU requirement signal",
                    message="The project-level ICU signal is high based on the current emergency findings.",
                    recommended_next_step="Escalate for clinician-led ICU assessment; the score does not decide admission.",
                )
            )

        deduped: dict[tuple[str, str], EmergencyAlert] = {}
        for alert in alerts:
            deduped[(alert.code, alert.message)] = alert
        alerts = list(deduped.values())

        severity_order = {"critical": 3, "high": 2, "warning": 1, "info": 0}
        highest = max(
            (a.severity for a in alerts),
            key=lambda s: severity_order.get(s, 0),
            default="None",
        )
        return EmergencyAlertGenerationResult(
            alerts=alerts,
            alert_count=len(alerts),
            highest_severity=highest,
        )
