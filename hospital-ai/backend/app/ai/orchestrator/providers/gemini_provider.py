"""
Google Gemini provider — priority 2, the first fallback when Groq is out.

Gemini does not speak the OpenAI Chat Completions protocol, so unlike Groq /
OpenRouter / HuggingFace this adapter implements the transport itself:

* messages map onto `contents[]` with `role: user|model` (Gemini has no
  "assistant" role, and system prompts go in a dedicated `systemInstruction`
  field rather than inline),
* the API key travels in the `x-goog-api-key` header rather than a query
  parameter, so it never lands in a proxy access log,
* `responseMimeType: application/json` is requested because every
  orchestrator prompt asks for structured JSON — this removes the markdown
  code-fence wrapping that otherwise has to be stripped downstream,
* Google's error codes are mapped onto the shared taxonomy so the
  `ProviderOrchestrator` treats a Gemini `RESOURCE_EXHAUSTED` exactly like a
  Groq daily-quota 429.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Iterator, List, Optional, Tuple

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
from app.core.logging import get_logger

logger = get_logger("hospital_ai.orchestrator.providers.gemini")

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(BaseAIProvider):
    name = "gemini"
    api_key_env = "GEMINI_API_KEY"
    console_url = "https://aistudio.google.com/apikey"

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
        try:
            response = httpx.post(
                f"{self.base_url}/models/{model}:generateContent",
                headers=self._headers(),
                json=self._payload(messages, temperature, max_tokens),
                timeout=self._timeout(timeout),
            )
        except httpx.ConnectError as exc:
            raise ProviderConnectionError(
                f"Cannot reach the Gemini API at {self.base_url}.", provider=self.name
            ) from exc
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"Gemini request timed out for model '{model}'.", provider=self.name
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderConnectionError(
                f"Gemini transport error: {exc}", provider=self.name
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
        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/models/{model}:streamGenerateContent?alt=sse",
                headers=self._headers(),
                json=self._payload(messages, temperature, max_tokens),
                timeout=self._timeout(timeout),
            ) as response:
                if response.status_code >= 400:
                    response.read()
                    self._raise_for_status(response, model)
                for line in response.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    text = self._extract_text(chunk)
                    if text:
                        yield text
        except httpx.ConnectError as exc:
            raise ProviderConnectionError(
                f"Cannot reach the Gemini API at {self.base_url}.", provider=self.name
            ) from exc
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"Gemini streaming request timed out for model '{model}'.",
                provider=self.name,
            ) from exc

    # ------------------------------------------------------------------
    # Models / health
    # ------------------------------------------------------------------
    def list_models(self) -> List[str]:
        if not self.api_key:
            return []
        try:
            response = httpx.get(
                f"{self.base_url}/models", headers=self._headers(), timeout=10.0
            )
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Gemini list_models failed: %s", exc)
            return []
        try:
            # Names come back fully qualified ("models/gemini-2.5-flash");
            # the rest of the system uses the bare id.
            return [
                str(m.get("name", "")).split("/")[-1]
                for m in (response.json().get("models") or [])
                if m.get("name")
            ]
        except Exception:  # noqa: BLE001
            return []

    def health_check(self, model: str) -> Tuple[bool, Optional[str]]:
        if not self.api_key:
            return False, self._credential_hint()
        models = self.list_models()
        if not models:
            return False, (
                f"Cannot reach the Gemini API at {self.base_url}, or the API key "
                "was rejected."
            )
        if model in models:
            return True, None
        preview = ", ".join(models[:5]) + ("…" if len(models) > 5 else "")
        return False, f"Model '{model}' is not available to this key (saw: {preview})."

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise AuthenticationError(self._credential_hint(), provider=self.name)
        return {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}

    def _credential_hint(self) -> str:
        return (
            "GEMINI_API_KEY is not configured, so the Gemini provider is "
            f"unavailable. Get a free key at {self.console_url} and set it in "
            "backend/.env."
        )

    def _timeout(self, timeout: Optional[float]) -> httpx.Timeout:
        return httpx.Timeout(
            connect=5.0, read=timeout or self.default_timeout, write=30.0, pool=5.0
        )

    def _payload(
        self, messages: List[ProviderMessage], temperature: float, max_tokens: int
    ) -> Dict[str, Any]:
        system_text = "\n\n".join(m.content for m in messages if m.role == "system")
        contents = [
            {
                # Gemini's turn roles are "user" and "model" — an assistant
                # turn from our conversation memory maps onto "model".
                "role": "model" if m.role == "assistant" else "user",
                "parts": [{"text": m.content}],
            }
            for m in messages
            if m.role != "system"
        ]
        if not contents:
            contents = [{"role": "user", "parts": [{"text": system_text or "Respond."}]}]

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}
        return payload

    @staticmethod
    def _extract_text(body: Dict[str, Any]) -> str:
        candidates = body.get("candidates") or []
        if not candidates:
            return ""
        parts = ((candidates[0].get("content") or {}).get("parts")) or []
        return "".join(str(p.get("text") or "") for p in parts)

    def _parse_completion(self, response: httpx.Response, model: str) -> ProviderCompletion:
        try:
            body = response.json()
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailableError(
                "Gemini returned a non-JSON response.", provider=self.name
            ) from exc

        content = self._extract_text(body)
        if not content:
            # A blocked prompt comes back 200 with an empty candidate list and
            # a `promptFeedback.blockReason` — surfacing that as an invalid
            # response lets the orchestrator fail over instead of parsing "".
            block = (body.get("promptFeedback") or {}).get("blockReason")
            if block:
                raise MalformedRequestError(
                    f"Gemini blocked the prompt (reason: {block}).", provider=self.name
                )

        usage = body.get("usageMetadata") or {}
        return ProviderCompletion(
            content=content,
            provider=self.name,
            model=model,
            prompt_tokens=int(usage.get("promptTokenCount") or 0),
            completion_tokens=int(usage.get("candidatesTokenCount") or 0),
            raw=body,
        )

    def _raise_for_status(self, response: httpx.Response, model: str) -> None:
        try:
            error = (response.json().get("error") or {})
            message = str(error.get("message") or response.text)
            status_text = str(error.get("status") or "")
        except Exception:  # noqa: BLE001
            message, status_text = response.text, ""

        message = (message or "").strip()[:500]
        status = response.status_code

        if status == 400:
            # Google returns 400 INVALID_ARGUMENT for a bad key as well as for
            # a genuinely malformed body; the wording is the only signal.
            if "api key not valid" in message.lower() or "api_key_invalid" in message.lower():
                raise AuthenticationError(
                    f"Gemini rejected the API key: {message}", provider=self.name
                )
            raise MalformedRequestError(
                f"Gemini rejected the request: {message}", provider=self.name
            )
        if status in (401, 403):
            raise AuthenticationError(
                f"Gemini rejected the API key ({status}): {message}", provider=self.name
            )
        if status == 404:
            raise ModelNotFoundError(
                f"Gemini model '{model}' not found: {message}", provider=self.name
            )
        if status == 429:
            retry_after = self._retry_delay(response, message)
            # RESOURCE_EXHAUSTED covers both per-minute and per-day limits;
            # only a long retry hint or explicit daily wording means quota.
            if (retry_after and retry_after > 120) or any(
                marker in message.lower()
                for marker in ("per day", "daily", "quota", "limit: 0", "billing")
            ):
                raise QuotaExceededError(
                    f"Gemini quota exceeded: {message}",
                    provider=self.name,
                    retry_after=retry_after,
                )
            raise RateLimitError(
                f"Gemini rate limit exceeded: {message}",
                provider=self.name,
                retry_after=retry_after,
            )
        if status >= 500:
            raise ProviderUnavailableError(
                f"Gemini server error {status} ({status_text}): {message}",
                provider=self.name,
            )
        raise MalformedRequestError(
            f"Gemini returned unexpected status {status}: {message}", provider=self.name
        )

    @staticmethod
    def _retry_delay(response: httpx.Response, message: str) -> Optional[float]:
        raw = response.headers.get("retry-after")
        if raw:
            try:
                return float(raw)
            except (TypeError, ValueError):
                pass
        # Google also embeds `retryDelay: "37s"` in the error details payload.
        try:
            details = (response.json().get("error") or {}).get("details") or []
            for detail in details:
                delay = str(detail.get("retryDelay") or "")
                if delay.endswith("s"):
                    return float(delay[:-1])
        except Exception:  # noqa: BLE001
            pass
        return None
