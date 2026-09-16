"""
ProviderRouter — turns a provider *name* into a live provider *instance*.

    AI Agent -> AI Orchestrator -> Provider Orchestrator -> [Provider Router]
             -> Provider Health Monitor -> Groq / Gemini / OpenRouter / HuggingFace

This is the only place in the codebase that knows which class backs which
name, and the only place that ever constructs one. The orchestrator, the load
balancer, the model router, and every AI Agent deal purely in names.

Construction is lazy and cached per name — an adapter is built the first time
it is needed and reused for the process lifetime, so a request never pays to
re-instantiate an HTTP client.

Every adapter is handed its `ProviderConfig` (from `providers.yaml`), which
is what supplies credentials, base URL, timeout, capability flags, and
pricing. Adding a provider therefore means: implement `BaseAIProvider`, add
one factory line below (or call `register()` from a plugin at startup), and
add a block to `providers.yaml`. No agent and no orchestrator code changes.
"""
from __future__ import annotations

import threading
from typing import Callable, Dict, List, Optional

from app.ai.orchestrator.interfaces import BaseAIProvider
from app.ai.orchestrator.providers.config import (
    FleetConfig,
    ProviderConfig,
    get_fleet_config,
)
from app.core.logging import get_logger

logger = get_logger("hospital_ai.orchestrator.provider_router")

#: A factory takes the provider's parsed YAML config and returns an adapter.
ProviderFactory = Callable[[ProviderConfig], BaseAIProvider]


class UnknownProviderError(ValueError):
    """Raised when a name has no registered adapter."""


class ProviderRouter:
    def __init__(self, fleet: Optional[FleetConfig] = None) -> None:
        self._fleet = fleet or get_fleet_config()
        self._instances: Dict[str, BaseAIProvider] = {}
        self._factories: Dict[str, ProviderFactory] = {}
        self._lock = threading.Lock()
        self._register_builtin_factories()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def _register_builtin_factories(self) -> None:
        # Imports are deferred into each factory so that an optional
        # provider's dependencies are only imported if it is actually used.
        def _groq(cfg: ProviderConfig) -> BaseAIProvider:
            from app.ai.orchestrator.providers.groq_provider import GroqProvider

            return GroqProvider(cfg.api_key, cfg.base_url, cfg.timeout_seconds, cfg)

        def _gemini(cfg: ProviderConfig) -> BaseAIProvider:
            from app.ai.orchestrator.providers.gemini_provider import GeminiProvider

            return GeminiProvider(cfg.api_key, cfg.base_url, cfg.timeout_seconds, cfg)

        def _openrouter(cfg: ProviderConfig) -> BaseAIProvider:
            from app.ai.orchestrator.providers.openrouter_provider import (
                OpenRouterProvider,
            )

            return OpenRouterProvider(cfg.api_key, cfg.base_url, cfg.timeout_seconds, cfg)

        def _huggingface(cfg: ProviderConfig) -> BaseAIProvider:
            from app.ai.orchestrator.providers.huggingface_provider import (
                HuggingFaceProvider,
            )

            return HuggingFaceProvider(cfg.api_key, cfg.base_url, cfg.timeout_seconds, cfg)

        def _openai(cfg: ProviderConfig) -> BaseAIProvider:
            from app.ai.orchestrator.providers.openai_provider import OpenAIProvider

            return OpenAIProvider(cfg.api_key, cfg.base_url, cfg.timeout_seconds, cfg)

        def _anthropic(cfg: ProviderConfig) -> BaseAIProvider:
            from app.ai.orchestrator.providers.anthropic_provider import AnthropicProvider

            return AnthropicProvider(cfg.api_key, cfg.base_url, cfg.timeout_seconds, cfg)

        def _azure_openai(cfg: ProviderConfig) -> BaseAIProvider:
            from app.ai.orchestrator.providers.azure_openai_provider import (
                AzureOpenAIProvider,
            )

            return AzureOpenAIProvider(cfg.api_key, cfg.base_url, cfg.timeout_seconds, cfg)

        def _ollama(cfg: ProviderConfig) -> BaseAIProvider:
            from app.ai.orchestrator.providers.ollama_provider import OllamaProvider

            return OllamaProvider(cfg.base_url, cfg.timeout_seconds, cfg)

        def _stub(cfg: ProviderConfig) -> BaseAIProvider:
            from app.ai.orchestrator.providers.stub_provider import StubProvider

            return StubProvider(cfg)

        self._factories = {
            "groq": _groq,
            "gemini": _gemini,
            "google": _gemini,
            "openrouter": _openrouter,
            "huggingface": _huggingface,
            "hf": _huggingface,
            "openai": _openai,
            "anthropic": _anthropic,
            "claude": _anthropic,
            "azure_openai": _azure_openai,
            "azure": _azure_openai,
            "ollama": _ollama,
            "stub": _stub,
        }

    def register(self, name: str, factory: ProviderFactory) -> None:
        """Register (or override) an adapter at runtime — from a plugin module
        or a test fixture — without editing this file."""
        key = (name or "").strip().lower()
        with self._lock:
            self._instances.pop(key, None)
            self._factories[key] = factory
        logger.info("Registered AI provider adapter '%s'.", key)

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------
    def resolve(self, name: Optional[str] = None) -> BaseAIProvider:
        """Cached adapter instance for `name`.

        Falls back to the highest-priority configured provider when no name is
        given, so callers that don't care (health checks, admin views) always
        get something sensible.
        """
        key = (name or "").strip().lower() or self.default_provider_name()
        config = self._fleet.get(key)

        with self._lock:
            cached = self._instances.get(key)
            if cached is not None:
                return cached

            factory = self._factories.get(key)
            if factory is None:
                raise UnknownProviderError(
                    f"No adapter registered for AI provider '{key}'. Known adapters: "
                    f"{', '.join(sorted(self._factories))}."
                )
            if config is None:
                # Adapter exists but the name isn't declared in providers.yaml.
                # Build it with an empty config so its own defaults apply and
                # `is_available()` reports the missing credential clearly.
                config = ProviderConfig(name=key, enabled=True)
                logger.warning(
                    "Provider '%s' is not declared in providers.yaml — using adapter defaults.",
                    key,
                )
            instance = factory(config)
            self._instances[key] = instance
            return instance

    def default_provider_name(self) -> str:
        """Highest-priority provider that is actually usable, else the
        highest-priority declared one so status pages still have something
        to show."""
        chain = self._fleet.failover_chain()
        if chain:
            return chain[0].name
        ordered = self._fleet.ordered()
        return ordered[0].name if ordered else "groq"

    def config_for(self, name: str) -> Optional[ProviderConfig]:
        return self._fleet.get(name)

    @property
    def fleet(self) -> FleetConfig:
        return self._fleet

    def available_providers(self) -> List[str]:
        """Providers that are declared, enabled, and hold a usable credential."""
        return [p.name for p in self._fleet.failover_chain()]

    def registered_adapters(self) -> List[str]:
        return sorted(self._factories)

    def reload(self, fleet: Optional[FleetConfig] = None) -> None:
        """Re-read configuration and drop cached adapters (admin action/tests)."""
        with self._lock:
            self._fleet = fleet or get_fleet_config()
            self._instances.clear()


_provider_router: Optional[ProviderRouter] = None


def get_provider_router() -> ProviderRouter:
    global _provider_router
    if _provider_router is None:
        _provider_router = ProviderRouter()
    return _provider_router


def get_provider(name: str = "") -> BaseAIProvider:
    """Backward-compatible wrapper around `ProviderRouter.resolve()`."""
    return get_provider_router().resolve(name)
