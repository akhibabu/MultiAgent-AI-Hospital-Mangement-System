"""
Provider package — concrete `BaseAIProvider` adapters.

The actual config-driven provider *selection* logic lives in
`app.ai.orchestrator.provider_router.ProviderRouter` (the "Provider
Router" architectural step). `get_provider()` is re-exported here only
for backward compatibility with existing call sites
(`from app.ai.orchestrator.providers import get_provider`) — new code
should prefer `from app.ai.orchestrator.provider_router import
get_provider_router`.

`AI_PROVIDER=groq` is the default provider. `ollama` / `openai` /
`gemini` / `anthropic` are fully implemented, pluggable alternatives —
switching is a configuration change only, no AI Agent or orchestrator
code needs to change. `stub` is a deterministic offline provider used
only by automated tests / local dev without any real API key.
"""
from __future__ import annotations

from app.ai.orchestrator.provider_router import get_provider, get_provider_router

__all__ = ["get_provider", "get_provider_router"]
