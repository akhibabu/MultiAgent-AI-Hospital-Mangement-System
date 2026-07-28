"""Research Agent repositories — `research_results` + `clinical_evidence`."""

from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.database.http import get_http_client
from app.repositories.intake_repositories import SupabaseRestRepository


class ResearchResultRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("research_results")

    def create(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.insert(body)

    def get_latest_for_patient(self, patient_id: UUID) -> Dict[str, Any] | None:
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


class ClinicalEvidenceRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("clinical_evidence")

    def create_many(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not rows:
            return []
        out: List[Dict[str, Any]] = []
        batch_size = 50
        for i in range(0, len(rows), batch_size):
            chunk = rows[i : i + batch_size]
            try:
                out.extend(self._insert_many(chunk))
            except Exception:  # noqa: BLE001
                for row in chunk:
                    out.append(self.insert(row))
        return out

    def _insert_many(self, body: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        try:
            response = get_http_client().post(
                self._url(),
                headers=self._headers(prefer="return=representation"),
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to reach Supabase") from exc
        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to insert clinical_evidence: {response.text[:300]}",
            )
        data = response.json()
        return data if isinstance(data, list) else [data]

    def list_for_research(self, research_result_id: UUID) -> List[Dict[str, Any]]:
        return self.select(
            [
                ("select", "*"),
                ("research_result_id", f"eq.{research_result_id}"),
                ("order", "confidence.desc"),
            ]
        )
