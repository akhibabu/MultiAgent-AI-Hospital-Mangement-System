"""Pydantic models shared across the AI Orchestrator subsystems."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    """One stored prompt/response pair from `ai_conversation_memory`."""

    id: Optional[str] = None
    patient_id: str
    agent: str
    task: str
    prompt_rendered: str = ""
    response_text: str = ""
    response_json: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    created_at: Optional[str] = None


class OrchestratorDebugInfo(BaseModel):
    """
    Per-call developer-mode debug info.

    Every agent's aggregate report attaches a list of these (one per
    orchestrator call made during that pipeline run) so the frontend
    "Developer Mode" panel can show exactly what happened without a
    separate debug endpoint.
    """

    agent: str
    task: str
    #: Provider that actually produced this response — not necessarily the
    #: one configured as primary, if failover kicked in.
    provider: str
    model: str
    prompt_name: str
    prompt_version: str = "1"
    processing_time_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    retry_count: int = 0
    cache_hit: bool = False
    raw_response: str = ""
    status: str = "success"
    error: Optional[str] = None
    # Best-effort USD estimate for this call (0.0 on cache hits, or when
    # pricing for the provider/model pair is unknown).
    estimated_cost_usd: float = 0.0

    # --- Failover visibility -------------------------------------------
    #: Provider the load balancer chose first for this request.
    primary_provider: str = ""
    #: True when `provider` != the primary, i.e. a fallback answered.
    fallback_used: bool = False
    #: Machine-readable reason the primary was abandoned (quota_exceeded,
    #: rate_limited, invalid_api_key, timeout, …).
    fallback_reason: str = ""
    #: One entry per provider attempted, in order — the Developer Mode
    #: execution timeline.
    attempts: List[Dict[str, Any]] = Field(default_factory=list)

    # --- Token optimization --------------------------------------------
    #: Before/after sizes from the ContextCompressor.
    context_compression: Dict[str, Any] = Field(default_factory=dict)
    #: How long this request waited for a queue slot.
    queue_wait_ms: int = 0

    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class AIResponse(BaseModel):
    """Structured result returned by `AIOrchestrator.run()`."""

    data: Dict[str, Any] = Field(default_factory=dict)
    debug: OrchestratorDebugInfo


class AgentUsageBreakdown(BaseModel):
    agent: str
    requests: int = 0
    cache_hits: int = 0
    errors: int = 0
    avg_duration_ms: float = 0.0


class UsageStats(BaseModel):
    """Aggregated usage statistics for the Admin / AI Orchestrator dashboard."""

    requests_total: int = 0
    requests_today: int = 0
    avg_duration_ms: float = 0.0
    cache_hit_rate: float = 0.0
    retry_rate: float = 0.0
    error_rate: float = 0.0
    by_agent: List[Dict[str, Any]] = Field(default_factory=list)


class ModelHealth(BaseModel):
    agent: str
    provider: str
    model: str
    available: bool = False
    error: Optional[str] = None


class ProviderHealth(BaseModel):
    """Live reliability state for one provider, from the health monitor."""

    provider: str
    status: str = "healthy"  # healthy | warning | offline
    total_requests: int = 0
    total_successes: int = 0
    total_failures: int = 0
    consecutive_failures: int = 0
    success_rate: float = 1.0
    failure_rate: float = 0.0
    avg_latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    quota_exhausted: bool = False
    cooldown_remaining_seconds: float = 0.0
    times_skipped: int = 0
    last_success_at: Optional[float] = None
    last_failure_at: Optional[float] = None
    last_error: Optional[str] = None
    last_error_reason: Optional[str] = None


class OrchestratorStatus(BaseModel):
    #: The provider currently first in the failover chain.
    provider: str
    provider_base_url: str = ""
    available_providers: List[str] = Field(default_factory=list)
    #: Ordered failover chain: [primary, first fallback, ...].
    failover_chain: List[str] = Field(default_factory=list)
    load_balancer_strategy: str = "priority"
    failover_enabled: bool = True
    models: Dict[str, str] = Field(default_factory=dict)
    model_health: List[ModelHealth] = Field(default_factory=list)
    cache_ttl_seconds: int = 0
    max_retries: int = 0
