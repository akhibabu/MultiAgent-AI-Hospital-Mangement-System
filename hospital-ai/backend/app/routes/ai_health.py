"""
`GET /ai/health` — provider-agnostic AI infrastructure health check.

Distinct from the plain liveness probe at `/health`: this reports on the AI
*fleet*. With automatic failover, "is Groq up?" is the wrong question — the
system is healthy as long as *some* provider can serve a request. So `status`
describes the fleet:

    healthy      at least one provider is configured and in rotation
    degraded     providers are configured but every one is cooling down
    unavailable  no provider is configured at all

Public (no auth) so it can be wired into uptime tooling alongside `/health`,
and therefore deliberately credential-free: it reports which providers exist
and whether they hold a key, never the key itself.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.ai.orchestrator.load_balancer import get_load_balancer
from app.ai.orchestrator.provider_health_monitor import get_health_monitor
from app.ai.orchestrator.provider_router import get_provider_router
from app.ai.orchestrator.router import get_model_router
from app.ai.orchestrator.services.usage_stats_service import get_usage_stats_service
from app.config import get_settings
from app.schemas.ai_orchestrator import AIHealthOut, AIProviderHealthSummaryOut

router = APIRouter(prefix="/ai", tags=["ai-health"])


@router.get(
    "/health",
    response_model=AIHealthOut,
    summary="AI infrastructure health — provider fleet, failover chain, latency",
)
def get_ai_health() -> AIHealthOut:
    settings = get_settings()
    checked_at = datetime.now(timezone.utc).isoformat()
    failover_enabled = getattr(settings, "ai_failover_enabled", True)

    try:
        provider_router = get_provider_router()
        model_router = get_model_router()
        monitor = get_health_monitor()
        fleet = provider_router.fleet
    except Exception as exc:  # noqa: BLE001 - health must never 500
        return AIHealthOut(
            provider="unknown",
            status="unavailable",
            connected=False,
            error=str(exc),
            checked_at=checked_at,
        )

    chain = [c.name for c in get_load_balancer().select()]
    primary = chain[0] if chain else provider_router.default_provider_name()

    summaries = []
    healthy_count = 0
    configured_count = 0
    for config in fleet.ordered():
        health = monitor.snapshot(config.name)
        in_chain = config.name in chain
        if config.configured:
            configured_count += 1
        state = health["status"] if config.configured else "not_configured"
        if config.configured and state == "healthy":
            healthy_count += 1
        summaries.append(
            AIProviderHealthSummaryOut(
                provider=config.name,
                status=state,
                configured=config.configured,
                in_failover_chain=in_chain,
                failover_position=chain.index(config.name) + 1 if in_chain else None,
                current_model=model_router.routing_table(config.name).get("diagnosis", ""),
                avg_latency_ms=health["avg_latency_ms"],
                success_rate=health["success_rate"],
                quota_exhausted=health["quota_exhausted"],
                last_error_reason=health.get("last_error_reason"),
            )
        )

    # Only the primary is probed over the network — a public health endpoint
    # must not fan out one request into N provider round-trips.
    error = None
    provider_base_url = ""
    available_models: list[str] = []
    connected = False
    models = model_router.routing_table(primary)
    if chain:
        try:
            provider = provider_router.resolve(primary)
            provider_base_url = getattr(provider, "base_url", "") or ""
            primary_model = next((m for m in models.values() if m), "")
            connected, error = (
                provider.health_check(primary_model) if primary_model else (False, None)
            )
            available_models = provider.list_models()
        except Exception as exc:  # noqa: BLE001
            connected, error = False, str(exc)

    if configured_count == 0:
        status_text = "unavailable"
        error = error or (
            "No AI provider is configured. Set GROQ_API_KEY, GEMINI_API_KEY, "
            "OPENROUTER_API_KEY, or HUGGINGFACE_API_KEY in backend/.env."
        )
    elif not chain:
        # Configured, but every provider is currently in cooldown.
        status_text = "degraded"
    elif connected or healthy_count > 0:
        status_text = "healthy"
    else:
        status_text = "degraded"

    try:
        avg_latency_ms = get_usage_stats_service().get_stats(window=200).avg_duration_ms
    except Exception:  # noqa: BLE001
        avg_latency_ms = 0.0

    return AIHealthOut(
        provider=primary,
        status=status_text,
        connected=connected,
        provider_base_url=provider_base_url,
        available_models=available_models,
        current_models=models,
        avg_latency_ms=avg_latency_ms,
        error=error,
        checked_at=checked_at,
        failover_enabled=failover_enabled,
        failover_chain=chain,
        providers=summaries,
        healthy_provider_count=healthy_count,
        configured_provider_count=configured_count,
    )
