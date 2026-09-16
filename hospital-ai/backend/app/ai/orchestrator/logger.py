"""
Logger — records every AI interaction, success or failure.

Writes one row per orchestrator call to `ai_interaction_logs` (Supabase) plus
a structured application log line. This is the single source of truth behind
the AI Infrastructure dashboard (`GET /api/ai/orchestrator/stats`).

Alongside the per-call basics (agent, task, model, duration, tokens, status)
each row records the *failover story*: which provider was tried first, which
one actually answered, why the switch happened, and the full attempt
timeline. That history is what turns "the AI felt slow yesterday" into
"Groq's daily quota ran out at 14:20 and Gemini served the next 180
requests", which is exactly the question an operator asks after an incident.

Persistence is strictly best-effort — a logging failure is swallowed and
logged locally, because telemetry must never be able to fail a clinical
request.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.logging import get_logger
from app.repositories.ai_orchestrator_repository import AIInteractionLogRepository

logger = get_logger("hospital_ai.orchestrator.interactions")


class AIInteractionLogger:
    def __init__(self, repo: Optional[AIInteractionLogRepository] = None) -> None:
        self._repo = repo or AIInteractionLogRepository()

    def log(
        self,
        *,
        agent: str,
        task: str,
        provider: str,
        model: str,
        status: str,
        duration_ms: int,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cache_hit: bool = False,
        retry_count: int = 0,
        error_message: Optional[str] = None,
        patient_id: Optional[UUID] = None,
        estimated_cost_usd: float = 0.0,
        primary_provider: str = "",
        fallback_used: bool = False,
        fallback_reason: str = "",
        attempts: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        attempts = attempts or []
        primary_provider = primary_provider or provider

        logger.info(
            "agent=%s task=%s provider=%s model=%s status=%s duration_ms=%s "
            "tokens=%s/%s cache_hit=%s retries=%s%s%s",
            agent,
            task,
            provider,
            model,
            status,
            duration_ms,
            prompt_tokens,
            completion_tokens,
            cache_hit,
            retry_count,
            f" fallback_from={primary_provider} reason={fallback_reason}"
            if fallback_used
            else "",
            f" error={error_message}" if error_message else "",
        )

        try:
            self._repo.create(
                {
                    "patient_id": str(patient_id) if patient_id else None,
                    "agent": agent,
                    "task": task,
                    "provider": provider,
                    "model": model,
                    "status": status,
                    "duration_ms": duration_ms,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "cache_hit": cache_hit,
                    "retry_count": retry_count,
                    "error_message": error_message,
                    "estimated_cost_usd": round(float(estimated_cost_usd or 0.0), 6),
                    "primary_provider": primary_provider,
                    "fallback_used": fallback_used,
                    "fallback_reason": fallback_reason or None,
                    # Stored as JSONB. Serialized defensively so an unexpected
                    # value in the timeline can't break the write.
                    "attempts": json.loads(json.dumps(attempts, default=str)),
                }
            )
        except Exception as exc:  # noqa: BLE001 - logging must never break a run
            logger.warning("Failed to persist AI interaction log: %s", exc)


_ai_interaction_logger: AIInteractionLogger | None = None


def get_ai_interaction_logger() -> AIInteractionLogger:
    global _ai_interaction_logger
    if _ai_interaction_logger is None:
        _ai_interaction_logger = AIInteractionLogger()
    return _ai_interaction_logger
