"""
OpenAI provider — fully implemented, disabled by default in `providers.yaml`
because it needs paid credentials.

Enable it by setting `OPENAI_API_KEY` and `OPENAI_ENABLED=true`; it then
joins the failover chain at its configured priority with no code change
anywhere else in the system.
"""
from __future__ import annotations

from typing import Sequence

from app.ai.orchestrator.providers.openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    default_base_url = "https://api.openai.com/v1"
    api_key_env = "OPENAI_API_KEY"
    console_url = "https://platform.openai.com/api-keys"

    quota_markers: Sequence[str] = (
        "insufficient_quota",
        "billing",
        "exceeded your current quota",
        "per day",
        "credits",
    )
