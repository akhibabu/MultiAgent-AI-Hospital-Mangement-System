"""
Abstract interfaces for the AI Orchestrator (Dependency Inversion Principle).

Every pluggable subsystem — LLM provider, prompt loading, context
assembly, caching, conversation memory, retries, model routing, response
parsing — is defined here as an ABC. `orchestrator.py` (the facade)
depends only on these contracts, never on a concrete implementation.
This is what lets a new LLM provider, a swapped-out cache backend, or a
different memory store be introduced later by adding one new class,
without touching the orchestrator facade or any AI Agent.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Type, TypeVar
from uuid import UUID

from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass
class ProviderMessage:
    """A single chat message sent to an LLM provider."""

    role: str  # system | user | assistant
    content: str


@dataclass
class ProviderCompletion:
    """Raw provider output — no business/parsing logic lives here."""

    content: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw: Dict[str, Any] = field(default_factory=dict)


class BaseAIProvider(ABC):
    """
    Provider-independent contract every LLM adapter must implement (Groq,
    Gemini, OpenRouter, HuggingFace, OpenAI, Anthropic, Azure OpenAI,
    Ollama, and any future provider). The orchestrator's `ProviderRouter`
    is the only thing that ever constructs a concrete provider, and the
    `ProviderOrchestrator` is the only thing that ever calls one — no AI
    Agent imports this module or a provider class directly.

    Adding a new provider means implementing this class, registering a
    factory in `ProviderRouter`, and adding a block to `providers.yaml`;
    nothing else in the system changes.

    `config` carries the provider's `providers.yaml` entry (capabilities,
    pricing, models, timeout). It is optional so providers stay unit-testable
    standalone, but the router always injects it in production.
    """

    name: str
    config: Optional[Any] = None  # ProviderConfig — untyped here to avoid a cycle

    @abstractmethod
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
        """
        Single-shot completion. `agent`/`task` are optional call metadata
        (which AI Agent/stage made this request) — real network-backed
        providers may ignore them or use them for their own request
        logging/telemetry; the `StubProvider` (`AI_PROVIDER=stub`,
        tests/offline dev only) uses them to select a task-appropriate
        canned JSON response.

        Implementations must raise typed exceptions so the orchestrator's
        `RetryHandler` can react correctly:
        - `ConnectionError` / `TimeoutError` / `OSError` (or the
          `RateLimitError` subclass in `providers/errors.py`) — transient,
          retried with exponential backoff.
        - `AuthenticationError` / `ModelNotFoundError` / `ValueError` —
          configuration problems, fail fast with an actionable message.
        """

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
        """
        Yields incremental text chunks. Providers without native
        streaming support (or that don't need it yet) may rely on this
        default, which simply yields the full `generate()` result once.
        """
        completion = self.generate(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            agent=agent,
            task=task,
        )
        yield completion.content

    def health_check(self, model: str) -> Tuple[bool, Optional[str]]:
        """Best-effort connectivity / model-availability check."""
        return True, None

    def list_models(self) -> List[str]:
        """Best-effort list of models available to this provider/account.
        Returns an empty list if the provider has no models endpoint or
        the call fails — callers must treat that as "unknown", not "none"."""
        return []

    def is_available(self) -> bool:
        """
        Cheap, non-network readiness check: does this provider have what it
        needs to be called at all (credentials, endpoint, enabled flag)?

        Distinct from `health_check()`, which performs live network I/O. The
        `ProviderOrchestrator` calls this on every request to build the
        candidate list, so it must stay fast and side-effect free.
        """
        cfg = self.config
        if cfg is None:
            return True
        return bool(getattr(cfg, "configured", True))

    def estimate_tokens(self, text: str) -> int:
        """
        Rough token estimate (~4 chars/token heuristic) for providers that
        don't report usage up front, e.g. before a request is sent to
        pre-flight-check `max_tokens` budgets. Override with a real
        tokenizer where one is cheaply available.
        """
        return max(1, len(text or "") // 4)

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Best-effort USD estimate for one call, from the `pricing` block in
        `providers.yaml`. Returns 0.0 for free/local providers and whenever
        pricing is unknown — always label this an *estimate* in the UI, it is
        never a billing source of truth.
        """
        cfg = self.config
        pricing = getattr(cfg, "pricing", None) if cfg is not None else None
        if pricing is None:
            return 0.0
        return pricing.estimate(prompt_tokens, completion_tokens)

    def supports_streaming(self) -> bool:
        """Whether `stream()` yields real incremental chunks (vs. one blob)."""
        return self._capability("streaming", default=False)

    def supports_vision(self) -> bool:
        """Whether the provider's routed models accept image input."""
        return self._capability("vision", default=False)

    def supports_long_context(self) -> bool:
        """Whether the provider handles large (>32k token) prompts comfortably."""
        return self._capability("long_context", default=False)

    def _capability(self, flag: str, *, default: bool) -> bool:
        capabilities = getattr(self.config, "capabilities", None) if self.config else None
        if capabilities is None:
            return default
        return bool(getattr(capabilities, flag, default))

    def validate_response(self, completion: ProviderCompletion) -> bool:
        """Sanity check before handing a completion to the ResponseParser."""
        return bool(completion.content and completion.content.strip())

    def complete(
        self,
        messages: List[ProviderMessage],
        *,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        agent: str = "",
        task: str = "",
    ) -> ProviderCompletion:
        """Deprecated alias kept for backward compatibility — use `generate()`."""
        return self.generate(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            agent=agent,
            task=task,
        )


# Backward-compatible alias — existing code importing `IAIProvider` keeps working.
IAIProvider = BaseAIProvider


class IModelRouter(ABC):
    @abstractmethod
    def resolve(self, agent: str) -> Tuple[str, str]:
        """Returns (provider_name, model_name) for the requesting agent."""


class IPromptManager(ABC):
    @abstractmethod
    def render(
        self, agent: str, task: str, variables: Dict[str, Any]
    ) -> Tuple[str, str, str]:
        """Returns (system_prompt, rendered_task_prompt, prompt_version)."""


class IContextManager(ABC):
    @abstractmethod
    def build(
        self,
        agent: str,
        patient_id: Optional[UUID],
        extra_vars: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Assembles every variable a prompt template may reference."""


class ICacheManager(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def set(self, key: str, value: Dict[str, Any]) -> None: ...


class IConversationMemory(ABC):
    @abstractmethod
    def recent(
        self, patient_id: UUID, agent: str, limit: int
    ) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def append(
        self,
        patient_id: UUID,
        agent: str,
        task: str,
        prompt_rendered: str,
        response_text: str,
        response_json: Optional[Dict[str, Any]],
        model: str,
        provider: str,
    ) -> None: ...


class IRetryHandler(ABC):
    @abstractmethod
    def execute(
        self,
        fn: Callable[[], Any],
        *,
        max_retries: int,
        base_delay_ms: int,
    ) -> Tuple[Any, int]:
        """Runs fn() with exponential backoff. Returns (result, retry_count)."""


class IResponseParser(ABC):
    @abstractmethod
    def parse(self, raw_text: str, response_model: Type[ModelT]) -> ModelT: ...

    @abstractmethod
    def extract_json(self, raw_text: str) -> Dict[str, Any]: ...


class IUsageLogger(ABC):
    @abstractmethod
    def log(self, **fields: Any) -> None: ...
