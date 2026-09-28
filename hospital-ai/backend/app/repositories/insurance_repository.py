"""Repositories for Insurance Agent policies and run results."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from app.repositories.intake_repositories import SupabaseRestRepository


class InsurancePolicyRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("insurance_policies")

    def get_latest_for_patient(self, patient_id: UUID) -> Optional[Dict[str, Any]]:
        rows = self.select(
            [
                ("select", "*"),
                ("patient_id", f"eq.{patient_id}"),
                ("order", "updated_at.desc"),
                ("limit", "1"),
            ]
        )
        return rows[0] if rows else None

    def get_by_policy_number(
        self, patient_id: UUID, policy_number: str
    ) -> Optional[Dict[str, Any]]:
        rows = self.select(
            [
                ("select", "*"),
                ("patient_id", f"eq.{patient_id}"),
                ("policy_number", f"eq.{policy_number}"),
                ("limit", "1"),
            ]
        )
        return rows[0] if rows else None

    def create(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.insert(body)

    def upsert_for_patient(
        self,
        *,
        patient_id: UUID,
        policy: Dict[str, Any],
    ) -> Dict[str, Any]:
        existing = self.get_by_policy_number(
            patient_id,
            str(policy.get("policy_number") or ""),
        )
        body = {
            "patient_id": str(patient_id),
            **policy,
        }
        if existing:
            return self.update(UUID(str(existing["id"])), body)
        return self.create(body)


class InsuranceResultRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("insurance_results")

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
        rows = self.select(
            [
                ("select", "*"),
                ("patient_id", f"eq.{patient_id}"),
                ("order", "created_at.desc"),
                ("limit", str(min(max(limit, 1), 100))),
            ]
        )
        return rows
