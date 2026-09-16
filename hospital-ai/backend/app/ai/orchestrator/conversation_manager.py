"""
ConversationManager — per-patient AI memory, reusable across every agent.

Stores previous prompts, previous responses, and context history per
(patient, agent) pair in `ai_conversation_memory` (Supabase), so memory
survives backend restarts and is shared by the whole team, not just one
process. A memory read/write failure never breaks an agent run — it is
logged and the orchestrator continues without that context.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from app.ai.orchestrator.interfaces import IConversationMemory
from app.ai.orchestrator.utils import truncate
from app.core.logging import get_logger
from app.repositories.ai_orchestrator_repository import ConversationMemoryRepository

logger = get_logger("hospital_ai.orchestrator.memory")


class ConversationManager(IConversationMemory):
    def __init__(self, repo: Optional[ConversationMemoryRepository] = None) -> None:
        self._repo = repo or ConversationMemoryRepository()

    def recent(self, patient_id: UUID, agent: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            return self._repo.recent_for_patient_agent(patient_id, agent, limit)
        except Exception as exc:  # noqa: BLE001 - memory must never break a run
            logger.warning("Conversation memory read failed (continuing without it): %s", exc)
            return []

    def append(
        self,
        patient_id: UUID,
        agent: str,
        task: str,
        prompt_rendered: str,
        response_text: str,
        response_json: Optional[Dict[str, Any]],
        model: str,
        provider: str,
    ) -> None:
        try:
            self._repo.create(
                {
                    "patient_id": str(patient_id),
                    "agent": agent,
                    "task": task,
                    "prompt_rendered": truncate(prompt_rendered, 8000),
                    "response_text": truncate(response_text, 8000),
                    "response_json": response_json,
                    "model": model,
                    "provider": provider,
                }
            )
        except Exception as exc:  # noqa: BLE001 - memory must never break a run
            logger.warning("Conversation memory write failed (continuing): %s", exc)


_conversation_manager: ConversationManager | None = None


def get_conversation_manager() -> ConversationManager:
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager
