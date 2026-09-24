"""Read-only inventory adapters for the Resource Allocation Agent."""
from __future__ import annotations

from typing import Any, Dict, List

from app.repositories.intake_repositories import SupabaseRestRepository
from app.services.resource_service import resource_service


class ResourceAllocationInventoryRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("doctors")

    def list_resources(self) -> List[Dict[str, Any]]:
        # Reuse the existing inventory service so allocation observes the same
        # hospital_resources representation as the main Resources module.
        return resource_service.all_rows()

    def list_doctors(self) -> List[Dict[str, Any]]:
        return self.select(
            [
                (
                    "select",
                    "id,first_name,last_name,specialization,availability_status,department_id",
                ),
                ("limit", "500"),
            ]
        )
