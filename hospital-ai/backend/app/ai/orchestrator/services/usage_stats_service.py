"""
UsageStatsService — aggregates `ai_interaction_logs` into dashboard-ready
statistics: requests today, average response time, cache-hit rate, retry
rate, and a per-agent breakdown.

PostgREST has no server-side aggregation, so this pulls a bounded recent
window of log rows and aggregates in Python. That is fine at this
project's scale; a Postgres RPC/materialized view can replace the
implementation later without changing the API contract
(`GET /api/ai/orchestrator/stats`).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.ai.orchestrator.models import UsageStats
from app.repositories.ai_orchestrator_repository import AIInteractionLogRepository


class UsageStatsService:
    def __init__(self, repo: Optional[AIInteractionLogRepository] = None) -> None:
        self._repo = repo or AIInteractionLogRepository()

    def get_stats(self, *, window: int = 1000) -> UsageStats:
        try:
            rows = self._repo.recent(limit=window)
        except Exception:  # noqa: BLE001 - dashboard must degrade gracefully
            rows = []
        return self._aggregate(rows)

    def get_recent_logs(self, *, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            return self._repo.recent(limit=limit)
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def _aggregate(rows: List[Dict[str, Any]]) -> UsageStats:
        if not rows:
            return UsageStats()

        today = datetime.now(timezone.utc).date().isoformat()
        total = len(rows)
        today_count = 0
        durations: List[float] = []
        cache_hits = 0
        retries = 0
        errors = 0
        by_agent: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"requests": 0, "cache_hits": 0, "errors": 0, "durations": []}
        )

        for row in rows:
            created_at = str(row.get("created_at") or "")
            if created_at.startswith(today):
                today_count += 1

            duration = row.get("duration_ms")
            is_error = row.get("status") not in {"success", None}
            if isinstance(duration, (int, float)):
                durations.append(float(duration))
            if row.get("cache_hit"):
                cache_hits += 1
            if row.get("retry_count"):
                retries += 1
            if is_error:
                errors += 1

            agent = row.get("agent") or "unknown"
            bucket = by_agent[agent]
            bucket["requests"] += 1
            if row.get("cache_hit"):
                bucket["cache_hits"] += 1
            if is_error:
                bucket["errors"] += 1
            if isinstance(duration, (int, float)):
                bucket["durations"].append(float(duration))

        by_agent_list = [
            {
                "agent": agent,
                "requests": bucket["requests"],
                "cache_hits": bucket["cache_hits"],
                "errors": bucket["errors"],
                "avg_duration_ms": round(
                    sum(bucket["durations"]) / len(bucket["durations"]), 1
                )
                if bucket["durations"]
                else 0.0,
            }
            for agent, bucket in by_agent.items()
        ]

        return UsageStats(
            requests_total=total,
            requests_today=today_count,
            avg_duration_ms=round(sum(durations) / len(durations), 1) if durations else 0.0,
            cache_hit_rate=round(cache_hits / total, 3) if total else 0.0,
            retry_rate=round(retries / total, 3) if total else 0.0,
            error_rate=round(errors / total, 3) if total else 0.0,
            by_agent=by_agent_list,
        )


_usage_stats_service: UsageStatsService | None = None


def get_usage_stats_service() -> UsageStatsService:
    global _usage_stats_service
    if _usage_stats_service is None:
        _usage_stats_service = UsageStatsService()
    return _usage_stats_service
