"""
Anthropic (Claude) provider — implemented, disabled by default because it
needs paid credentials.

Claude's Messages API differs from OpenAI's in two ways this adapter
normalizes: the system prompt is a top-level `system` field rather than a
message with `role: system`, and authentication uses `x-api-key` plus a
pinned `anthropic-version` header.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.ai.orchestrator.providers.base import (
    BaseAIProvider,
    ProviderCompletion,
    ProviderMessage,
)
from app.ai.orchestrator.providers.errors import (
    AuthenticationError,
    MalformedRequestError,
    ModelNotFoundError,
    ProviderConnectionError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    QuotaExceededError,
    RateLimitError,
)

DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
API_VERSION = "2023-06-01"


class AnthropicProvider(BaseAIProvider):
    name = "anthropic"
    api_key_env = "ANTHROPIC_API_KEY"
    console_url = "https://console.anthropic.com/settings/keys"

    def __init__(
        self,
        api_key: str = "",
        base_url: Optional[str] = None,
        timeout: float = 120.0,
        config: Optional[Any] = None,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.default_timeout = timeout or 120.0
        self.config = config

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
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        chat = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in {"user", "assistant"}
        ]
        try:
            response = httpx.post(
                f"{self.base_url}/messages",
                headers=self._headers(),
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system or "You are a clinical AI assistant.",
                    "messages": chat or [{"role": "user", "content": "Respond."}],
                },
                timeout=self._timeout(timeout),
            )
        except httpx.ConnectError as exc:
            raise ProviderConnectionError(
                "Cannot reach the Anthropic API.", provider=self.name
            ) from exc
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"Anthropic request timed out for model '{model}'.", provider=self.name
            ) from exc

        if response.status_code >= 400:
            self._raise_for_status(response, model)

        body = response.json()
        usage = body.get("usage") or {}
        blocks = body.get("content") or []
        content = "".join(
            str(b.get("text") or "") for b in blocks if isinstance(b, dict)
        )
        return ProviderCompletion(
            content=content,
            provider=self.name,
            model=body.get("model") or model,
            prompt_tokens=int(usage.get("input_tokens") or 0),
            completion_tokens=int(usage.get("output_tokens") or 0),
            raw=body,
        )

    def list_models(self) -> List[str]:
        if not self.api_key:
            return []
        try:
            response = httpx.get(
                f"{self.base_url}/models", headers=self._headers(), timeout=10.0
            )
            response.raise_for_status()
            return [m.get("id") for m in (response.json().get("data") or []) if m.get("id")]
        except Exception:  # noqa: BLE001
            return []

    def health_check(self, model: str) -> Tuple[bool, Optional[str]]:
        if not self.api_key:
            return False, (
                "ANTHROPIC_API_KEY is not configured, so the Anthropic provider "
                f"is unavailable. Get a key at {self.console_url}."
            )
        models = self.list_models()
        if not models:
            return False, "Cannot reach the Anthropic API, or the API key was rejected."
        if model in models:
            return True, None
        return False, f"Model '{model}' is not available to this Anthropic account."

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise AuthenticationError(
                "ANTHROPIC_API_KEY is not configured.", provider=self.name
            )
        return {
            "x-api-key": self.api_key,
            "anthropic-version": API_VERSION,
            "Content-Type": "application/json",
        }

    def _timeout(self, timeout: Optional[float]) -> httpx.Timeout:
        return httpx.Timeout(
            connect=5.0, read=timeout or self.default_timeout, write=30.0, pool=5.0
        )

    def _raise_for_status(self, response: httpx.Response, model: str) -> None:
        try:
            message = str((response.json().get("error") or {}).get("message") or response.text)
        except Exception:  # noqa: BLE001
            message = response.text
        message = (message or "").strip()[:500]
        status = response.status_code

        if status in (400, 422):
            raise MalformedRequestError(
                f"Anthropic rejected the request: {message}", provider=self.name
            )
        if status in (401, 403):
            raise AuthenticationError(
                f"Anthropic rejected the API key: {message}", provider=self.name
            )
        if status == 404:
            raise ModelNotFoundError(
                f"Anthropic model '{model}' not found: {message}", provider=self.name
            )
        if status == 429:
            lowered = message.lower()
            if "credit" in lowered or "quota" in lowered or "billing" in lowered:
                raise QuotaExceededError(
                    f"Anthropic quota exhausted: {message}", provider=self.name
                )
            raise RateLimitError(
                f"Anthropic rate limit exceeded: {message}", provider=self.name
            )
        if status >= 500:
            raise ProviderUnavailableError(
                f"Anthropic server error {status}: {message}", provider=self.name
            )
        raise MalformedRequestError(
            f"Anthropic returned unexpected status {status}: {message}", provider=self.name
        )
