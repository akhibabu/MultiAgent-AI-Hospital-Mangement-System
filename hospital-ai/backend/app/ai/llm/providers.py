"""Provider-independent LLM abstraction with adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

import httpx

from app.core.logging import get_logger

logger = get_logger("hospital_ai.llm")


@dataclass
class LLMMessage:
    role: str  # system | user | assistant
    content: str


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    usage: dict = field(default_factory=dict)


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def complete(
        self,
        messages: List[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        ...


class StubLLMProvider(LLMProvider):
    """Deterministic local LLM for Intake without external APIs."""

    name = "stub"

    def complete(
        self,
        messages: List[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        summary = (
            "Patient summary (stub LLM): clinical narrative reviewed. "
            "Key themes include chronic metabolic disease, elevated vitals, "
            "and active respiratory symptoms. Downstream agents should use "
            "structured Patient Context JSON rather than this prose."
        )
        if "entity" in user.lower() or "extract" in user.lower():
            summary = (
                '{"diseases":["Type 2 Diabetes Mellitus","Hypertension"],'
                '"symptoms":["fever","cough","fatigue"],'
                '"medications":[{"name":"Metformin","dosage":"500 mg"}],'
                '"note":"stub-llm-json"}'
            )
        return LLMResponse(
            content=summary[:max_tokens],
            provider=self.name,
            model="stub-local",
            usage={"prompt_chars": sum(len(m.content) for m in messages)},
        )


class OpenAIAdapter(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def complete(
        self,
        messages: List[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        payload = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60.0,
        )
        response.raise_for_status()
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        return LLMResponse(
            content=content,
            provider=self.name,
            model=self.model,
            usage=body.get("usage") or {},
        )


class GeminiAdapter(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def complete(
        self,
        messages: List[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        # Flatten chat into Gemini content parts
        text = "\n\n".join(f"{m.role.upper()}: {m.content}" for m in messages)
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        response = httpx.post(
            url,
            json={
                "contents": [{"parts": [{"text": text}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
            },
            timeout=60.0,
        )
        response.raise_for_status()
        body = response.json()
        content = body["candidates"][0]["content"]["parts"][0]["text"]
        return LLMResponse(
            content=content, provider=self.name, model=self.model, usage={}
        )


class AnthropicAdapter(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def complete(
        self,
        messages: List[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        system = "\n".join(m.content for m in messages if m.role == "system")
        chat = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in {"user", "assistant"}
        ]
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system or "You are a clinical intake assistant.",
                "messages": chat or [{"role": "user", "content": "Summarize."}],
            },
            timeout=60.0,
        )
        response.raise_for_status()
        body = response.json()
        content = body["content"][0]["text"]
        return LLMResponse(
            content=content, provider=self.name, model=self.model, usage=body.get("usage") or {}
        )


class OllamaAdapter(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def complete(
        self,
        messages: List[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
                "messages": [{"role": m.role, "content": m.content} for m in messages],
            },
            timeout=120.0,
        )
        response.raise_for_status()
        body = response.json()
        content = (body.get("message") or {}).get("content") or body.get("response") or ""
        return LLMResponse(
            content=content, provider=self.name, model=self.model, usage={}
        )


def get_llm_provider() -> LLMProvider:
    from app.config import get_settings

    settings = get_settings()
    name = (settings.llm_provider or "stub").strip().lower()
    if name in {"stub", "local", "none"}:
        return StubLLMProvider()
    if name == "openai":
        return OpenAIAdapter(settings.openai_api_key, settings.openai_model)
    if name in {"gemini", "google"}:
        return GeminiAdapter(settings.gemini_api_key, settings.gemini_model)
    if name == "anthropic":
        return AnthropicAdapter(settings.anthropic_api_key, settings.anthropic_model)
    if name == "ollama":
        return OllamaAdapter(settings.ollama_base_url, settings.ollama_model)
    raise ValueError(
        f"Unknown LLM_PROVIDER '{name}'. Use stub|openai|gemini|anthropic|ollama"
    )
