"""
HuggingFace Inference provider — priority 4, the last resort in the chain.

HuggingFace's Inference Providers router (`router.huggingface.co/v1`) speaks
the OpenAI Chat Completions protocol, so this reuses the shared transport.

Two HuggingFace-specific behaviors are worth knowing:

* **Cold starts.** Serverless models return HTTP 503 with an
  `estimated_time` while weights load. The shared client maps 503 to
  `ProviderUnavailableError`, which is retried with backoff — exactly the
  right behavior for a model that is warming up.
* **Model ids are repo paths** (`mistralai/Mistral-7B-Instruct-v0.3`), not
  short names, so a typo surfaces as 404 -> `ModelNotFoundError` -> failover
  rather than a confusing hang.
"""
from __future__ import annotations

from typing import Optional, Sequence, Tuple

from app.ai.orchestrator.providers.openai_compatible import OpenAICompatibleProvider


class HuggingFaceProvider(OpenAICompatibleProvider):
    name = "huggingface"
    default_base_url = "https://router.huggingface.co/v1"
    api_key_env = "HUGGINGFACE_API_KEY"
    console_url = "https://huggingface.co/settings/tokens"

    quota_markers: Sequence[str] = (
        "monthly",
        "per month",
        "quota",
        "credits",
        "exceeded your",
        "subscribe to pro",
    )

    def _probe_without_model_list(self) -> Tuple[bool, Optional[str]]:
        """The HF router serves thousands of models and its `/models` listing
        is large and occasionally unavailable. An empty list here means
        "couldn't enumerate", not "no models" — so when a token is present we
        report the provider as reachable-but-unverified instead of marking a
        working fallback as offline."""
        if self.api_key:
            return True, (
                "Connected, but the model list could not be enumerated — "
                "model availability will be confirmed on first use."
            )
        return False, self._credential_hint()
