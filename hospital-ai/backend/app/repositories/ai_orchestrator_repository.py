"""
Repositories backing the AI Orchestrator: per-patient conversation memory
(`ai_conversation_memory`) and every AI interaction log (`ai_interaction_logs`).

See `migrations/017_create_ai_orchestrator_tables.sql` for the schema.
"""
from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from app.repositories.intake_repositories import SupabaseRestRepository


class ConversationMemoryRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("ai_conversation_memory")

    def create(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.insert(body)

    def recent_for_patient_agent(
        self, patient_id: UUID, agent: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        return self.select(
            [
                ("select", "*"),
                ("patient_id", f"eq.{patient_id}"),
                ("agent", f"eq.{agent}"),
                ("order", "created_at.desc"),
                ("limit", str(min(max(limit, 1), 50))),
            ]
        )


class AIInteractionLogRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("ai_interaction_logs")

    def create(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.insert(body)

    def recent(self, limit: int = 200) -> List[Dict[str, Any]]:
        return self.select(
            [
                ("select", "*"),
                ("order", "created_at.desc"),
                ("limit", str(min(max(limit, 1), 5000))),
            ]
        )
