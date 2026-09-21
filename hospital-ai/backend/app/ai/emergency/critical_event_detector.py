"""Emergency Agent Stage 3: critical event detection."""

from __future__ import annotations

from typing import Iterable

from app.ai.emergency.models import CriticalEvent, CriticalEventDetectionResult, VitalMonitoringResult


class CriticalEventDetector:
    """Detect explicit high-acuity patterns from structured patient context."""

    def detect(
        self,
        *,
        conditions: Iterable[str],
        symptoms: Iterable[str],
        monitoring: VitalMonitoringResult,
        risk_level: str | None,
        risk_alerts: list[dict] | None,
    ) -> CriticalEventDetectionResult:
        conditions_l = [str(x).lower() for x in conditions if x]
        symptoms_l = [str(x).lower() for x in symptoms if x]
        alerts_l = [
            str((a or {}).get("message", "")).lower()
            for a in (risk_alerts or [])
            if isinstance(a, dict)
        ]

        events: list[CriticalEvent] = []

        def add(event_type: str, severity: str, evidence: list[str], message: str) -> None:
            events.append(
                CriticalEvent(
                    event_type=event_type,
                    severity=severity,
                    evidence=evidence,
                    message=message,
                )
            )

        if any("sepsis" in c for c in conditions_l) or any("sepsis" in a for a in alerts_l):
            add(
                "sepsis_signal",
                "critical",
                ["Sepsis appears in recognized conditions/risk alerts."],
                "Sepsis-related emergency signal detected from existing patient context.",
            )

        if any(
            "myocardial infarction" in c or "acute coronary" in c or c == "heart attack"
            for c in conditions_l
        ):
            add(
                "acute_cardiac_signal",
                "critical",
                ["Acute cardiac condition appears in recognized conditions."],
                "Acute cardiac emergency signal detected from existing patient context.",
            )

        if any("stroke" in c or "cva" in c for c in conditions_l):
            add(
                "stroke_signal",
                "critical",
                ["Stroke/CVA appears in recognized conditions."],
                "Stroke-related emergency signal detected from existing patient context.",
            )

        if any("anaphylaxis" in c for c in conditions_l):
            add(
                "anaphylaxis_signal",
                "critical",
                ["Anaphylaxis appears in recognized conditions."],
                "Anaphylaxis-related emergency signal detected from existing patient context.",
            )

        if any("chest pain" in s for s in symptoms_l) and any(
            "shortness of breath" in s or "dyspnea" in s for s in symptoms_l
        ):
            add(
                "cardiorespiratory_combination",
                "critical",
                ["Chest pain and dyspnea/shortness of breath are both recognized."],
                "Combined cardiorespiratory symptom signal requires urgent clinician review.",
            )

        critical_vitals = [
            o for o in monitoring.observations if o.severity == "critical"
        ]
        for observation in critical_vitals:
            add(
                f"critical_vital:{observation.name.lower()}",
                "critical",
                [f"{observation.name}: {observation.value} {observation.unit}".strip()],
                observation.message,
            )

        if len(critical_vitals) >= 2:
            add(
                "multiple_critical_vitals",
                "critical",
                [f"{len(critical_vitals)} critical vital observations are present."],
                "Multiple critical vital signals detected.",
            )

        if (risk_level or "").lower() == "critical":
            add(
                "critical_risk_profile",
                "critical",
                ["Existing Intake Risk Profile is marked Critical."],
                "The existing patient risk profile indicates critical acuity.",
            )
        elif (risk_level or "").lower() == "high":
            add(
                "high_risk_profile",
                "high",
                ["Existing Intake Risk Profile is marked High."],
                "The existing patient risk profile indicates high acuity.",
            )

        unique: dict[str, CriticalEvent] = {}
        for event in events:
            current = unique.get(event.event_type)
            if current is None or event.severity == "critical":
                unique[event.event_type] = event

        final_events = list(unique.values())
        critical_count = sum(1 for e in final_events if e.severity == "critical")
        return CriticalEventDetectionResult(
            events=final_events,
            detected_event_count=len(final_events),
            critical_event_count=critical_count,
        )
