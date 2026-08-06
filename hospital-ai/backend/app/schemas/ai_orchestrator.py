"""API schemas for the AI Orchestrator admin dashboard endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OrchestratorDebugInfoOut(BaseModel):
    """
    Per-call developer-mode debug info, echoed on every AI Agent's
    `*StartResponse` (`ai_debug: List[OrchestratorDebugInfoOut]`) so the
    frontend Developer Mode panel can show exactly what happened for each
    orchestrator call made during that pipeline run.
    """

    agent: str
    task: str
    #: Provider that actually answered — may differ from `primary_provider`.
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
    estimated_cost_usd: float = 0.0
    # Failover visibility
    primary_provider: str = ""
    fallback_used: bool = False
    fallback_reason: str = ""
    attempts: List[Dict[str, Any]] = Field(default_factory=list)
    # Token optimization + queueing
    context_compression: Dict[str, Any] = Field(default_factory=dict)
    queue_wait_ms: int = 0
    created_at: str = ""


class ModelHealthOut(BaseModel):
    agent: str
    provider: str
    model: str
    available: bool
    error: Optional[str] = None


class OrchestratorStatusOut(BaseModel):
    #: Provider currently first in the failover chain.
    provider: str
    provider_base_url: str = ""
    available_providers: List[str] = Field(default_factory=list)
    #: Ordered failover chain: [primary, first fallback, ...].
    failover_chain: List[str] = Field(default_factory=list)
    load_balancer_strategy: str = "priority"
    failover_enabled: bool = True
    models: Dict[str, str] = Field(default_factory=dict)
    model_health: List[ModelHealthOut] = Field(default_factory=list)
    cache_ttl_seconds: int = 0
    max_retries: int = 0
    temperature: float = 0.0
    max_tokens: int = 0


# ---------------------------------------------------------------------------
# Provider fleet
# ---------------------------------------------------------------------------
class ProviderCapabilitiesOut(BaseModel):
    streaming: bool = False
    vision: bool = False
    long_context: bool = False


class ProviderPricingOut(BaseModel):
    """USD per 1M tokens. Estimates for the dashboard, never billing."""

    input_per_1m: float = 0.0
    output_per_1m: float = 0.0


class ProviderLimitsOut(BaseModel):
    """Single-request size ceiling declared in `providers.yaml`.

    `max_request_tokens` bounds `prompt + reserved completion` together, so a
    large `MAX_TOKENS` reduces the usable prompt one-for-one. `0` means the
    provider has no declared limit.
    """

    max_request_tokens: int = 0
    min_completion_tokens: int = 0


class ProviderHealthOut(BaseModel):
    """Live reliability state from the in-process health monitor."""

    provider: str = ""
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


class ProviderFleetEntryOut(BaseModel):
    """One provider's configuration + live health.

    API keys are never included — only `has_api_key`, so the UI can tell a
    developer which credential is missing without the secret leaving the
    backend.
    """

    name: str
    enabled: bool = False
    priority: int = 100
    configured: bool = False
    has_api_key: bool = False
    requires_api_key: bool = True
    base_url: str = ""
    console_url: str = ""
    timeout_seconds: float = 0.0
    models: Dict[str, str] = Field(default_factory=dict)
    capabilities: ProviderCapabilitiesOut = Field(default_factory=ProviderCapabilitiesOut)
    pricing: ProviderPricingOut = Field(default_factory=ProviderPricingOut)
    limits: ProviderLimitsOut = Field(default_factory=ProviderLimitsOut)
    health: ProviderHealthOut = Field(default_factory=ProviderHealthOut)
    in_failover_chain: bool = False
    failover_position: Optional[int] = None


class ProviderEventOut(BaseModel):
    """One provider state transition, for the 'Provider history' panel."""

    provider: str
    event: str  # offline | recovered | failover | quota_exhausted
    reason: str = ""
    detail: str = ""
    at: float = 0.0


class ProviderFleetOut(BaseModel):
    strategy: str = "priority"
    failover_enabled: bool = True
    max_providers_per_request: int = 4
    config_source: str = ""
    config_error: Optional[str] = None
    providers: List[ProviderFleetEntryOut] = Field(default_factory=list)
    events: List[ProviderEventOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Request queue
# ---------------------------------------------------------------------------
class QueuedRequestOut(BaseModel):
    id: str
    agent: str
    task: str = ""
    priority: str = "normal"
    patient_id: str = ""
    state: str = "queued"
    stage: str = ""
    percent: float = 0.0
    wait_ms: int = 0
    running_ms: int = 0
    enqueued_at: float = 0.0


class QueueStatusOut(BaseModel):
    max_concurrent: int = 0
    active: int = 0
    queued: int = 0
    completed: int = 0
    cancelled: int = 0
    timed_out: int = 0
    failed: int = 0
    active_requests: List[QueuedRequestOut] = Field(default_factory=list)
    queued_requests: List[QueuedRequestOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
class CacheStatsOut(BaseModel):
    entries: int = 0
    ttl_seconds: int = 0
    max_entries: int = 0
    hits: int = 0
    misses: int = 0
    hit_rate: float = 0.0
    evictions: int = 0
    invalidations: int = 0
    entries_by_agent: Dict[str, int] = Field(default_factory=dict)
    category_ttl_seconds: Dict[str, int] = Field(default_factory=dict)


class CacheInvalidationOut(BaseModel):
    removed: int = 0
    scope: str = ""


class AgentUsageOut(BaseModel):
    agent: str
    requests: int = 0
    cache_hits: int = 0
    errors: int = 0
    avg_duration_ms: float = 0.0


class OrchestratorStatsOut(BaseModel):
    requests_total: int = 0
    requests_today: int = 0
    avg_duration_ms: float = 0.0
    cache_hit_rate: float = 0.0
    retry_rate: float = 0.0
    error_rate: float = 0.0
    by_agent: List[AgentUsageOut] = Field(default_factory=list)


class InteractionLogOut(BaseModel):
    id: Optional[str] = None
    patient_id: Optional[str] = None
    agent: str
    task: str
    provider: str
    model: str
    status: str
    duration_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cache_hit: bool = False
    retry_count: int = 0
    error_message: Optional[str] = None
    # Present once migration 018 has been applied; optional so the dashboard
    # keeps working against a database that hasn't been migrated yet.
    primary_provider: Optional[str] = None
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    estimated_cost_usd: float = 0.0
    attempts: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: Optional[str] = None


class OrchestratorLogsOut(BaseModel):
    logs: List[InteractionLogOut] = Field(default_factory=list)


class AIProviderHealthSummaryOut(BaseModel):
    """One line per provider in the `GET /ai/health` fleet summary."""

    provider: str
    status: str = "unknown"  # healthy | warning | offline | not_configured
    configured: bool = False
    in_failover_chain: bool = False
    failover_position: Optional[int] = None
    current_model: str = ""
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    quota_exhausted: bool = False
    last_error_reason: Optional[str] = None


class AIHealthOut(BaseModel):
    """`GET /ai/health` — provider-agnostic AI infrastructure health check.

    `status` describes the *system*, not any one provider, which is the whole
    point of the failover design:

        healthy      at least one provider is configured and in rotation
        degraded     providers are configured but all are cooling down, or
                     the primary is down and only fallbacks remain
        unavailable  no provider is configured at all
    """

    provider: str
    status: str = "unknown"  # healthy | degraded | unavailable
    connected: bool = False
    provider_base_url: str = ""
    available_models: List[str] = Field(default_factory=list)
    current_models: Dict[str, str] = Field(default_factory=dict)
    avg_latency_ms: float = 0.0
    error: Optional[str] = None
    checked_at: str = ""
    # Fleet view
    failover_enabled: bool = True
    failover_chain: List[str] = Field(default_factory=list)
    providers: List[AIProviderHealthSummaryOut] = Field(default_factory=list)
    healthy_provider_count: int = 0
    configured_provider_count: int = 0
