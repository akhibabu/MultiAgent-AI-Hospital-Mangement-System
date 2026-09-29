"""Data access for the Hospital Digital Twin."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from app.repositories.intake_repositories import SupabaseRestRepository


class DigitalTwinDataRepository(SupabaseRestRepository):
    """Read-only source adapter for the live hospital operational state."""

    def __init__(self) -> None:
        super().__init__("hospital_resources")

    def resources(self) -> List[Dict[str, Any]]:
        return self.select([
            ("select", "id,resource_name,resource_type,quantity,available_quantity,status,location,updated_at"),
            ("order", "resource_type.asc,resource_name.asc"),
        ])

    def doctors(self) -> List[Dict[str, Any]]:
        return self._table_select("doctors", [
            ("select", "id,availability_status,department_id,updated_at"),
        ])

    def appointments(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        return self._table_select("appointments", [
            ("select", "id,patient_id,doctor_id,appointment_date,start_time,end_time,status,visit_type,updated_at"),
            ("appointment_date", f"gte.{start_date.isoformat()}"),
            ("appointment_date", f"lte.{end_date.isoformat()}"),
            ("status", "in.(Scheduled,Rescheduled)"),
            ("order", "appointment_date.asc,start_time.asc"),
        ])

    def recent_emergencies(self, since_iso: str) -> List[Dict[str, Any]]:
        return self._table_select("emergency_results", [
            ("select", "id,patient_id,patient_priority_json,triage_classification_json,icu_requirement_json,created_at"),
            ("created_at", f"gte.{since_iso}"),
            ("order", "created_at.desc"),
            ("limit", "500"),
        ])

    def recent_rows(self, table: str, since_iso: str) -> List[Dict[str, Any]]:
        select = "id,created_at"
        if table == "resource_allocation_results":
            select = "id,conflicts_json,created_at"
        return self._table_select(table, [
            ("select", select),
            ("created_at", f"gte.{since_iso}"),
            ("order", "created_at.desc"),
            ("limit", "500"),
        ])

    def get_latest_run(self) -> Optional[Dict[str, Any]]:
        rows = self._table_select("digital_twin_runs", [
            ("select", "*"),
            ("order", "created_at.desc"),
            ("limit", "1"),
        ])
        return rows[0] if rows else None

    def list_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._table_select("digital_twin_runs", [
            ("select", "id,created_at,status,engine,horizon_hours,processing_time_ms,simulation_json"),
            ("order", "created_at.desc"),
            ("limit", str(min(max(limit, 1), 100))),
        ])

    def create_run(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self._table_select_insert("digital_twin_runs", body)

    def _table_select(self, table: str, params: List[tuple[str, str]]) -> List[Dict[str, Any]]:
        previous = self.table
        self.table = table
        try:
            return self.select(params)
        finally:
            self.table = previous

    def _table_select_insert(self, table: str, body: Dict[str, Any]) -> Dict[str, Any]:
        previous = self.table
        self.table = table
        try:
            return self.insert(body)
        finally:
            self.table = previous
