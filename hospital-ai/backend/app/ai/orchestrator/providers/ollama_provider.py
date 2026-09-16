"""
Ollama provider — optional local runtime, disabled by default.

Talks to a locally running `ollama serve` instance (default
`http://localhost:11434`). Because it runs on the operator's own hardware it
has no API key, no quota, and no cost, which makes it a useful last link in
the failover chain for air-gapped or offline deployments — enable it in
`providers.yaml` (`ollama.enabled: true`) and pull the configured model.

Failures are raised as the shared typed errors so the Provider Orchestrator
treats a dead local runtime exactly like any other unreachable provider.
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

import httpx

from app.ai.orchestrator.providers.base import (
    BaseAIProvider,
    ProviderCompletion,
    ProviderMessage,
)
from app.ai.orchestrator.providers.errors import (
    ModelNotFoundError,
    ProviderConnectionError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.core.logging import get_logger

logger = get_logger("hospital_ai.orchestrator.providers.ollama")


class OllamaProvider(BaseAIProvider):
    """Local runtime — no credentials, no quota, no cost."""

    name = "ollama"

    def __init__(
        self,
        base_url: str = "",
        timeout: float = 180.0,
        config: Optional[Any] = None,
    ) -> None:
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")
        self.default_timeout = timeout or 180.0
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
        try:
            # Connect/pool must fail fast when Ollama isn't running; read stays
            # long so local model generation can finish (first load is slow).
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                    "messages": [{"role": m.role, "content": m.content} for m in messages],
                },
                timeout=httpx.Timeout(
                    connect=5.0,
                    read=timeout or self.default_timeout,
                    write=30.0,
                    pool=5.0,
                ),
            )
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise ProviderConnectionError(
                f"Cannot reach Ollama at {self.base_url}. Is 'ollama serve' running? "
                f"Install from https://ollama.com then run: ollama pull {model}",
                provider=self.name,
            ) from exc
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"Ollama request timed out for model '{model}'. "
                f"If Ollama is not running, start it; otherwise the model may still be loading.",
                provider=self.name,
            ) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 404:
                raise ModelNotFoundError(
                    f"Ollama model '{model}' not found. Run 'ollama pull {model}'.",
                    provider=self.name,
                ) from exc
            if status >= 500:
                raise ProviderUnavailableError(
                    f"Ollama returned server error {status} for model '{model}'.",
                    provider=self.name,
                ) from exc
            raise

        body = response.json()
        content = (body.get("message") or {}).get("content") or body.get("response") or ""
        return ProviderCompletion(
            content=content,
            provider=self.name,
            model=model,
            prompt_tokens=int(body.get("prompt_eval_count") or 0),
            completion_tokens=int(body.get("eval_count") or 0),
            raw=body,
        )

    def list_models(self) -> List[str]:
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            response.raise_for_status()
        except httpx.HTTPError:
            return []
        try:
            return [m.get("name") for m in (response.json().get("models") or []) if m.get("name")]
        except Exception:  # noqa: BLE001
            return []

    def health_check(self, model: str) -> Tuple[bool, Optional[str]]:
        try:
            names = set(self.list_models())
        except Exception as exc:  # noqa: BLE001
            return False, f"Cannot reach Ollama at {self.base_url}: {exc}"
        if not names:
            return False, f"Cannot reach Ollama at {self.base_url}."
        base_names = {str(n).split(":")[0] for n in names if n}

        if model in names or model.split(":")[0] in base_names:
            return True, None
        return False, f"Model '{model}' not pulled. Run 'ollama pull {model}'."
