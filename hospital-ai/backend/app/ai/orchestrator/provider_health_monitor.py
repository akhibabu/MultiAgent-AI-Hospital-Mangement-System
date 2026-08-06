"""
ProviderHealthMonitor — live reliability state for every provider in the fleet.

Sits between the Provider Router and the actual providers:

    Provider Orchestrator -> Provider Router -> [Provider Health Monitor] -> Groq / Gemini / ...

Its job is to remember what just happened so the next request doesn't repeat
a known-bad call. Without it, a provider whose daily quota is exhausted would
be tried — and fail — on every single request for the rest of the day, adding
its timeout to every user-visible latency. With it, that provider is taken
out of rotation and the fleet quietly routes around it.

State machine (a circuit breaker with three states)
---------------------------------------------------
    HEALTHY  — recent calls succeeded; first choice for routing.
    WARNING  — degraded: some recent failures, or freshly out of cooldown
               (half-open). Still eligible, but ranked below healthy peers.
    OFFLINE  — in cooldown after hard failure (quota exhausted, bad API key)
               or after `failure_threshold` consecutive transient failures.
               Skipped entirely until the cooldown expires, then re-enters as
               WARNING so a single probe decides whether it is really back.

Cooldown length depends on *why* it failed, which is the whole point of the
error taxonomy: a daily quota gets the long `quota_cooldown_seconds` because
it genuinely will not recover in two minutes, while a network blip gets the
short `cooldown_seconds`.

All statistics are in-process and rolling (bounded deques), so this is O(1)
per call and safe to consult on every request. Nothing here performs network
I/O — live probing is `BaseAIProvider.health_check()`, called by the admin
dashboard, not by the request path.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

from app.ai.orchestrator.providers.config import HealthConfig, get_fleet_config
from app.ai.orchestrator.providers.errors import (
    AuthenticationError,
    ModelNotFoundError,
    QuotaExceededError,
    RateLimitError,
    reason_for,
)
from app.core.logging import get_logger

logger = get_logger("hospital_ai.orchestrator.health")

HEALTHY = "healthy"
WARNING = "warning"
OFFLINE = "offline"

#: How many failover/recovery events to keep for the admin dashboard.
_EVENT_HISTORY = 50


@dataclass
class ProviderEvent:
    """One notable transition, shown as 'Provider history' in the dashboard."""

    provider: str
    event: str  # offline | recovered | failover | quota_exhausted
    reason: str = ""
    detail: str = ""
    at: float = field(default_factory=time.time)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "event": self.event,
            "reason": self.reason,
            "detail": self.detail,
            "at": self.at,
        }


@dataclass
class ProviderStats:
    """Rolling reliability counters for a single provider."""

    provider: str
    sample_window: int = 50

    total_requests: int = 0
    total_successes: int = 0
    total_failures: int = 0
    consecutive_failures: int = 0

    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost_usd: float = 0.0

    #: Latency of recent *successful* calls, in ms.
    latencies: Deque[float] = field(default_factory=lambda: deque(maxlen=50))
    #: 1 = success, 0 = failure, for the rolling error rate.
    outcomes: Deque[int] = field(default_factory=lambda: deque(maxlen=50))

    last_success_at: Optional[float] = None
    last_failure_at: Optional[float] = None
    last_error: Optional[str] = None
    last_error_reason: Optional[str] = None

    #: Wall-clock time until which this provider is skipped. 0 = available.
    unavailable_until: float = 0.0
    quota_exhausted: bool = False
    #: How many times a request was routed away from this provider.
    times_skipped: int = 0

    def __post_init__(self) -> None:
        self.latencies = deque(maxlen=self.sample_window)
        self.outcomes = deque(maxlen=self.sample_window)

    @property
    def avg_latency_ms(self) -> float:
        return round(sum(self.latencies) / len(self.latencies), 1) if self.latencies else 0.0

    @property
    def success_rate(self) -> float:
        return round(sum(self.outcomes) / len(self.outcomes), 3) if self.outcomes else 1.0

    @property
    def failure_rate(self) -> float:
        return round(1.0 - self.success_rate, 3)

    @property
    def cooldown_remaining_seconds(self) -> float:
        return max(0.0, round(self.unavailable_until - time.time(), 1))


class ProviderHealthMonitor:
    """Thread-safe health/reliability registry for the provider fleet."""

    def __init__(self, config: Optional[HealthConfig] = None) -> None:
        self._config = config or get_fleet_config().health
        self._lock = threading.RLock()
        self._stats: Dict[str, ProviderStats] = {}
        self._events: Deque[ProviderEvent] = deque(maxlen=_EVENT_HISTORY)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------
    def record_success(
        self,
        provider: str,
        *,
        latency_ms: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        with self._lock:
            stats = self._get(provider)
            was_offline = stats.unavailable_until > time.time()

            stats.total_requests += 1
            stats.total_successes += 1
            stats.consecutive_failures = 0
            stats.latencies.append(float(latency_ms))
            stats.outcomes.append(1)
            stats.last_success_at = time.time()
            stats.total_prompt_tokens += max(0, prompt_tokens)
            stats.total_completion_tokens += max(0, completion_tokens)
            stats.total_cost_usd = round(stats.total_cost_usd + max(0.0, cost_usd), 6)

            # A success clears any cooldown — the provider demonstrably works.
            stats.unavailable_until = 0.0
            stats.quota_exhausted = False
            stats.last_error = None
            stats.last_error_reason = None

            if was_offline:
                self._events.append(
                    ProviderEvent(provider=provider, event="recovered", reason="probe_succeeded")
                )
                logger.info("Provider '%s' recovered and is back in rotation.", provider)

    def record_failure(self, provider: str, exc: BaseException) -> None:
        """Update health after a failed call and apply the right cooldown."""
        with self._lock:
            stats = self._get(provider)
            now = time.time()

            stats.total_requests += 1
            stats.total_failures += 1
            stats.consecutive_failures += 1
            stats.outcomes.append(0)
            stats.last_failure_at = now
            stats.last_error = str(exc)[:500]
            stats.last_error_reason = reason_for(exc)

            cooldown = self._cooldown_for(exc, stats)
            if cooldown > 0:
                stats.unavailable_until = now + cooldown
                event = "quota_exhausted" if isinstance(exc, QuotaExceededError) else "offline"
                stats.quota_exhausted = isinstance(exc, QuotaExceededError)
                self._events.append(
                    ProviderEvent(
                        provider=provider,
                        event=event,
                        reason=stats.last_error_reason or "",
                        detail=f"cooling down {int(cooldown)}s",
                    )
                )
                logger.warning(
                    "Provider '%s' taken out of rotation for %ss (%s): %s",
                    provider,
                    int(cooldown),
                    stats.last_error_reason,
                    stats.last_error,
                )

    def record_failover(self, *, from_provider: str, to_provider: str, reason: str) -> None:
        """Record that a request was rerouted — powers 'Provider history'."""
        with self._lock:
            self._get(from_provider).times_skipped += 1
            self._events.append(
                ProviderEvent(
                    provider=from_provider,
                    event="failover",
                    reason=reason,
                    detail=f"-> {to_provider}",
                )
            )

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------
    def is_available(self, provider: str) -> bool:
        """False while the provider is in cooldown. Consulted per request, so
        it must stay cheap and never touch the network."""
        with self._lock:
            return self._get(provider).unavailable_until <= time.time()

    def state(self, provider: str) -> str:
        with self._lock:
            return self._state(self._get(provider))

    def stats(self, provider: str) -> ProviderStats:
        with self._lock:
            return self._get(provider)

    def snapshot(self, provider: str) -> Dict[str, Any]:
        with self._lock:
            return self._snapshot(self._get(provider))

    def snapshots(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._snapshot(s) for s in self._stats.values()]

    def recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [e.as_dict() for e in list(self._events)[-limit:][::-1]]

    def reset(self, provider: Optional[str] = None) -> None:
        """Clear cooldowns/counters — used by the admin 'retry now' action and
        by tests. Without a name, resets the whole fleet."""
        with self._lock:
            if provider:
                self._stats.pop(provider.strip().lower(), None)
            else:
                self._stats.clear()
                self._events.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _get(self, provider: str) -> ProviderStats:
        key = (provider or "").strip().lower()
        if key not in self._stats:
            self._stats[key] = ProviderStats(
                provider=key, sample_window=self._config.sample_window
            )
        return self._stats[key]

    def _state(self, stats: ProviderStats) -> str:
        if stats.unavailable_until > time.time():
            return OFFLINE
        if stats.total_requests == 0:
            # Never called yet — optimistic, so a fresh process still tries
            # the configured primary first.
            return HEALTHY
        if (
            stats.consecutive_failures > 0
            or stats.failure_rate > self._config.warning_error_rate
        ):
            return WARNING
        return HEALTHY

    def _cooldown_for(self, exc: BaseException, stats: ProviderStats) -> float:
        """How long to skip this provider, based on why it failed."""
        if isinstance(exc, QuotaExceededError):
            # Honor the provider's own reset hint when it gives one, but never
            # go below the configured quota cooldown.
            retry_after = getattr(exc, "retry_after", None) or 0.0
            return max(self._config.quota_cooldown_seconds, float(retry_after))
        if isinstance(exc, (AuthenticationError, ModelNotFoundError)):
            # Configuration problems don't fix themselves mid-run; re-probing
            # every couple of minutes just adds latency to every request.
            return self._config.quota_cooldown_seconds
        if isinstance(exc, RateLimitError):
            retry_after = getattr(exc, "retry_after", None) or 0.0
            if retry_after > 0:
                return min(float(retry_after), self._config.cooldown_seconds)
        # Transient failures only trip the breaker once they repeat.
        if stats.consecutive_failures >= self._config.failure_threshold:
            return self._config.cooldown_seconds
        return 0.0

    def _snapshot(self, stats: ProviderStats) -> Dict[str, Any]:
        return {
            "provider": stats.provider,
            "status": self._state(stats),
            "total_requests": stats.total_requests,
            "total_successes": stats.total_successes,
            "total_failures": stats.total_failures,
            "consecutive_failures": stats.consecutive_failures,
            "success_rate": stats.success_rate,
            "failure_rate": stats.failure_rate,
            "avg_latency_ms": stats.avg_latency_ms,
            "prompt_tokens": stats.total_prompt_tokens,
            "completion_tokens": stats.total_completion_tokens,
            "total_tokens": stats.total_prompt_tokens + stats.total_completion_tokens,
            "estimated_cost_usd": round(stats.total_cost_usd, 6),
            "quota_exhausted": stats.quota_exhausted,
            "cooldown_remaining_seconds": stats.cooldown_remaining_seconds,
            "times_skipped": stats.times_skipped,
            "last_success_at": stats.last_success_at,
            "last_failure_at": stats.last_failure_at,
            "last_error": stats.last_error,
            "last_error_reason": stats.last_error_reason,
        }


_monitor: Optional[ProviderHealthMonitor] = None


def get_health_monitor() -> ProviderHealthMonitor:
    global _monitor
    if _monitor is None:
        _monitor = ProviderHealthMonitor()
    return _monitor
