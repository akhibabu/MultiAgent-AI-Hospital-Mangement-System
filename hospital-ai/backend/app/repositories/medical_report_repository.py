"""
Medical Report Agent repositories.

`generated_medical_reports` (append-only, versioned run aggregate) +
`referral_letters` + `insurance_documents` (normalized, queryable children).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from app.repositories.intake_repositories import SupabaseRestRepository


class GeneratedMedicalReportRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("generated_medical_reports")

    def create(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.insert(body)

    def get_by_id(self, row_id: UUID, select: str = "*") -> Optional[Dict[str, Any]]:  # type: ignore[override]
        return super().get_by_id(row_id, select=select)

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

    def count_for_patient(self, patient_id: UUID) -> int:
        rows = self.select(
            [
                ("select", "id"),
                ("patient_id", f"eq.{patient_id}"),
            ]
        )
        return len(rows)


class ReferralLetterRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("referral_letters")

    def create(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.insert(body)

    def get_for_report(self, generated_report_id: UUID) -> Optional[Dict[str, Any]]:
        rows = self.select(
            [
                ("select", "*"),
                ("generated_report_id", f"eq.{generated_report_id}"),
                ("limit", "1"),
            ]
        )
        return rows[0] if rows else None


class InsuranceDocumentRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("insurance_documents")

    def create(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.insert(body)

    def get_for_report(self, generated_report_id: UUID) -> Optional[Dict[str, Any]]:
        rows = self.select(
            [
                ("select", "*"),
                ("generated_report_id", f"eq.{generated_report_id}"),
                ("limit", "1"),
            ]
        )
        return rows[0] if rows else None
