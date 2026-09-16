"""
OpenRouter provider — priority 3 in the default failover chain.

OpenRouter is a gateway in front of many model vendors, exposing a single
OpenAI-compatible API. That makes it a strong third fallback: even when Groq
and Gemini are both rate limited, OpenRouter's `:free` model tier usually
still answers.

Beyond the shared transport it needs two attribution headers (OpenRouter
uses them for its public app leaderboard and for per-app rate limiting) and
it signals exhausted credits with HTTP 402, which the shared client already
maps to `QuotaExceededError`.
"""
from __future__ import annotations

from typing import Dict, Sequence

from app.ai.orchestrator.providers.openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    name = "openrouter"
    default_base_url = "https://openrouter.ai/api/v1"
    api_key_env = "OPENROUTER_API_KEY"
    console_url = "https://openrouter.ai/keys"

    quota_markers: Sequence[str] = (
        "per day",
        "daily",
        "quota",
        "credits",
        "insufficient",
        "free-models-per-day",
    )

    def _extra_headers(self) -> Dict[str, str]:
        # Optional but recommended by OpenRouter; identifies the calling app.
        referer = str(self.config.extra.get("referer", "")) if self.config else ""
        title = str(self.config.extra.get("title", "")) if self.config else ""
        return {
            "HTTP-Referer": referer or "http://localhost:5173",
            "X-Title": title or "Hospital AI",
        }
