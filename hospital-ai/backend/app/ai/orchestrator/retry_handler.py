"""
RetryHandler — exponential backoff for *transient* provider failures.

This handles the "try the same provider again" half of resilience; the
"try a different provider" half is `ProviderOrchestrator`. The split matters:
retrying is only ever correct for failures that are likely to clear on their
own within a second or two.

What is retried is decided by `providers/errors.classify()`, never by
inspecting status codes here:

    RETRY     network failures, HTTP 500/502/503/504, timeouts, short
              (per-minute) rate limits
    FAILOVER  quota exhausted, invalid API key, model not found — re-raised
              immediately so the caller can switch providers
    FATAL     malformed request — re-raised immediately; no amount of
              retrying or failing over fixes a bad payload

Backoff is exponential (`base_delay_ms * 2**attempt`). When a provider sends
a `Retry-After`, it is honored but capped: a rate limit that says "wait 90
minutes" is really a quota, and blocking a clinician's request for 90 minutes
is never the right answer — those raise `QuotaExceededError` and fail over
instead.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Tuple

from app.ai.orchestrator.interfaces import IRetryHandler
from app.ai.orchestrator.providers.errors import FailureAction, classify, reason_for
from app.core.logging import get_logger

logger = get_logger("hospital_ai.orchestrator.retry")

#: Never sleep longer than this on a single retry, whatever `Retry-After` says.
MAX_RETRY_SLEEP_SECONDS = 30.0


class ExponentialBackoffRetryHandler(IRetryHandler):
    def execute(
        self,
        fn: Callable[[], Any],
        *,
        max_retries: int = 3,
        base_delay_ms: int = 500,
    ) -> Tuple[Any, int]:
        """Run `fn`, retrying transient failures. Returns `(result, retry_count)`."""
        attempt = 0
        while True:
            try:
                return fn(), attempt
            except BaseException as exc:  # noqa: BLE001 - re-raised below
                if classify(exc) is not FailureAction.RETRY:
                    raise
                if attempt >= max_retries:
                    logger.error(
                        "Retry budget exhausted after %s attempt(s) (%s): %s",
                        attempt + 1,
                        reason_for(exc),
                        exc,
                    )
                    raise

                delay = self._delay_seconds(exc, attempt, base_delay_ms)
                logger.warning(
                    "Transient provider failure (%s), attempt %s/%s — retrying in %.1fs: %s",
                    reason_for(exc),
                    attempt + 1,
                    max_retries,
                    delay,
                    exc,
                )
                time.sleep(delay)
                attempt += 1

    @staticmethod
    def _delay_seconds(exc: BaseException, attempt: int, base_delay_ms: int) -> float:
        delay = (base_delay_ms * (2**attempt)) / 1000.0
        retry_after = getattr(exc, "retry_after", None)
        if isinstance(retry_after, (int, float)) and retry_after > 0:
            delay = max(delay, float(retry_after))
        return min(delay, MAX_RETRY_SLEEP_SECONDS)


_retry_handler: ExponentialBackoffRetryHandler | None = None


def get_retry_handler() -> ExponentialBackoffRetryHandler:
    global _retry_handler
    if _retry_handler is None:
        _retry_handler = ExponentialBackoffRetryHandler()
    return _retry_handler
