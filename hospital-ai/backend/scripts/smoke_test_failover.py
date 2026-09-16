"""
Smoke test: automatic provider failover.

Exercises the Provider Orchestrator against fake in-memory providers, so it
runs offline, in CI, and costs nothing. It verifies the behavior the whole
multi-provider redesign exists to guarantee:

  1. A healthy primary serves the request, no failover.
  2. A quota-exhausted primary transparently fails over to the next provider.
  3. A transient (5xx) failure is retried on the *same* provider, not failed over.
  4. An invalid API key fails over immediately without burning retries.
  5. A malformed request is FATAL — no failover, no retry storm.
  6. A quota-exhausted provider is removed from rotation for later requests
     (the health monitor circuit breaker), so it isn't tried again.
  7. When every provider is down the caller gets one actionable error.
  8. An oversized request ("HTTP 413 request too large") fails over rather
     than being treated as fatal — it is one provider's limit, not a bad
     prompt.
  9. A prompt too big for the primary is routed to a roomier provider
     *before* the request is sent, instead of burning a round trip.
 10. The completion reservation shrinks to fit a provider's request limit,
     since providers meter `prompt + max_tokens` against one ceiling.
 11. A prompt no provider can hold produces a size-specific error, not a
     generic "everything failed".

Run from `backend/`:

    python scripts/smoke_test_failover.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.orchestrator.interfaces import (  # noqa: E402
    BaseAIProvider,
    ProviderCompletion,
    ProviderMessage,
)
from app.ai.orchestrator.load_balancer import LoadBalancer  # noqa: E402
from app.ai.orchestrator.provider_health_monitor import (  # noqa: E402
    ProviderHealthMonitor,
)
from app.ai.orchestrator.provider_orchestrator import (  # noqa: E402
    AllProvidersFailedError,
    ProviderOrchestrator,
)
from app.ai.orchestrator.provider_router import ProviderRouter  # noqa: E402
from app.ai.orchestrator.providers.config import (  # noqa: E402
    FleetConfig,
    HealthConfig,
    ProviderCapabilities,
    ProviderConfig,
    ProviderLimits,
    RoutingConfig,
)
from app.ai.orchestrator.providers.errors import (  # noqa: E402
    AuthenticationError,
    ContextLengthExceededError,
    MalformedRequestError,
    ProviderUnavailableError,
    QuotaExceededError,
)
from app.ai.orchestrator.retry_handler import ExponentialBackoffRetryHandler  # noqa: E402

MESSAGES = [ProviderMessage(role="user", content="hello")]

_failures: List[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  [PASS] {label}")
    else:
        print(f"  [FAIL] {label}{(' - ' + detail) if detail else ''}")
        _failures.append(label)


class FakeProvider(BaseAIProvider):
    """Provider that either answers or raises a scripted error."""

    def __init__(self, name: str, error: Optional[BaseException] = None) -> None:
        self.name = name
        self.error = error
        self.calls = 0
        self.config = None

    def generate(self, messages, *, model, temperature=0.2, max_tokens=4096,
                 timeout=None, agent="", task="") -> ProviderCompletion:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return ProviderCompletion(
            content='{"ok": true}',
            provider=self.name,
            model=model,
            prompt_tokens=10,
            completion_tokens=5,
        )

    def is_available(self) -> bool:
        return True


class RecordingProvider(FakeProvider):
    """Succeeds, and remembers the `max_tokens` it was actually asked for."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.last_max_tokens = 0

    def generate(self, messages, *, model, temperature=0.2, max_tokens=4096,
                 timeout=None, agent="", task="") -> ProviderCompletion:
        self.last_max_tokens = max_tokens
        return super().generate(
            messages, model=model, temperature=temperature, max_tokens=max_tokens,
            timeout=timeout, agent=agent, task=task,
        )


class FlakyProvider(FakeProvider):
    """Fails `fail_times` times with a transient error, then succeeds."""

    def __init__(self, name: str, fail_times: int) -> None:
        super().__init__(name)
        self.fail_times = fail_times

    def generate(self, messages, *, model, temperature=0.2, max_tokens=4096,
                 timeout=None, agent="", task="") -> ProviderCompletion:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise ProviderUnavailableError(f"{self.name} 503", provider=self.name)
        return ProviderCompletion(
            content='{"ok": true}', provider=self.name, model=model,
            prompt_tokens=10, completion_tokens=5,
        )


def build(
    providers: dict[str, BaseAIProvider],
    limits: Optional[dict[str, ProviderLimits]] = None,
) -> tuple[ProviderOrchestrator, ProviderHealthMonitor]:
    """Wire a Provider Orchestrator over the given fake providers."""
    limits = limits or {}
    fleet = FleetConfig(
        routing=RoutingConfig(strategy="priority", max_providers_per_request=5),
        # Trip the breaker on the first failure so test 6 is deterministic.
        health=HealthConfig(
            failure_threshold=1,
            warning_error_rate=0.25,
            cooldown_seconds=60.0,
            quota_cooldown_seconds=900.0,
            sample_window=10,
        ),
        providers={
            name: ProviderConfig(
                name=name,
                enabled=True,
                priority=index + 1,
                api_key="test-key",
                base_url=f"https://{name}.test",
                models={"default": f"{name}-model"},
                capabilities=ProviderCapabilities(streaming=True, long_context=True),
                limits=limits.get(name, ProviderLimits()),
            )
            for index, name in enumerate(providers)
        },
    )
    router = ProviderRouter(fleet=fleet)
    for name, instance in providers.items():
        instance.config = fleet.get(name)
        router.register(name, (lambda inst: lambda cfg: inst)(instance))

    monitor = ProviderHealthMonitor(fleet.health)
    balancer = LoadBalancer(fleet=fleet, monitor=monitor)
    orchestrator = ProviderOrchestrator(
        router=router,
        balancer=balancer,
        monitor=monitor,
        # base_delay_ms is passed per-call; keep retries instant in tests.
        retry_handler=ExponentialBackoffRetryHandler(),
    )
    return orchestrator, monitor


def run(orchestrator: ProviderOrchestrator, **kwargs):
    return orchestrator.execute(
        MESSAGES, agent="diagnosis", task="smoke", base_delay_ms=1, **kwargs
    )


def main() -> int:
    print("\n1. Healthy primary serves the request")
    primary = FakeProvider("groq")
    backup = FakeProvider("gemini")
    orch, _ = build({"groq": primary, "gemini": backup})
    result = run(orch)
    check("served by primary", result.provider == "groq", result.provider)
    check("no fallback flagged", result.fallback_used is False)
    check("backup never called", backup.calls == 0, f"calls={backup.calls}")

    print("\n2. Quota-exhausted primary fails over to the next provider")
    primary = FakeProvider("groq", QuotaExceededError("daily tokens gone", provider="groq"))
    backup = FakeProvider("gemini")
    orch, monitor = build({"groq": primary, "gemini": backup})
    result = run(orch)
    check("served by fallback", result.provider == "gemini", result.provider)
    check("fallback flagged", result.fallback_used is True)
    check("reason recorded", result.fallback_reason == "quota_exceeded", result.fallback_reason)
    check("primary tried exactly once", primary.calls == 1, f"calls={primary.calls}")
    check("timeline has 2 attempts", len(result.attempts) == 2, str(len(result.attempts)))

    print("\n3. Transient 5xx is retried on the SAME provider (no failover)")
    flaky = FlakyProvider("groq", fail_times=2)
    backup = FakeProvider("gemini")
    orch, _ = build({"groq": flaky, "gemini": backup})
    result = run(orch, max_retries=3)
    check("still served by primary", result.provider == "groq", result.provider)
    check("retried twice then succeeded", flaky.calls == 3, f"calls={flaky.calls}")
    check("retry count reported", result.total_retries == 2, str(result.total_retries))
    check("backup never called", backup.calls == 0, f"calls={backup.calls}")

    print("\n4. Invalid API key fails over immediately, without retrying")
    primary = FakeProvider("groq", AuthenticationError("bad key", provider="groq"))
    backup = FakeProvider("gemini")
    orch, _ = build({"groq": primary, "gemini": backup})
    result = run(orch, max_retries=3)
    check("served by fallback", result.provider == "gemini", result.provider)
    check("primary not retried", primary.calls == 1, f"calls={primary.calls}")
    check("reason recorded", result.fallback_reason == "invalid_api_key", result.fallback_reason)

    print("\n5. Malformed request is FATAL - no failover, no retry storm")
    primary = FakeProvider("groq", MalformedRequestError("bad payload", provider="groq"))
    backup = FakeProvider("gemini")
    orch, _ = build({"groq": primary, "gemini": backup})
    try:
        run(orch, max_retries=3)
        check("raises AllProvidersFailedError", False, "no exception raised")
    except AllProvidersFailedError as exc:
        check("raises AllProvidersFailedError", True)
        check("primary called once", primary.calls == 1, f"calls={primary.calls}")
        check("backup NOT called", backup.calls == 0, f"calls={backup.calls}")
        check("message is actionable", "not a provider outage" in str(exc), str(exc)[:80])

    print("\n6. Circuit breaker keeps a dead provider out of rotation")
    primary = FakeProvider("groq", QuotaExceededError("daily tokens gone", provider="groq"))
    backup = FakeProvider("gemini")
    orch, monitor = build({"groq": primary, "gemini": backup})
    run(orch)
    calls_after_first = primary.calls
    run(orch)
    run(orch)
    check("primary skipped on later requests", primary.calls == calls_after_first,
          f"calls={primary.calls}")
    check("backup served all three", backup.calls == 3, f"calls={backup.calls}")
    check("monitor reports offline", monitor.state("groq") == "offline", monitor.state("groq"))
    check("quota flagged", monitor.snapshot("groq")["quota_exhausted"] is True)

    print("\n7. Whole fleet down -> one actionable error")
    primary = FakeProvider("groq", QuotaExceededError("quota", provider="groq"))
    backup = FakeProvider("gemini", QuotaExceededError("quota", provider="gemini"))
    orch, _ = build({"groq": primary, "gemini": backup})
    try:
        run(orch)
        check("raises AllProvidersFailedError", False, "no exception raised")
    except AllProvidersFailedError as exc:
        message = str(exc)
        check("raises AllProvidersFailedError", True)
        check("names both providers", "groq" in message and "gemini" in message)
        check("explains quota", "Quota exhausted" in message, message[:100])
        check("suggests adding a provider", "free tiers" in message)
        check("no raw API payload leaked", "Traceback" not in message)

    print("\n8. An oversized request fails over instead of killing the pipeline")
    # Regression: Groq answers "request too large" with HTTP 413, which fell
    # through to the catch-all and was classified FATAL. That took the whole
    # fleet down over a limit only one provider has.
    primary = FakeProvider(
        "groq", ContextLengthExceededError("413 request too large", provider="groq")
    )
    backup = FakeProvider("gemini")
    orch, _ = build({"groq": primary, "gemini": backup})
    result = run(orch, max_retries=3)
    check("served by fallback", result.provider == "gemini", result.provider)
    check("primary not retried", primary.calls == 1, f"calls={primary.calls}")
    check(
        "reason recorded",
        result.fallback_reason == "context_length_exceeded",
        result.fallback_reason,
    )

    print("\n9. A too-large prompt is routed to a roomier provider, not sent blind")
    big_messages = [ProviderMessage(role="user", content="x" * 40_000)]  # ~10k tokens
    small = FakeProvider("groq")
    roomy = FakeProvider("gemini")
    orch, _ = build(
        {"groq": small, "gemini": roomy},
        limits={
            "groq": ProviderLimits(max_request_tokens=5800),
            "gemini": ProviderLimits(max_request_tokens=120_000),
        },
    )
    result = orch.execute(big_messages, agent="diagnosis", task="smoke", base_delay_ms=1)
    check("served by the roomy provider", result.provider == "gemini", result.provider)
    check("small provider never called", small.calls == 0, f"calls={small.calls}")
    skipped = [a for a in result.attempts if a.outcome == "skipped"]
    check(
        "skip reason recorded",
        any(a.reason == "context_length_exceeded" for a in skipped),
        str([a.reason for a in skipped]),
    )

    print("\n10. Completion budget shrinks to fit the provider's request limit")
    recorder = RecordingProvider("groq")
    orch, _ = build(
        {"groq": recorder},
        limits={"groq": ProviderLimits(max_request_tokens=5800)},
    )
    # ~4 000 prompt tokens + a default 4 096 reservation = 8 096 > 5 800.
    prompt = [ProviderMessage(role="user", content="y" * 16_000)]
    result = orch.execute(
        prompt, agent="diagnosis", task="smoke", max_tokens=4096, base_delay_ms=1
    )
    check("request still served", result.provider == "groq", result.provider)
    check(
        "max_tokens was reduced",
        recorder.last_max_tokens < 4096,
        f"max_tokens={recorder.last_max_tokens}",
    )
    check(
        "prompt + completion fits the limit",
        4000 + recorder.last_max_tokens <= 5800,
        f"{4000} + {recorder.last_max_tokens}",
    )

    print("\n11. A prompt no provider can hold gets a size-specific error")
    tiny_a = FakeProvider("groq")
    tiny_b = FakeProvider("gemini")
    orch, _ = build(
        {"groq": tiny_a, "gemini": tiny_b},
        limits={
            "groq": ProviderLimits(max_request_tokens=2000),
            "gemini": ProviderLimits(max_request_tokens=3000),
        },
    )
    try:
        orch.execute(big_messages, agent="diagnosis", task="smoke", base_delay_ms=1)
        check("raises AllProvidersFailedError", False, "no exception raised")
    except AllProvidersFailedError as exc:
        message = str(exc)
        check("raises AllProvidersFailedError", True)
        check("neither provider was called", tiny_a.calls == 0 and tiny_b.calls == 0)
        check("message names the size problem", "too large" in message, message[:90])
        check("message suggests a fix", "MAX_TOKENS" in message, message[:90])

    print("\n" + "=" * 70)
    if _failures:
        print(f"FAILED: {len(_failures)} check(s)")
        for name in _failures:
            print(f"  - {name}")
        return 1
    print("All failover checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
