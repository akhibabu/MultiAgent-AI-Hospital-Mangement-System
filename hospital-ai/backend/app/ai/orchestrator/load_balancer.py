"""
LoadBalancer — decides the order in which providers are attempted.

The Provider Orchestrator asks for an ordered candidate list and then walks
it: first entry is the primary attempt, the rest are the failover chain. So
this class alone determines both "which provider serves this request" and
"who takes over when it fails" — there is no separate, divergent failover
ordering to keep in sync.

Selection happens in three layers, in this order:

1. **Eligibility.** Providers that aren't configured (no API key) or are
   excluded from failover are dropped. Providers currently in health-monitor
   cooldown are dropped too — that is what stops an exhausted Groq quota
   from adding a failed call to every request for the rest of the day.
2. **Capability.** If a request needs vision or long context, providers that
   can't do it are dropped. Declared in `providers.yaml`, so adding a
   vision-capable provider needs no code change.
3. **Strategy.** The survivors are ranked:

       priority       Configured `priority` order. Deterministic and cheapest
                      — always exhausts the free/fast provider first.
       round_robin    Rotate the starting point each request to spread load
                      evenly across providers and stretch free-tier quotas.
       least_latency  Fastest observed average latency first.
       least_errors   Highest observed success rate first.

   Health always outranks the strategy: a `healthy` provider is tried before
   a `warning` one no matter what the strategy says, because a degraded
   provider that happens to be fast is still a worse first choice.

If every provider is in cooldown the list is not left empty — the one whose
cooldown expires soonest is returned as a last-ditch probe, so the caller
produces a real provider error rather than a bare "nothing configured".
"""
from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass
from typing import List, Optional, Sequence

from app.ai.orchestrator.provider_health_monitor import (
    HEALTHY,
    OFFLINE,
    WARNING,
    ProviderHealthMonitor,
    get_health_monitor,
)
from app.ai.orchestrator.providers.config import FleetConfig, ProviderConfig, get_fleet_config
from app.core.logging import get_logger

logger = get_logger("hospital_ai.orchestrator.balancer")

STRATEGY_PRIORITY = "priority"
STRATEGY_ROUND_ROBIN = "round_robin"
STRATEGY_LEAST_LATENCY = "least_latency"
STRATEGY_LEAST_ERRORS = "least_errors"

SUPPORTED_STRATEGIES = (
    STRATEGY_PRIORITY,
    STRATEGY_ROUND_ROBIN,
    STRATEGY_LEAST_LATENCY,
    STRATEGY_LEAST_ERRORS,
)

#: Rank order for the health-first tier. Lower sorts earlier.
_HEALTH_RANK = {HEALTHY: 0, WARNING: 1, OFFLINE: 2}


@dataclass(frozen=True)
class RequestRequirements:
    """Capability constraints for a single request. Defaults to "no special
    needs", which every provider satisfies."""

    needs_vision: bool = False
    needs_long_context: bool = False
    needs_streaming: bool = False

    def satisfied_by(self, provider: ProviderConfig) -> bool:
        caps = provider.capabilities
        if self.needs_vision and not caps.vision:
            return False
        if self.needs_long_context and not caps.long_context:
            return False
        if self.needs_streaming and not caps.streaming:
            return False
        return True


class LoadBalancer:
    def __init__(
        self,
        fleet: Optional[FleetConfig] = None,
        monitor: Optional[ProviderHealthMonitor] = None,
        strategy: Optional[str] = None,
    ) -> None:
        self._fleet = fleet or get_fleet_config()
        self._monitor = monitor or get_health_monitor()
        configured = strategy or self._fleet.routing.strategy
        self._strategy = (
            configured if configured in SUPPORTED_STRATEGIES else STRATEGY_PRIORITY
        )
        if configured != self._strategy:
            logger.warning(
                "Unknown load balancer strategy '%s' — falling back to '%s'. Supported: %s",
                configured,
                self._strategy,
                ", ".join(SUPPORTED_STRATEGIES),
            )
        self._rotation = itertools.count()
        self._lock = threading.Lock()

    @property
    def strategy(self) -> str:
        return self._strategy

    def select(
        self,
        *,
        requirements: Optional[RequestRequirements] = None,
        pinned: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[ProviderConfig]:
        """Ordered candidates for one request: `[primary, *failover_chain]`.

        `pinned` (from `AI_PROVIDER`) expresses a *preference*, not a lock: it
        moves that provider to the front while the rest of the fleet stays
        behind it as fallbacks. Pinning a provider marked
        `exclude_from_failover` in `providers.yaml` — currently only `stub` —
        is the one exception, and returns that provider alone. That keeps
        `AI_PROVIDER=stub` a genuinely offline mode instead of silently
        reaching for the network on the second attempt.
        """
        requirements = requirements or RequestRequirements()

        if pinned:
            forced = self._fleet.get(pinned.strip().lower())
            if forced is not None and forced.exclude_from_failover:
                return [forced]

        candidates = [
            p
            for p in self._fleet.failover_chain()
            if requirements.satisfied_by(p)
        ]

        if not candidates:
            return self._pinned_only(pinned)

        available = [p for p in candidates if self._monitor.is_available(p.name)]
        if not available:
            # Whole fleet is cooling down. Probe whichever recovers soonest so
            # the caller surfaces a real provider error, not a config error.
            soonest = min(
                candidates,
                key=lambda p: self._monitor.stats(p.name).cooldown_remaining_seconds,
            )
            logger.warning(
                "Every AI provider is in cooldown — probing '%s' (%.0fs remaining).",
                soonest.name,
                self._monitor.stats(soonest.name).cooldown_remaining_seconds,
            )
            available = [soonest]

        ordered = self._rank(available)

        if pinned:
            pinned_key = pinned.strip().lower()
            forced = self._fleet.get(pinned_key)
            ordered = [p for p in ordered if p.name != pinned_key]
            if forced is not None:
                ordered.insert(0, forced)

        max_providers = limit or self._fleet.routing.max_providers_per_request
        return ordered[: max(1, max_providers)]

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------
    def _rank(self, providers: Sequence[ProviderConfig]) -> List[ProviderConfig]:
        health_rank = {
            p.name: _HEALTH_RANK.get(self._monitor.state(p.name), 1) for p in providers
        }

        if self._strategy == STRATEGY_LEAST_LATENCY:
            def key(p: ProviderConfig):
                stats = self._monitor.stats(p.name)
                # A provider with no samples yet sorts on its configured
                # priority rather than a fake 0ms latency.
                latency = stats.avg_latency_ms if stats.latencies else float("inf")
                return (health_rank[p.name], latency, p.priority)

        elif self._strategy == STRATEGY_LEAST_ERRORS:
            def key(p: ProviderConfig):
                stats = self._monitor.stats(p.name)
                return (health_rank[p.name], stats.failure_rate, p.priority)

        elif self._strategy == STRATEGY_ROUND_ROBIN:
            ordered = sorted(providers, key=lambda p: (health_rank[p.name], p.priority))
            with self._lock:
                offset = next(self._rotation) % len(ordered)
            return ordered[offset:] + ordered[:offset]

        else:  # STRATEGY_PRIORITY
            def key(p: ProviderConfig):
                return (health_rank[p.name], p.priority, p.name)

        return sorted(providers, key=key)

    def _pinned_only(self, pinned: Optional[str]) -> List[ProviderConfig]:
        """No provider satisfies the request. Fall back to an explicit pin if
        there is one (e.g. `AI_PROVIDER=stub` in an offline dev environment)."""
        if pinned:
            forced = self._fleet.get(pinned.strip().lower())
            if forced is not None:
                return [forced]
        return []


_balancer: Optional[LoadBalancer] = None


def get_load_balancer() -> LoadBalancer:
    global _balancer
    if _balancer is None:
        _balancer = LoadBalancer()
    return _balancer
