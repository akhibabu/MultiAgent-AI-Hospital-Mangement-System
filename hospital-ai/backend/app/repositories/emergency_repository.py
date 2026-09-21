"""Emergency Agent repository — append-only emergency_results history."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from app.repositories.intake_repositories import SupabaseRestRepository


class EmergencyResultRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("emergency_results")

    def create(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.insert(body)

    def get_latest_for_patient(self, patient_id: UUID) -> Optional[Dict[str, Any]]:
        rows = self.select(
            [
                ("select", "*"),
                ("patient_id", f"eq.{patient_id}"),
                ("order", "created_at.desc"),
                ("limit", "1"),
            ]
        )
        return rows[0] if rows else None

    def list_for_patient(self, patient_id: UUID, limit: int = 20) -> List[Dict[str, Any]]:
        return self.select(
            [
                ("select", "*"),
                ("patient_id", f"eq.{patient_id}"),
                ("order", "created_at.desc"),
                ("limit", str(min(max(limit, 1), 100))),
            ]
        )
