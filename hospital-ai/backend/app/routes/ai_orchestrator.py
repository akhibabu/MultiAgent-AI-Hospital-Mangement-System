"""
AI Orchestrator admin API — backs the frontend "AI Infrastructure" dashboard.

Read endpoints expose the provider fleet, its live health, usage statistics,
and recent interaction logs. Write endpoints are the operational levers an
administrator needs during an incident: clear a provider's cooldown, reload
`providers.yaml` without a restart, drop stale cached answers, and cancel a
runaway request.

Every response is credential-free by construction — `ProviderConfig.redacted()`
reports only *whether* a key is present, never its value.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.ai.orchestrator.cache_manager import get_cache_manager
from app.ai.orchestrator.load_balancer import get_load_balancer
from app.ai.orchestrator.provider_health_monitor import get_health_monitor
from app.ai.orchestrator.provider_orchestrator import get_provider_orchestrator
from app.ai.orchestrator.provider_router import get_provider_router
from app.ai.orchestrator.providers.config import reload_fleet_config
from app.ai.orchestrator.request_queue import get_request_queue
from app.ai.orchestrator.router import get_model_router
from app.ai.orchestrator.services.usage_stats_service import (
    UsageStatsService,
    get_usage_stats_service,
)
from app.auth.dependencies import CurrentUser
from app.config import get_settings
from app.schemas.ai_orchestrator import (
    AgentUsageOut,
    CacheInvalidationOut,
    CacheStatsOut,
    InteractionLogOut,
    ModelHealthOut,
    OrchestratorLogsOut,
    OrchestratorStatsOut,
    OrchestratorStatusOut,
    ProviderFleetOut,
    QueueStatusOut,
)

router = APIRouter(prefix="/ai/orchestrator", tags=["ai-orchestrator"])


@router.get(
    "/status",
    response_model=OrchestratorStatusOut,
    summary="Active provider, failover chain, model routing, and live model health",
)
def get_orchestrator_status(_current_user: CurrentUser) -> OrchestratorStatusOut:
    settings = get_settings()
    provider_router = get_provider_router()
    model_router = get_model_router()
    balancer = get_load_balancer()

    chain = [c.name for c in balancer.select()]
    primary = chain[0] if chain else provider_router.default_provider_name()
    models = model_router.routing_table(primary)

    # Live model availability is only checked for the primary: probing every
    # provider on every dashboard poll would be several network round-trips
    # per refresh. Fallback health comes from the health monitor instead.
    model_health = []
    try:
        provider = provider_router.resolve(primary)
    except Exception as exc:  # noqa: BLE001 - status must never 500
        provider = None
        probe_error = str(exc)
    else:
        probe_error = None

    for agent, model in models.items():
        if not model:
            continue
        if provider is None:
            available, error = False, probe_error
        else:
            try:
                available, error = provider.health_check(model)
            except Exception as exc:  # noqa: BLE001
                available, error = False, str(exc)
        model_health.append(
            ModelHealthOut(
                agent=agent,
                provider=primary,
                model=model,
                available=available,
                error=error,
            )
        )

    return OrchestratorStatusOut(
        provider=primary,
        provider_base_url=getattr(provider, "base_url", "") or "",
        available_providers=provider_router.available_providers(),
        failover_chain=chain,
        load_balancer_strategy=balancer.strategy,
        failover_enabled=getattr(settings, "ai_failover_enabled", True),
        models=models,
        model_health=model_health,
        cache_ttl_seconds=settings.ai_cache_ttl_seconds,
        max_retries=settings.ai_max_retries,
        temperature=settings.ai_temperature,
        max_tokens=settings.ai_max_tokens,
    )


@router.get(
    "/providers",
    response_model=ProviderFleetOut,
    summary="Provider fleet: configuration, priority, live health, and failover history",
)
def get_provider_fleet(_current_user: CurrentUser) -> ProviderFleetOut:
    provider_router = get_provider_router()
    fleet = provider_router.fleet
    settings = get_settings()

    return ProviderFleetOut(
        strategy=get_load_balancer().strategy,
        failover_enabled=getattr(settings, "ai_failover_enabled", True),
        max_providers_per_request=fleet.routing.max_providers_per_request,
        config_source=fleet.source_path,
        config_error=fleet.load_error,
        providers=get_provider_orchestrator().fleet_snapshot(),
        events=get_health_monitor().recent_events(limit=25),
    )


@router.post(
    "/providers/{provider_name}/reset",
    response_model=ProviderFleetOut,
    summary="Clear a provider's cooldown and put it back in rotation",
)
def reset_provider_health(
    provider_name: str, _current_user: CurrentUser
) -> ProviderFleetOut:
    """Used when the underlying cause was fixed out-of-band — a quota reset
    early, or a corrected API key — so an administrator doesn't have to wait
    out the cooldown or restart the API."""
    provider_router = get_provider_router()
    if provider_router.config_for(provider_name) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_name}' is not declared in providers.yaml.",
        )
    get_health_monitor().reset(provider_name)
    return get_provider_fleet(_current_user)


@router.post(
    "/providers/reload",
    response_model=ProviderFleetOut,
    summary="Re-read providers.yaml and rebuild the fleet without a restart",
)
def reload_providers(_current_user: CurrentUser) -> ProviderFleetOut:
    fleet = reload_fleet_config()
    get_provider_router().reload(fleet)
    return get_provider_fleet(_current_user)


@router.get(
    "/queue",
    response_model=QueueStatusOut,
    summary="Request queue: active/queued AI requests, concurrency, and progress",
)
def get_queue_status(_current_user: CurrentUser) -> QueueStatusOut:
    return QueueStatusOut(**get_request_queue().snapshot())


@router.post(
    "/queue/{request_id}/cancel",
    response_model=QueueStatusOut,
    summary="Cancel a queued or running AI request",
)
def cancel_queued_request(request_id: str, _current_user: CurrentUser) -> QueueStatusOut:
    if not get_request_queue().cancel(request_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active or queued AI request with id '{request_id}'.",
        )
    return QueueStatusOut(**get_request_queue().snapshot())


@router.get(
    "/cache",
    response_model=CacheStatsOut,
    summary="AI response cache statistics",
)
def get_cache_stats(_current_user: CurrentUser) -> CacheStatsOut:
    return CacheStatsOut(**get_cache_manager().stats())


@router.delete(
    "/cache",
    response_model=CacheInvalidationOut,
    summary="Invalidate cached AI responses (all, by agent, or by patient)",
)
def invalidate_cache(
    _current_user: CurrentUser,
    agent: str = Query(default="", description="Invalidate one agent's cached responses"),
    patient_id: str = Query(
        default="",
        description=(
            "Invalidate every cached AI response for one patient. Use after new "
            "clinical data lands — the patient's context changed, so cached "
            "answers derived from the old context are stale."
        ),
    ),
) -> CacheInvalidationOut:
    cache = get_cache_manager()
    if patient_id:
        return CacheInvalidationOut(
            removed=cache.invalidate_patient(patient_id), scope=f"patient:{patient_id}"
        )
    if agent:
        return CacheInvalidationOut(
            removed=cache.invalidate_agent(agent), scope=f"agent:{agent}"
        )
    return CacheInvalidationOut(removed=cache.clear(), scope="all")


@router.get(
    "/stats",
    response_model=OrchestratorStatsOut,
    summary="Aggregated usage statistics (requests, latency, cache/retry rates)",
)
def get_orchestrator_stats(
    _current_user: CurrentUser,
    service: Annotated[UsageStatsService, Depends(get_usage_stats_service)],
    window: int = Query(default=1000, ge=1, le=5000),
) -> OrchestratorStatsOut:
    stats = service.get_stats(window=window)
    return OrchestratorStatsOut(
        requests_total=stats.requests_total,
        requests_today=stats.requests_today,
        avg_duration_ms=stats.avg_duration_ms,
        cache_hit_rate=stats.cache_hit_rate,
        retry_rate=stats.retry_rate,
        error_rate=stats.error_rate,
        by_agent=[AgentUsageOut(**row) for row in stats.by_agent],
    )


@router.get(
    "/logs",
    response_model=OrchestratorLogsOut,
    summary="Recent AI Orchestrator interaction logs",
)
def get_orchestrator_logs(
    _current_user: CurrentUser,
    service: Annotated[UsageStatsService, Depends(get_usage_stats_service)],
    limit: int = Query(default=50, ge=1, le=200),
) -> OrchestratorLogsOut:
    logs = service.get_recent_logs(limit=limit)
    return OrchestratorLogsOut(logs=[InteractionLogOut.model_validate(row) for row in logs])
