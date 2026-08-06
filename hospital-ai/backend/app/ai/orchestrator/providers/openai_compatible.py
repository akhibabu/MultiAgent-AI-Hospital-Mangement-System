"""
Shared transport for every OpenAI-compatible provider.

Groq, OpenRouter, HuggingFace Inference, OpenAI, and Azure OpenAI all expose
the same `POST /chat/completions` contract, so they share one hardened HTTP
client instead of five near-identical copies. Each concrete provider only
declares what actually differs: its name, its auth header, its "you are out
of quota" wording, and where a developer goes to get a key.

Everything failure-related is translated into the typed errors in
`errors.py`, which is what lets the `ProviderOrchestrator` decide between
retrying here and failing over to the next provider. No raw `httpx`
exception ever escapes this module.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

import httpx

from app.ai.orchestrator.providers.base import (
    BaseAIProvider,
    ProviderCompletion,
    ProviderMessage,
)
from app.ai.orchestrator.providers.errors import (
    AuthenticationError,
    ContextLengthExceededError,
    MalformedRequestError,
    ModelNotFoundError,
    ProviderConnectionError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    QuotaExceededError,
    RateLimitError,
)
from app.core.logging import get_logger

logger = get_logger("hospital_ai.orchestrator.providers")

# Wording providers use for hard (daily/monthly) limits, as opposed to the
# short per-minute limits that are worth retrying in place.
_DEFAULT_QUOTA_MARKERS: Sequence[str] = (
    "per day",
    "per month",
    "tpd",
    "rpd",
    "daily",
    "monthly",
    "quota",
    "credits",
    "insufficient_quota",
    "billing",
)

# A 429 whose Retry-After exceeds this is a quota reset, not a rate limit —
# no request should ever block for minutes waiting on it.
_QUOTA_RETRY_AFTER_THRESHOLD_SECONDS = 120.0

# Wording that means "this request is too big for me", regardless of the
# status code it arrives under. Matched case-insensitively.
_TOO_LARGE_MARKERS: Sequence[str] = (
    "request too large",
    "context_length_exceeded",
    "context length exceeded",
    "maximum context length",
    "reduce your message size",
    "reduce the length of the messages",
    "too many tokens",
    "input is too long",
    "prompt is too long",
)


class OpenAICompatibleProvider(BaseAIProvider):
    """Base class for providers speaking the OpenAI Chat Completions API."""

    name = "openai_compatible"
    default_base_url = ""
    #: Env var a developer must set, used in actionable error messages.
    api_key_env = "API_KEY"
    #: Where to get that key.
    console_url = ""
    quota_markers: Sequence[str] = _DEFAULT_QUOTA_MARKERS

    def __init__(
        self,
        api_key: str = "",
        base_url: Optional[str] = None,
        timeout: float = 120.0,
        config: Optional[Any] = None,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or self.default_base_url or "").rstrip("/")
        self.default_timeout = timeout or 120.0
        self.config = config

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------
    def generate(
        self,
        messages: List[ProviderMessage],
        *,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: Optional[float] = None,
        agent: str = "",
        task: str = "",
    ) -> ProviderCompletion:
        payload = self._payload(messages, model, temperature, max_tokens, stream=False)
        try:
            response = httpx.post(
                self._chat_endpoint(model),
                headers=self._headers(),
                json=payload,
                timeout=self._timeout(timeout),
            )
        except httpx.ConnectError as exc:
            raise ProviderConnectionError(
                f"Cannot reach {self.name} at {self.base_url}. Check network connectivity.",
                provider=self.name,
            ) from exc
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"{self.name} request timed out for model '{model}' after "
                f"{timeout or self.default_timeout}s.",
                provider=self.name,
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderConnectionError(
                f"{self.name} transport error: {exc}", provider=self.name
            ) from exc

        if response.status_code >= 400:
            self._raise_for_status(response, model)

        return self._parse_completion(response, model)

    # ------------------------------------------------------------------
    # Streaming (SSE)
    # ------------------------------------------------------------------
    def stream(
        self,
        messages: List[ProviderMessage],
        *,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: Optional[float] = None,
        agent: str = "",
        task: str = "",
    ) -> Iterator[str]:
        payload = self._payload(messages, model, temperature, max_tokens, stream=True)
        try:
            with httpx.stream(
                "POST",
                self._chat_endpoint(model),
                headers=self._headers(),
                json=payload,
                timeout=self._timeout(timeout),
            ) as response:
                if response.status_code >= 400:
                    response.read()
                    self._raise_for_status(response, model)
                for line in response.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = (chunk.get("choices") or [{}])[0].get("delta") or {}
                    text = delta.get("content")
                    if text:
                        yield text
        except httpx.ConnectError as exc:
            raise ProviderConnectionError(
                f"Cannot reach {self.name} at {self.base_url}.", provider=self.name
            ) from exc
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"{self.name} streaming request timed out for model '{model}'.",
                provider=self.name,
            ) from exc

    # ------------------------------------------------------------------
    # Models / health
    # ------------------------------------------------------------------
    def list_models(self) -> List[str]:
        if self.requires_key and not self.api_key:
            return []
        try:
            response = httpx.get(
                f"{self.base_url}/models", headers=self._headers(), timeout=10.0
            )
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001 - "unknown", never fatal
            logger.debug("%s list_models failed: %s", self.name, exc)
            return []
        try:
            return [m.get("id") for m in (response.json().get("data") or []) if m.get("id")]
        except Exception:  # noqa: BLE001
            return []

    def health_check(self, model: str) -> Tuple[bool, Optional[str]]:
        if self.requires_key and not self.api_key:
            return False, self._credential_hint()
        models = self.list_models()
        if not models:
            # Some gateways (notably HuggingFace's router) don't expose an
            # enumerable /models list. Absence of a list is "unknown", so we
            # report reachable-but-unverified rather than a false negative.
            return self._probe_without_model_list()
        if model in models:
            return True, None
        preview = ", ".join(models[:5]) + ("…" if len(models) > 5 else "")
        return False, (
            f"Model '{model}' is not available on this {self.name} account "
            f"(saw: {preview})."
        )

    def _probe_without_model_list(self) -> Tuple[bool, Optional[str]]:
        return False, (
            f"Cannot reach {self.name} at {self.base_url}, or the API key was rejected."
        )

    # ------------------------------------------------------------------
    # Internals — override these in concrete providers
    # ------------------------------------------------------------------
    @property
    def requires_key(self) -> bool:
        cfg = self.config
        if cfg is None:
            return True
        return bool(getattr(cfg, "requires_api_key", True))

    def _chat_endpoint(self, model: str) -> str:
        return f"{self.base_url}/chat/completions"

    def _headers(self) -> Dict[str, str]:
        if self.requires_key and not self.api_key:
            raise AuthenticationError(self._credential_hint(), provider=self.name)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self._extra_headers())
        return headers

    def _extra_headers(self) -> Dict[str, str]:
        return {}

    def _payload(
        self,
        messages: List[ProviderMessage],
        model: str,
        temperature: float,
        max_tokens: int,
        *,
        stream: bool,
    ) -> Dict[str, Any]:
        return {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }

    def _credential_hint(self) -> str:
        console = self.console_url or getattr(self.config, "console_url", "") or ""
        where = f" Get one at {console}." if console else ""
        return (
            f"{self.api_key_env} is not configured, so the {self.name} provider "
            f"is unavailable.{where} Set it in backend/.env."
        )

    def _timeout(self, timeout: Optional[float]) -> httpx.Timeout:
        return httpx.Timeout(
            connect=5.0, read=timeout or self.default_timeout, write=30.0, pool=5.0
        )

    def _parse_completion(self, response: httpx.Response, model: str) -> ProviderCompletion:
        try:
            body = response.json()
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailableError(
                f"{self.name} returned a non-JSON response.", provider=self.name
            ) from exc

        usage = body.get("usage") or {}
        choice = (body.get("choices") or [{}])[0]
        content = ((choice.get("message") or {}).get("content")) or ""
        return ProviderCompletion(
            content=content,
            provider=self.name,
            model=body.get("model") or model,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            raw=body,
        )

    def _raise_for_status(self, response: httpx.Response, model: str) -> None:
        """Map an HTTP error onto the typed taxonomy in `errors.py`."""
        try:
            body = response.json()
            error = body.get("error")
            if isinstance(error, dict):
                message = error.get("message") or response.text
            elif isinstance(error, str):
                message = error
            else:
                message = body.get("message") or response.text
        except Exception:  # noqa: BLE001
            message = response.text

        message = (message or "").strip()[:500]
        status = response.status_code

        # Size rejections come back under several different status codes
        # (Groq uses 413, OpenAI uses 400 + `context_length_exceeded`), so
        # they are matched before the generic per-status branches below.
        if self._is_too_large(status, message):
            raise ContextLengthExceededError(
                f"{self.name} rejected the request as too large ({status}): {message}",
                provider=self.name,
            )
        if status in (400, 422):
            raise MalformedRequestError(
                f"{self.name} rejected the request as invalid ({status}): {message}",
                provider=self.name,
            )
        if status in (401, 403):
            raise AuthenticationError(
                f"{self.name} rejected the API key ({status}): {message}",
                provider=self.name,
            )
        if status == 404:
            raise ModelNotFoundError(
                f"{self.name} model '{model}' not found: {message}", provider=self.name
            )
        if status == 402:
            # OpenRouter/OpenAI use 402 for exhausted credits.
            raise QuotaExceededError(
                f"{self.name} credits exhausted: {message}", provider=self.name
            )
        if status == 429:
            retry_after = self._retry_after(response)
            if self._is_quota(message, retry_after):
                raise QuotaExceededError(
                    f"{self.name} quota exceeded: {message}",
                    provider=self.name,
                    retry_after=retry_after,
                )
            raise RateLimitError(
                f"{self.name} rate limit exceeded: {message}",
                provider=self.name,
                retry_after=retry_after,
            )
        if status >= 500:
            raise ProviderUnavailableError(
                f"{self.name} server error {status}: {message}", provider=self.name
            )
        raise MalformedRequestError(
            f"{self.name} returned unexpected status {status}: {message}",
            provider=self.name,
        )

    @staticmethod
    def _retry_after(response: httpx.Response) -> Optional[float]:
        raw = response.headers.get("retry-after")
        if not raw:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    def _is_quota(self, message: str, retry_after: Optional[float]) -> bool:
        """Distinguish 'come back tomorrow' from 'come back in 5 seconds'."""
        if retry_after is not None and retry_after > _QUOTA_RETRY_AFTER_THRESHOLD_SECONDS:
            return True
        lowered = (message or "").lower()
        return any(marker in lowered for marker in self.quota_markers)

    @staticmethod
    def _is_too_large(status: int, message: str) -> bool:
        """Is this a 'your request doesn't fit' rejection?

        HTTP 413 always is. Beyond that the signal is only in the wording:
        OpenAI reports context overflow as a 400 with `context_length_exceeded`,
        and Groq phrases its per-minute token ceiling as "Request too large …
        please reduce your message size", which is the same class of problem
        even though it is a rate limit underneath.
        """
        if status == 413:
            return True
        if status not in (400, 422):
            return False
        lowered = (message or "").lower()
        return any(marker in lowered for marker in _TOO_LARGE_MARKERS)
