"""Re-exports the provider contract so `providers/*.py` don't reach into `interfaces` directly."""
from __future__ import annotations

from app.ai.orchestrator.interfaces import (
    BaseAIProvider,
    IAIProvider,
    ProviderCompletion,
    ProviderMessage,
)

__all__ = ["BaseAIProvider", "IAIProvider", "ProviderCompletion", "ProviderMessage"]
