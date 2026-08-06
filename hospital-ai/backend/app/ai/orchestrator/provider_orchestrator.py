"""
ProviderOrchestrator — high availability for the AI layer.

    AI Agent -> AI Orchestrator -> [Provider Orchestrator] -> Provider Router
             -> Provider Health Monitor -> Groq / Gemini / OpenRouter / HuggingFace

The `AIOrchestrator` owns *what* to ask (prompt, context, memory, parsing).
This class owns *who answers it*, and guarantees that a single provider
running out of quota, rate limiting, or going down never surfaces to an AI
Agent — let alone to a clinician looking at a patient record.

One call to `execute()` does all of this:

    1. Ask the LoadBalancer for an ordered candidate list, already filtered
       by health, credentials, and capability.
    2. Try the first candidate, retrying transient failures in place with
       exponential backoff (`RetryHandler`).
    3. On a non-transient failure — quota exhausted, bad key, model missing,
       provider down — record it with the health monitor and move to the next
       candidate *immediately*.
    4. Return the first successful completion, plus a full attempt timeline
       describing exactly which providers were tried, why each was abandoned,
       and which one ultimately answered.
    5. If every candidate fails, raise one `AllProvidersFailedError` carrying
       a clinician-safe summary message — never a raw API error.

The failure taxonomy in `providers/errors.py` is what makes step 3 correct:
retrying a bad API key on the same provider is pointless, and failing over on
a malformed request just reproduces the same error N times.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.ai.orchestrator.interfaces import ProviderCompletion, ProviderMessage
from app.ai.orchestrator.load_balancer import (
    LoadBalancer,
    RequestRequirements,
    get_load_balancer,
)
from app.ai.orchestrator.provider_health_monitor import (
    ProviderHealthMonitor,
    get_health_monitor,
)
from app.ai.orchestrator.provider_router import ProviderRouter, get_provider_router
from app.ai.orchestrator.providers.errors import (
    FailureAction,
    InvalidResponseError,
    classify,
    reason_for,
)
from app.ai.orchestrator.retry_handler import (
    ExponentialBackoffRetryHandler,
    get_retry_handler,
)
from app.core.logging import get_logger

logger = get_logger("hospital_ai.orchestrator.providers")


@dataclass
class ProviderAttempt:
    """One provider's turn at a request — the Developer Mode timeline row."""

    provider: str
    model: str
    outcome: str  # success | failed | skipped
    duration_ms: int = 0
    retries: int = 0
    reason: str = ""
    error: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "outcome": self.outcome,
            "duration_ms": self.duration_ms,
            "retries": self.retries,
            "reason": self.reason,
            "error": self.error,
        }


@dataclass
class ProviderExecution:
    """Result of a successful `execute()`, including how we got there."""

    completion: ProviderCompletion
    provider: str
    model: str
    attempts: List[ProviderAttempt] = field(default_factory=list)
    primary_provider: str = ""
    fallback_used: bool = False
    fallback_reason: str = ""
    total_retries: int = 0
    estimated_cost_usd: float = 0.0


class AllProvidersFailedError(RuntimeError):
    """Every provider in the chain failed.

    `args[0]` is deliberately written for a human operator: it names what was
    tried and what to do next. Raw provider payloads stay in `attempts` and in
    the application log, never in a UI toast.
    """

    def __init__(self, message: str, attempts: List[ProviderAttempt]) -> None:
        super().__init__(message)
        self.attempts = attempts


class ProviderOrchestrator:
    def __init__(
        self,
        *,
        router: Optional[ProviderRouter] = None,
        balancer: Optional[LoadBalancer] = None,
        monitor: Optional[ProviderHealthMonitor] = None,
        retry_handler: Optional[ExponentialBackoffRetryHandler] = None,
    ) -> None:
        self._router = router or get_provider_router()
        self._balancer = balancer or get_load_balancer()
        self._monitor = monitor or get_health_monitor()
        self._retry = retry_handler or get_retry_handler()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def execute(
        self,
        messages: List[ProviderMessage],
        *,
        agent: str,
        task: str = "",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        base_delay_ms: int = 500,
        pinned_provider: Optional[str] = None,
        requirements: Optional[RequestRequirements] = None,
        max_providers: Optional[int] = None,
    ) -> ProviderExecution:
        candidates = self._balancer.select(
            requirements=requirements, pinned=pinned_provider, limit=max_providers
        )
        if not candidates:
            raise AllProvidersFailedError(
                "No AI provider is configured. Set at least one provider API key "
                "(GROQ_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY, or "
                "HUGGINGFACE_API_KEY) in backend/.env and restart the API.",
                [],
            )

        attempts: List[ProviderAttempt] = []
        primary = candidates[0].name
        total_retries = 0

        for index, config in enumerate(candidates):
            provider_name = config.name
            model = self._model_for(agent, config)

            if not model:
                attempts.append(
                    ProviderAttempt(
                        provider=provider_name,
                        model="",
                        outcome="skipped",
                        reason="no_model_configured",
                        error=f"No model configured for agent '{agent}' on '{provider_name}'.",
                    )
                )
                continue

            try:
                provider = self._router.resolve(provider_name)
            except Exception as exc:  # noqa: BLE001 - a broken adapter must not stop failover
                attempts.append(
                    ProviderAttempt(
                        provider=provider_name,
                        model=model,
                        outcome="skipped",
                        reason="adapter_unavailable",
                        error=str(exc)[:300],
                    )
                )
                continue

            if not provider.is_available():
                attempts.append(
                    ProviderAttempt(
                        provider=provider_name,
                        model=model,
                        outcome="skipped",
                        reason="not_configured",
                        error=f"{provider_name} has no usable credentials.",
                    )
                )
                continue

            # Pre-flight size check. Providers meter `prompt + reserved
            # completion` against one limit, so a default 4 096-token
            # reservation can push an otherwise-fine prompt over the edge.
            # Shrinking the reservation is free; sending a request we can
            # already tell will be rejected costs a round trip and a
            # health-monitor failure against a provider that is working fine.
            prompt_tokens = self._estimate_prompt_tokens(provider, messages)
            limits = config.limits
            if not limits.fits(prompt_tokens):
                attempts.append(
                    ProviderAttempt(
                        provider=provider_name,
                        model=model,
                        outcome="skipped",
                        reason="context_length_exceeded",
                        error=(
                            f"Prompt needs ~{prompt_tokens} tokens; {provider_name} "
                            f"accepts {limits.max_request_tokens} per request."
                        ),
                    )
                )
                logger.info(
                    "Skipping '%s' for agent='%s' task='%s': prompt ~%d tokens exceeds "
                    "its %d-token request limit.",
                    provider_name,
                    agent,
                    task,
                    prompt_tokens,
                    limits.max_request_tokens,
                )
                continue

            effective_max_tokens = limits.completion_budget(prompt_tokens, max_tokens)
            if effective_max_tokens < max_tokens:
                logger.debug(
                    "Reduced completion budget for '%s' from %d to %d tokens to fit "
                    "its %d-token request limit (prompt ~%d).",
                    provider_name,
                    max_tokens,
                    effective_max_tokens,
                    limits.max_request_tokens,
                    prompt_tokens,
                )

            started = time.monotonic()
            try:
                completion, retries = self._retry.execute(
                    lambda p=provider, m=model, mt=effective_max_tokens: p.generate(
                        messages,
                        model=m,
                        temperature=temperature,
                        max_tokens=mt,
                        timeout=timeout,
                        agent=agent,
                        task=task,
                    ),
                    max_retries=max_retries,
                    base_delay_ms=base_delay_ms,
                )
                total_retries += retries

                if not provider.validate_response(completion):
                    raise InvalidResponseError(
                        f"{provider_name} returned an empty response.",
                        provider=provider_name,
                    )

                duration_ms = int((time.monotonic() - started) * 1000)
                cost = provider.estimate_cost(
                    completion.prompt_tokens, completion.completion_tokens
                )
                self._monitor.record_success(
                    provider_name,
                    latency_ms=duration_ms,
                    prompt_tokens=completion.prompt_tokens,
                    completion_tokens=completion.completion_tokens,
                    cost_usd=cost,
                )
                attempts.append(
                    ProviderAttempt(
                        provider=provider_name,
                        model=model,
                        outcome="success",
                        duration_ms=duration_ms,
                        retries=retries,
                    )
                )

                fallback_used = index > 0
                fallback_reason = ""
                if fallback_used:
                    fallback_reason = next(
                        (a.reason for a in attempts if a.outcome in {"failed", "skipped"}),
                        "primary_unavailable",
                    )
                    logger.info(
                        "AI request for agent='%s' task='%s' served by fallback provider "
                        "'%s' after '%s' failed (%s).",
                        agent,
                        task,
                        provider_name,
                        primary,
                        fallback_reason,
                    )

                return ProviderExecution(
                    completion=completion,
                    provider=provider_name,
                    model=completion.model or model,
                    attempts=attempts,
                    primary_provider=primary,
                    fallback_used=fallback_used,
                    fallback_reason=fallback_reason,
                    total_retries=total_retries,
                    estimated_cost_usd=cost,
                )

            except BaseException as exc:  # noqa: BLE001 - decided by classify()
                duration_ms = int((time.monotonic() - started) * 1000)
                action = classify(exc)
                reason = reason_for(exc)
                self._monitor.record_failure(provider_name, exc)
                attempts.append(
                    ProviderAttempt(
                        provider=provider_name,
                        model=model,
                        outcome="failed",
                        duration_ms=duration_ms,
                        reason=reason,
                        error=str(exc)[:300],
                    )
                )

                if action is FailureAction.FATAL:
                    # The request itself is invalid — every provider would
                    # reject it identically, so stop and say so clearly.
                    logger.error(
                        "Fatal AI request error on '%s' (%s): %s", provider_name, reason, exc
                    )
                    raise AllProvidersFailedError(
                        "The AI request was rejected as invalid and could not be "
                        f"processed ({reason}). This is a configuration or prompt "
                        "problem, not a provider outage.",
                        attempts,
                    ) from exc

                if index + 1 < len(candidates):
                    self._monitor.record_failover(
                        from_provider=provider_name,
                        to_provider=candidates[index + 1].name,
                        reason=reason,
                    )
                    logger.warning(
                        "Provider '%s' failed (%s) — failing over to '%s'.",
                        provider_name,
                        reason,
                        candidates[index + 1].name,
                    )

        raise AllProvidersFailedError(self._exhausted_message(attempts), attempts)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _model_for(self, agent: str, config) -> str:
        """Model this provider should use for this agent.

        Delegates to the ModelRouter so model selection stays in one place,
        and every provider in the failover chain still honors per-agent model
        routing — Groq's diagnosis model and Gemini's diagnosis model can
        differ without any agent knowing either exists.
        """
        from app.ai.orchestrator.router import get_model_router

        return get_model_router().resolve_for_provider(agent, config.name)

    @staticmethod
    def _estimate_prompt_tokens(provider, messages: List[ProviderMessage]) -> int:
        """Approximate tokens the prompt will cost on this provider.

        Uses the provider's own estimator so a tokenizer-aware adapter can be
        more accurate than the shared ~4-chars-per-token heuristic. The result
        only gates budget decisions, so erring slightly high is the safe
        direction and no exactness is required.
        """
        try:
            return sum(provider.estimate_tokens(m.content or "") for m in messages)
        except Exception:  # noqa: BLE001 - estimation must never fail a request
            return sum(len(m.content or "") for m in messages) // 4

    def prompt_budget_tokens(
        self,
        *,
        agent: str = "",
        pinned: Optional[str] = None,
        reserved_completion_tokens: int = 4096,
    ) -> int:
        """Largest prompt (in tokens) any currently-usable provider can hold.

        Lets the `AIOrchestrator` size context compression to the fleet it
        actually has, rather than to a fixed constant. Returns 0 when no
        candidate declares a limit, meaning "don't compress on my account".
        """
        try:
            candidates = self._balancer.select(pinned=pinned)
        except Exception:  # noqa: BLE001 - budgeting is advisory, never fatal
            return 0

        budgets = [
            c.limits.prompt_budget_tokens(reserved_completion_tokens)
            for c in candidates
            if c.limits.declared
        ]
        if not budgets or len(budgets) < len(candidates):
            # At least one candidate has no declared ceiling, so there is a
            # provider that can hold anything we send.
            return 0
        return max(budgets)

    @staticmethod
    def _exhausted_message(attempts: List[ProviderAttempt]) -> str:
        """Operator-facing summary. Deliberately free of raw API payloads."""
        if not attempts:
            return (
                "No AI provider was available to handle this request. Check the AI "
                "Infrastructure dashboard for provider health."
            )

        quota_hit = [a.provider for a in attempts if a.reason == "quota_exceeded"]
        auth_hit = [a.provider for a in attempts if a.reason == "invalid_api_key"]
        too_big = [a.provider for a in attempts if a.reason == "context_length_exceeded"]
        tried = ", ".join(dict.fromkeys(a.provider for a in attempts))

        # A request that no provider is large enough to hold is a different
        # problem from an outage, and has a different fix, so it gets its own
        # message rather than "add another key".
        if too_big and len(too_big) == len(attempts):
            return (
                f"This request is too large for every configured AI provider "
                f"(tried: {tried}). Configure a provider with a bigger request "
                "limit — Gemini's free tier is the usual choice — or reduce "
                "MAX_TOKENS in backend/.env to leave more room for the prompt."
            )

        parts = [f"Every configured AI provider failed for this request (tried: {tried})."]
        if too_big:
            parts.append(
                f"Request too large for: {', '.join(dict.fromkeys(too_big))}."
            )
        if quota_hit:
            parts.append(
                f"Quota exhausted on: {', '.join(dict.fromkeys(quota_hit))}. "
                "These reset on the provider's own schedule."
            )
        if auth_hit:
            parts.append(
                f"Invalid or missing API key on: {', '.join(dict.fromkeys(auth_hit))}."
            )
        parts.append(
            "Add another provider key in backend/.env (Gemini, OpenRouter, and "
            "HuggingFace all have free tiers) to keep the system available."
        )
        return " ".join(parts)

    # ------------------------------------------------------------------
    # Introspection for the admin dashboard
    # ------------------------------------------------------------------
    def fleet_snapshot(self) -> List[Dict[str, Any]]:
        """Config + live health for every declared provider, credentials
        redacted. Backs `GET /api/ai/orchestrator/providers`."""
        snapshots = {s["provider"]: s for s in self._monitor.snapshots()}
        chain = [p.name for p in self._router.fleet.failover_chain()]
        rows: List[Dict[str, Any]] = []
        for config in self._router.fleet.ordered():
            row = config.redacted()
            row["health"] = snapshots.get(
                config.name,
                {
                    "provider": config.name,
                    "status": "healthy" if config.configured else "offline",
                    "total_requests": 0,
                    "success_rate": 1.0,
                    "failure_rate": 0.0,
                    "avg_latency_ms": 0.0,
                    "quota_exhausted": False,
                    "cooldown_remaining_seconds": 0.0,
                },
            )
            row["in_failover_chain"] = config.name in chain
            row["failover_position"] = (
                chain.index(config.name) + 1 if config.name in chain else None
            )
            rows.append(row)
        return rows


_provider_orchestrator: Optional[ProviderOrchestrator] = None


def get_provider_orchestrator() -> ProviderOrchestrator:
    global _provider_orchestrator
    if _provider_orchestrator is None:
        _provider_orchestrator = ProviderOrchestrator()
    return _provider_orchestrator
