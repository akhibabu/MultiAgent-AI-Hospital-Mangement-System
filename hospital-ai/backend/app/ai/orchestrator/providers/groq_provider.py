"""
Groq provider — priority 1 in the default failover chain.

Groq hosts open-weight models (Llama 3.3, etc.) behind an OpenAI-compatible
Chat Completions API, so the transport, error mapping, streaming, and token
accounting all come from `OpenAICompatibleProvider`. Only the Groq-specific
identity and quota wording live here.

Nothing outside `ProviderRouter` constructs this class, and nothing outside
`ProviderOrchestrator` calls it — no AI Agent talks to Groq, or knows Groq
exists. If Groq's daily token quota is exhausted the orchestrator fails over
to Gemini, then OpenRouter, then HuggingFace, with no agent-visible change.
"""
from __future__ import annotations

from typing import Sequence

from app.ai.orchestrator.providers.openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    name = "groq"
    default_base_url = "https://api.groq.com/openai/v1"
    api_key_env = "GROQ_API_KEY"
    console_url = "https://console.groq.com/keys"

    # Groq's free tier enforces tokens-per-day (TPD) and requests-per-day
    # (RPD) alongside per-minute limits; both arrive as HTTP 429, and only
    # the per-minute ones are worth retrying in place.
    quota_markers: Sequence[str] = (
        "per day",
        "tpd",
        "rpd",
        "daily",
        "quota",
        "tokens per month",
    )
