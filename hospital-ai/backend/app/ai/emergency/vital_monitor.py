"""Emergency Agent Stage 1: vital monitoring."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.ai.emergency.models import VitalMonitoringResult, VitalObservation

_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _number(value: Any) -> Optional[float]:
    if value is None:
        return None
    match = _NUMBER_RE.search(str(value).replace(",", ""))
    return float(match.group(0)) if match else None


def _bp(value: Any) -> Optional[Tuple[float, float]]:
    if value is None:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", str(value))
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


class VitalMonitor:
    """Analyze the latest vital observations stored in Intake context.

    Thresholds mirror the existing RiskProfiler's BP, HR and SpO2 emergency-
    oriented rules so Emergency does not create a competing interpretation.
    """

    def monitor(self, vitals: List[Dict[str, Any]]) -> VitalMonitoringResult:
        observations: List[VitalObservation] = []
        seen_keys: set[str] = set()

        for raw in reversed(vitals or []):
            if not isinstance(raw, dict):
                continue
            name = str(raw.get("name") or raw.get("type") or raw.get("vital") or "").strip()
            value = str(raw.get("value") or raw.get("reading") or "").strip()
            unit = str(raw.get("unit") or "").strip()
            if not name or not value:
                continue

            key = self._key(name)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            if key == "blood_pressure":
                observations.append(self._blood_pressure(name, value, unit))
            elif key == "heart_rate":
                observations.append(self._heart_rate(name, value, unit))
            elif key == "spo2":
                observations.append(self._spo2(name, value, unit))
            else:
                observations.append(
                    VitalObservation(
                        name=name,
                        value=value,
                        unit=unit,
                        status="observed",
                        severity="normal",
                        message="Vital received but no Emergency v1 rule is defined for this type.",
                    )
                )

        observations.reverse()

        abnormal = sum(
            1 for item in observations if item.severity in {"warning", "critical"}
        )
        critical = sum(1 for item in observations if item.severity == "critical")
        if not observations:
            status = "no_data"
        elif critical:
            status = "critical"
        elif abnormal:
            status = "warning"
        else:
            status = "stable"

        return VitalMonitoringResult(
            observations=observations,
            abnormal_count=abnormal,
            critical_count=critical,
            monitoring_status=status,
            limitations=[
                "This is an on-demand snapshot of the latest vitals available in Patient Context.",
                "It is not a streaming bedside monitor and should not replace bedside observation.",
            ],
        )

    @staticmethod
    def _key(name: str) -> str:
        n = name.lower().replace("-", " ").replace("_", " ")
        if "blood pressure" in n or n.strip() == "bp":
            return "blood_pressure"
        if "heart rate" in n or n.strip() in {"hr", "pulse"}:
            return "heart_rate"
        if "spo2" in n or "oxygen saturation" in n or "o2 saturation" in n:
            return "spo2"
        return n

    @staticmethod
    def _blood_pressure(name: str, value: str, unit: str) -> VitalObservation:
        parsed = _bp(value)
        if not parsed:
            return VitalObservation(
                name=name, value=value, unit=unit, status="observed",
                severity="unknown", message="Blood pressure format could not be parsed."
            )
        systolic, diastolic = parsed
        if systolic >= 180 or diastolic >= 120:
            return VitalObservation(
                name=name, value=value, unit=unit, status="abnormal",
                severity="critical",
                message="Blood pressure matches the existing risk model's critical threshold.",
            )
        if systolic >= 140 or diastolic >= 90:
            return VitalObservation(
                name=name, value=value, unit=unit, status="abnormal",
                severity="warning",
                message="Blood pressure matches the existing risk model's elevated threshold.",
            )
        return VitalObservation(
            name=name, value=value, unit=unit, status="normal", severity="normal",
            message="No Emergency v1 BP threshold was triggered.",
        )

    @staticmethod
    def _heart_rate(name: str, value: str, unit: str) -> VitalObservation:
        number = _number(value)
        if number is None:
            return VitalObservation(
                name=name, value=value, unit=unit, severity="unknown",
                status="observed", message="Heart rate could not be parsed."
            )
        if number >= 120 or number <= 45:
            return VitalObservation(
                name=name, value=value, unit=unit, status="abnormal",
                severity="critical",
                message="Heart rate matches the existing risk model's emergency-oriented threshold.",
            )
        return VitalObservation(
            name=name, value=value, unit=unit, status="normal", severity="normal",
            message="No Emergency v1 HR threshold was triggered.",
        )

    @staticmethod
    def _spo2(name: str, value: str, unit: str) -> VitalObservation:
        number = _number(value.replace("%", ""))
        if number is None:
            return VitalObservation(
                name=name, value=value, unit=unit, severity="unknown",
                status="observed", message="SpO2 could not be parsed."
            )
        if number < 90:
            return VitalObservation(
                name=name, value=value, unit=unit, status="abnormal",
                severity="critical",
                message="SpO2 matches the existing risk model's critical threshold.",
            )
        if number < 94:
            return VitalObservation(
                name=name, value=value, unit=unit, status="abnormal",
                severity="warning",
                message="SpO2 matches the existing risk model's low threshold.",
            )
        return VitalObservation(
            name=name, value=value, unit=unit, status="normal", severity="normal",
            message="No Emergency v1 SpO2 threshold was triggered.",
        )
