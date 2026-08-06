"""
Typed provider errors + the failure taxonomy that drives failover.

Every LLM adapter (Groq, Gemini, OpenRouter, HuggingFace, OpenAI, Anthropic,
Azure OpenAI, Ollama) translates its raw HTTP/SDK failures into one of these
types. The `ProviderOrchestrator` then asks `classify()` what to do, so the
retry/failover policy lives in exactly one place instead of being re-derived
from status codes at each call site.

    ┌─────────────────────┬──────────────────────────────────────────────────┐
    │ FailureAction.RETRY │ Same provider, exponential backoff.               │
    │                     │ Network blips, HTTP 500/502/503, timeouts,        │
    │                     │ short rate limits.                                │
    ├─────────────────────┼──────────────────────────────────────────────────┤
    │ FailureAction       │ Give up on this provider, immediately try the     │
    │        .FAILOVER    │ next healthy one. Quota exhausted, bad/missing    │
    │                     │ API key, model unavailable here, provider down.   │
    ├─────────────────────┼──────────────────────────────────────────────────┤
    │ FailureAction.FATAL │ No provider can help — the request itself is      │
    │                     │ wrong. Malformed payload, unsupported parameter.  │
    └─────────────────────┴──────────────────────────────────────────────────┘

Retrying on the *same* provider is pointless for a bad API key or an
exhausted daily quota, and failing over is pointless for a malformed
request — getting this classification right is what turns "one provider ran
out of quota" from an outage into an invisible reroute.
"""
from __future__ import annotations

import enum
from typing import Optional


class FailureAction(enum.Enum):
    """What the Provider Orchestrator should do about a given failure."""

    RETRY = "retry"
    FAILOVER = "failover"
    FATAL = "fatal"


class ProviderError(RuntimeError):
    """Base for every provider failure that carries a failover decision.

    `provider` and `retry_after` are filled in by the adapter where known;
    the orchestrator uses them for logging and for health-monitor cooldowns.
    """

    action: FailureAction = FailureAction.FAILOVER
    #: Short machine-readable reason, surfaced in logs and Developer Mode
    #: as "why did we switch providers".
    reason: str = "provider_error"

    def __init__(
        self,
        message: str,
        *,
        provider: str = "",
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.retry_after = retry_after


# ---------------------------------------------------------------------------
# FAILOVER — this provider can't serve the request, another one might
# ---------------------------------------------------------------------------
class AuthenticationError(ProviderError):
    """Invalid or missing API key. Never retried — the key won't fix itself
    mid-request — but another provider may well be configured correctly."""

    action = FailureAction.FAILOVER
    reason = "invalid_api_key"


class ModelNotFoundError(ProviderError):
    """Requested model doesn't exist for this provider/account. Another
    provider in the chain routes to a different model and may succeed."""

    action = FailureAction.FAILOVER
    reason = "model_not_found"


class QuotaExceededError(ProviderError):
    """Daily/monthly quota exhausted. Does not recover within a request
    window, so we fail over immediately and put this provider in a long
    cooldown rather than sleeping for hours."""

    action = FailureAction.FAILOVER
    reason = "quota_exceeded"


class ProviderOfflineError(ProviderError):
    """Provider is unreachable or persistently erroring (health monitor has
    taken it out of rotation, or DNS/connection failed outright)."""

    action = FailureAction.FAILOVER
    reason = "provider_offline"


class InvalidResponseError(ProviderError):
    """Provider returned an empty or structurally unusable payload. Another
    provider gets a clean shot at the same prompt."""

    action = FailureAction.FAILOVER
    reason = "invalid_response"


class ContextLengthExceededError(ProviderError):
    """The request is larger than this provider will accept in one call.

    Deliberately NOT fatal, even though the provider reports it like a bad
    request. "Too big for Groq's 6 000 token-per-minute free tier" says
    nothing about Gemini's 1M context window — the prompt is valid, this
    particular provider just can't hold it. Failing over is exactly right.

    Note that providers count the *reserved* completion budget against the
    same limit, so `prompt_tokens + max_tokens` is what has to fit, not the
    prompt alone. `ProviderOrchestrator` shrinks `max_tokens` to fit before
    sending; this error is what remains when even that isn't enough.
    """

    action = FailureAction.FAILOVER
    reason = "context_length_exceeded"


# ---------------------------------------------------------------------------
# RETRY — transient, same provider will probably work in a moment
# ---------------------------------------------------------------------------
class RateLimitError(ProviderError):
    """Short-window rate limit (requests/tokens per minute). Retryable with
    backoff, honoring `retry_after` when the provider supplies one.

    Distinct from `QuotaExceededError`: that one means "come back tomorrow",
    this one means "come back in a few seconds".
    """

    action = FailureAction.RETRY
    reason = "rate_limited"


class ProviderTimeoutError(ProviderError):
    """Request exceeded the configured timeout."""

    action = FailureAction.RETRY
    reason = "timeout"


class ProviderUnavailableError(ProviderError):
    """HTTP 500/502/503/504 — provider-side transient fault."""

    action = FailureAction.RETRY
    reason = "server_error"


class ProviderConnectionError(ProviderError):
    """Network failure reaching the provider (DNS, TLS, connection reset)."""

    action = FailureAction.RETRY
    reason = "network_failure"


# ---------------------------------------------------------------------------
# FATAL — the request itself is wrong; no provider will accept it
# ---------------------------------------------------------------------------
class MalformedRequestError(ProviderError):
    """HTTP 400/422 — we sent something structurally invalid (bad parameter,
    unsupported option). Failing over would just reproduce the same error N
    more times and delay a clear message to the operator.

    Size problems are explicitly *not* in this category — see
    `ContextLengthExceededError`. Treating "too big for this provider" as
    fatal takes the whole fleet down over a limit only one member has.
    """

    action = FailureAction.FATAL
    reason = "malformed_request"


def classify(exc: BaseException) -> FailureAction:
    """Decide what to do about `exc`.

    Handles both our typed `ProviderError`s and the builtin exceptions that
    adapters (or httpx, or the stdlib) may still raise, so an adapter that
    hasn't been fully migrated still gets sane retry behavior.
    """
    if isinstance(exc, ProviderError):
        return exc.action
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return FailureAction.RETRY
    if isinstance(exc, ValueError):
        # Historically raised by adapters for "model not found" / bad config.
        return FailureAction.FAILOVER
    return FailureAction.FAILOVER


def reason_for(exc: BaseException) -> str:
    """Short machine-readable failure reason for logs and Developer Mode."""
    if isinstance(exc, ProviderError):
        return exc.reason
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, ConnectionError):
        return "network_failure"
    if isinstance(exc, OSError):
        return "network_failure"
    return exc.__class__.__name__
