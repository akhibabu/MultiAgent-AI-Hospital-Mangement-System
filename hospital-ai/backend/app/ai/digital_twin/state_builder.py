"""Build a hospital-wide operational snapshot from current application data."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List

from app.ai.digital_twin.models import (
    FlowTwinState,
    HospitalTwinState,
    ResourceTwinState,
    StaffTwinState,
)
from app.repositories.digital_twin_repository import DigitalTwinDataRepository


class DigitalTwinStateBuilder:
    """Create a read-only operational mirror. No source tables are mutated."""

    def __init__(self, data: DigitalTwinDataRepository | None = None) -> None:
        self._data = data or DigitalTwinDataRepository()

    def build(self) -> HospitalTwinState:
        now = datetime.now(timezone.utc)
        day_ahead = now + timedelta(hours=24)
        week_ahead = now + timedelta(days=7)
        since = now - timedelta(hours=24)

        source_status: Dict[str, bool] = {}
        source_timestamps: Dict[str, str] = {}

        resources = self._safe("resources", self._data.resources, source_status)
        doctors = self._safe("doctors", self._data.doctors, source_status)
        appointments_24h = self._safe(
            "appointments_24h",
            lambda: self._data.appointments(now.date(), day_ahead.date()),
            source_status,
        )
        appointments_7d = self._safe(
            "appointments_7d",
            lambda: self._data.appointments(now.date(), week_ahead.date()),
            source_status,
        )
        emergencies = self._safe(
            "emergency_results",
            lambda: self._data.recent_emergencies(since.isoformat()),
            source_status,
        )
        scheduling = self._safe(
            "scheduling_results",
            lambda: self._data.recent_rows("scheduling_results", since.isoformat()),
            source_status,
        )
        allocations = self._safe(
            "resource_allocation_results",
            lambda: self._data.recent_rows("resource_allocation_results", since.isoformat()),
            source_status,
        )

        if resources:
            source_timestamps["resources"] = self._latest(resources)
        if appointments_7d:
            source_timestamps["appointments"] = self._latest(appointments_7d)
        if emergencies:
            source_timestamps["emergency_results"] = self._latest(emergencies)
        if scheduling:
            source_timestamps["scheduling_results"] = self._latest(scheduling)
        if allocations:
            source_timestamps["resource_allocation_results"] = self._latest(allocations)

        resource_states = self._resource_states(resources)
        staff = self._staff_state(doctors)
        flow = self._flow_state(
            appointments_24h,
            appointments_7d,
            emergencies,
            scheduling,
            allocations,
        )
        pressure = self._pressure(resource_states, staff, flow)

        return HospitalTwinState(
            resources=resource_states,
            staff=staff,
            flow=flow,
            operational_pressure=pressure,
            source_status=source_status,
            source_timestamps=source_timestamps,
        )

    @staticmethod
    def _safe(name: str, fn, status: Dict[str, bool]):
        try:
            value = fn()
            status[name] = True
            return value if isinstance(value, list) else []
        except Exception:
            status[name] = False
            return []

    @staticmethod
    def _latest(rows: Iterable[Dict[str, Any]]) -> str:
        values = [str(r.get("created_at") or r.get("updated_at") or "") for r in rows]
        return max(values) if values else ""

    @staticmethod
    def _resource_states(rows: List[Dict[str, Any]]) -> List[ResourceTwinState]:
        grouped: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            "total": 0,
            "available": 0,
            "maintenance": 0,
            "out": 0,
        })
        for row in rows:
            kind = str(row.get("resource_type") or "Other")
            quantity = max(0, int(row.get("quantity") or 0))
            available = min(quantity, max(0, int(row.get("available_quantity") or 0)))
            status = str(row.get("status") or "")
            bucket = grouped[kind]
            bucket["total"] += quantity
            bucket["available"] += available
            if status == "Maintenance":
                bucket["maintenance"] += quantity
            elif status == "Out of Service":
                bucket["out"] += quantity

        result: List[ResourceTwinState] = []
        for kind, values in sorted(grouped.items()):
            total = values["total"]
            available = min(total, values["available"])
            in_use = max(0, total - available - values["maintenance"] - values["out"])
            utilization = round(((total - available) / total) * 100, 1) if total else 0.0
            result.append(
                ResourceTwinState(
                    resource_type=kind,
                    total_quantity=total,
                    available_quantity=available,
                    in_use_quantity=in_use,
                    maintenance_quantity=values["maintenance"],
                    out_of_service_quantity=values["out"],
                    utilization_percent=min(100.0, utilization),
                )
            )
        return result

    @staticmethod
    def _staff_state(rows: List[Dict[str, Any]]) -> StaffTwinState:
        total = len(rows)
        available = sum(1 for r in rows if str(r.get("availability_status") or "") == "Available")
        busy = sum(1 for r in rows if str(r.get("availability_status") or "") == "Busy")
        leave = sum(1 for r in rows if str(r.get("availability_status") or "") == "On Leave")
        utilization = ((total - available) / total) * 100 if total else 0.0
        return StaffTwinState(
            total_doctors=total,
            available_doctors=available,
            busy_doctors=busy,
            on_leave_doctors=leave,
            utilization_percent=round(min(100.0, utilization), 1),
        )

    @staticmethod
    def _flow_state(
        appointments_24h: List[Dict[str, Any]],
        appointments_7d: List[Dict[str, Any]],
        emergencies: List[Dict[str, Any]],
        scheduling: List[Dict[str, Any]],
        allocations: List[Dict[str, Any]],
    ) -> FlowTwinState:
        high_critical = 0
        icu_signals = 0
        for row in emergencies:
            priority = row.get("patient_priority_json") or {}
            level = str(priority.get("priority_level") or "").strip().lower()
            if level in {"high", "critical"}:
                high_critical += 1
            icu = row.get("icu_requirement_json") or {}
            required = icu.get("required")
            if required is True or str(icu.get("level") or "").lower() in {"high", "critical", "required"}:
                icu_signals += 1

        conflict_count = 0
        for row in allocations:
            conflicts = row.get("conflicts_json") or []
            if isinstance(conflicts, list):
                conflict_count += len(conflicts)

        return FlowTwinState(
            appointments_next_24h=sum(1 for r in appointments_24h if str(r.get("status") or "") in {"Scheduled", "Rescheduled"}),
            appointments_next_7d=sum(1 for r in appointments_7d if str(r.get("status") or "") in {"Scheduled", "Rescheduled"}),
            emergency_results_last_24h=len(emergencies),
            high_or_critical_emergencies=high_critical,
            icu_signals_last_24h=icu_signals,
            scheduling_runs_last_24h=len(scheduling),
            allocation_runs_last_24h=len(allocations),
            allocation_conflicts_last_24h=conflict_count,
        )

    @staticmethod
    def _pressure(
        resources: List[ResourceTwinState],
        staff: StaffTwinState,
        flow: FlowTwinState,
    ) -> float:
        critical_types = {"Bed", "ICU Bed", "Ventilator", "Operation Theatre"}
        utilizations = [
            r.utilization_percent for r in resources if r.resource_type in critical_types and r.total_quantity
        ]
        resource_pressure = max(utilizations, default=0.0)
        staff_pressure = staff.utilization_percent
        emergency_pressure = min(100.0, flow.high_or_critical_emergencies * 15.0 + flow.icu_signals_last_24h * 10.0)
        appointment_pressure = min(100.0, flow.appointments_next_24h * 2.0)
        return round(min(100.0, max(resource_pressure, staff_pressure * 0.9, emergency_pressure, appointment_pressure)), 1)
