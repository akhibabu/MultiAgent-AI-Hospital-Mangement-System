"""Cross-agent context for Resource Allocation."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from app.ai.resource_allocation.models import ResourceRequirement
from app.repositories.emergency_repository import EmergencyResultRepository
from app.repositories.patient_context_repository import PatientClinicalContextRepository
from app.repositories.scheduling_result_repository import SchedulingResultRepository


def _unique(values: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            result.append(cleaned)
    return result


class ResourceAllocationContext:
    """Loads only persisted upstream outputs needed for resource planning."""

    def __init__(
        self,
        *,
        scheduling: Optional[SchedulingResultRepository] = None,
        emergency: Optional[EmergencyResultRepository] = None,
        patient_context: Optional[PatientClinicalContextRepository] = None,
    ) -> None:
        self.scheduling = scheduling or SchedulingResultRepository()
        self.emergency = emergency or EmergencyResultRepository()
        self.patient_context = patient_context or PatientClinicalContextRepository()

    def load(self, patient_id: UUID) -> Dict[str, Any]:
        return {
            "patient": self.patient_context.load(patient_id),
            "scheduling": self.scheduling.get_latest_for_patient(patient_id),
            "emergency": self.emergency.get_latest_for_patient(patient_id),
        }

    @staticmethod
    def derive(source: Dict[str, Any]) -> Dict[str, Any]:
        patient = source.get("patient")
        scheduling = source.get("scheduling") or {}
        emergency = source.get("emergency") or {}

        requirements_json = scheduling.get("resource_requirements_json") or []
        procedures = scheduling.get("procedures_json") or []
        surgery = scheduling.get("surgery_scheduling_json") or {}
        surgery_recommendation = scheduling.get("surgery_recommendation_json") or []
        specialists = scheduling.get("derived_specialists_json") or []
        priority_level = str(
            scheduling.get("emergency_priority_level")
            or ((emergency.get("patient_priority_json") or {}).get("priority_level"))
            or "Routine"
        ).strip() or "Routine"
        priority_score = _number(
            scheduling.get("emergency_priority_score")
            or ((emergency.get("patient_priority_json") or {}).get("priority_score"))
        )
        icu_signal = str(
            ((emergency.get("icu_requirement_json") or {}).get("signal"))
            or ""
        ).strip()

        requirements: List[ResourceRequirement] = []
        seen = set()

        def add(
            label: str,
            resource_type: Optional[str],
            source_name: str,
            rationale: str,
            quantity: int = 1,
            priority: Optional[int] = None,
        ) -> None:
            key = (label.lower(), (resource_type or "").lower())
            if key in seen:
                return
            seen.add(key)
            requirements.append(
                ResourceRequirement(
                    requirement=label,
                    resource_type=resource_type,
                    required_quantity=max(1, quantity),
                    source=source_name,
                    rationale=rationale,
                    priority=priority if priority is not None else _requirement_priority(label, priority_level),
                )
            )

        for raw in requirements_json if isinstance(requirements_json, list) else []:
            label = str(raw or "").strip()
            if not label:
                continue
            add(
                label,
                _resource_type_for(label),
                "Scheduling Agent",
                "Derived from the Scheduling Agent downstream resource requirements.",
            )

        if bool(surgery.get("required")):
            add(
                "Operating Theatre",
                "Operation Theatre",
                "Scheduling Agent",
                "Required by the upstream surgery scheduling recommendation.",
                priority=_requirement_priority("Operating Theatre", priority_level),
            )

        if procedures and bool(surgery.get("required")):
            add(
                "Procedure Support Equipment",
                "Medical Equipment",
                "Scheduling Agent",
                "Procedure/surgery recommendation requires equipment capacity to be validated downstream.",
            )

        if not scheduling and icu_signal == "High":
            add(
                "ICU Bed",
                "ICU Bed",
                "Emergency Agent",
                "Fallback requirement from the latest Emergency ICU acuity signal.",
                priority=_requirement_priority("ICU Bed", priority_level),
            )
        elif icu_signal == "High":
            add(
                "ICU Bed",
                "ICU Bed",
                "Emergency Agent",
                "Emergency Agent ICU signal is High; Scheduling context should carry the same downstream requirement.",
                priority=_requirement_priority("ICU Bed", priority_level),
            )
        elif icu_signal == "Moderate":
            add(
                "Monitored Bed",
                "Bed",
                "Emergency Agent",
                "Emergency Agent ICU signal is Moderate; a monitored bed is represented using the existing Bed inventory type.",
                priority=_requirement_priority("Monitored Bed", priority_level),
            )

        return {
            "patient_name": getattr(patient, "patient_name", None) or "Patient",
            "priority_level": priority_level,
            "priority_score": min(100.0, max(0.0, priority_score)),
            "requirements": requirements,
            "procedures": _unique(procedures if isinstance(procedures, list) else []),
            "specialists": _unique(specialists if isinstance(specialists, list) else []),
            "surgery_required": bool(surgery.get("required")),
            "surgery_recommendation": _unique(
                surgery_recommendation if isinstance(surgery_recommendation, list) else []
            ),
            "sources_available": {
                "scheduling": bool(scheduling),
                "emergency": bool(emergency),
            },
            "source_result_ids": {
                "scheduling": str(scheduling.get("id")) if scheduling.get("id") else None,
                "emergency": str(emergency.get("id")) if emergency.get("id") else None,
            },
        }


def _resource_type_for(label: str) -> Optional[str]:
    key = label.strip().lower()
    mappings = {
        "icu bed": "ICU Bed",
        "monitored bed": "Bed",
        "bed": "Bed",
        "operating theatre": "Operation Theatre",
        "ventilator": "Ventilator",
        "ambulance": "Ambulance",
        "wheelchair": "Wheelchair",
        "laboratory capacity": "Laboratory",
        "laboratory": "Laboratory",
        "pharmacy": "Pharmacy",
        "imaging capacity": "Medical Equipment",
        "medical equipment": "Medical Equipment",
        "procedure support equipment": "Medical Equipment",
        "specialist staff": None,
    }
    return mappings.get(key)


def _requirement_priority(label: str, level: str) -> int:
    base = {"Critical": 100, "Urgent": 85, "Semi-Urgent": 65, "Routine": 40}.get(level, 40)
    key = label.lower()
    if "icu" in key or "ventilator" in key:
        return min(100, base + 5)
    if "theatre" in key or "surgery" in key:
        return min(100, base + 3)
    return base


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
