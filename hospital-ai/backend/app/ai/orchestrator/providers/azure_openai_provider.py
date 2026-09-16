"""
Azure OpenAI provider — implemented, disabled by default.

Azure differs from stock OpenAI in three ways, all handled here so the rest
of the system stays provider-agnostic:

1. **Deployment-scoped URLs.** Requests go to
   `{endpoint}/openai/deployments/{deployment}/chat/completions`, where the
   deployment name is chosen by whoever provisioned the resource. If no
   deployment is configured we fall back to using the routed model name,
   which is the common convention.
2. **`api-key` header** instead of `Authorization: Bearer`.
3. **Mandatory `api-version` query parameter.**

Configure via `providers.yaml` (`azure_openai.extra.deployment` /
`.api_version`) plus `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY`.
"""
from __future__ import annotations

from typing import Dict, Sequence

from app.ai.orchestrator.providers.openai_compatible import OpenAICompatibleProvider


class AzureOpenAIProvider(OpenAICompatibleProvider):
    name = "azure_openai"
    default_base_url = ""
    api_key_env = "AZURE_OPENAI_API_KEY"
    console_url = "https://portal.azure.com"

    quota_markers: Sequence[str] = ("quota", "per day", "billing", "exceeded")

    DEFAULT_API_VERSION = "2024-10-21"

    @property
    def _api_version(self) -> str:
        extra = getattr(self.config, "extra", {}) if self.config else {}
        return str(extra.get("api_version") or self.DEFAULT_API_VERSION)

    @property
    def _deployment(self) -> str:
        extra = getattr(self.config, "extra", {}) if self.config else {}
        return str(extra.get("deployment") or "")

    def _chat_endpoint(self, model: str) -> str:
        deployment = self._deployment or model
        return (
            f"{self.base_url}/openai/deployments/{deployment}/chat/completions"
            f"?api-version={self._api_version}"
        )

    def _headers(self) -> Dict[str, str]:
        headers = super()._headers()
        # Azure authenticates with `api-key`, not a bearer token.
        headers.pop("Authorization", None)
        headers["api-key"] = self.api_key
        return headers

    def list_models(self) -> list[str]:
        """Azure exposes deployments, not a public model catalogue, and the
        management API needs separate credentials. Returning the configured
        deployment keeps health checks meaningful without a second auth flow."""
        deployment = self._deployment
        return [deployment] if deployment else []

    def health_check(self, model: str):
        if not self.api_key:
            return False, self._credential_hint()
        if not self.base_url:
            return False, "AZURE_OPENAI_ENDPOINT is not configured."
        return True, None
