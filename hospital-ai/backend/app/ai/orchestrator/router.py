"""
ModelRouter — decides which model serves a given agent on a given provider.

    Intake Agent         -> INTAKE_MODEL
    Diagnosis Agent      -> DIAGNOSIS_MODEL
    Research Agent       -> RESEARCH_MODEL
    Prescription Agent   -> PRESCRIPTION_MODEL
    Medical Report Agent -> REPORT_MODEL

Model selection is per (agent, provider), not just per agent, because the
failover chain spans vendors with completely different model catalogues:
Groq answers a diagnosis request with `llama-3.3-70b-versatile`, and if Groq
is out of quota Gemini answers the same request with `gemini-2.5-flash`. The
AI Agent asks for neither — it names a *task*, and this router resolves the
model for whichever provider ends up serving it.

Models come from `providers.yaml` (`providers.<name>.models`), where the
per-agent entries interpolate the classic `DIAGNOSIS_MODEL`-style env vars,
so existing `.env` files keep working unchanged. `Settings` is consulted only
as a last-resort fallback when the YAML is unavailable.

Adding an agent = one entry in `_MODEL_SETTING_MAP` plus a line in
`providers.yaml`. No pipeline code in any agent ever changes.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from app.ai.orchestrator.interfaces import IModelRouter
from app.ai.orchestrator.providers.config import FleetConfig, get_fleet_config


class ModelRouter(IModelRouter):
    #: Agent -> the `Settings` field holding its fallback model.
    _MODEL_SETTING_MAP = {
        "intake": "intake_model",
        "diagnosis": "diagnosis_model",
        "research": "research_model",
        "prescription": "prescription_model",
        "medical_report": "report_model",
    }

    def __init__(
        self,
        settings: Optional[object] = None,
        fleet: Optional[FleetConfig] = None,
    ) -> None:
        self._settings = settings
        self._fleet = fleet

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------
    def resolve(self, agent: str) -> Tuple[str, str]:
        """`(provider, model)` for the agent's *primary* provider.

        Kept for the `IModelRouter` contract and for status/admin views. The
        request path uses `resolve_for_provider()` instead, because the
        provider isn't known until the load balancer has picked one.
        """
        provider = self._default_provider()
        return provider, self.resolve_for_provider(agent, provider)

    def resolve_for_provider(self, agent: str, provider: str) -> str:
        """Model `provider` should use for `agent`.

        Returns "" when the provider declares no model for this agent, which
        the Provider Orchestrator treats as "skip this provider" rather than
        as an error — a provider that can't serve an agent simply isn't a
        candidate for it.
        """
        key = (agent or "").strip().lower()
        if key not in self._MODEL_SETTING_MAP:
            raise ValueError(
                f"No model routing configured for agent '{agent}'. Known agents: "
                f"{', '.join(self._MODEL_SETTING_MAP)}."
            )

        config = self._get_fleet().get(provider)
        if config is not None:
            model = config.model_for(key)
            if model:
                return model

        return self._settings_model(key)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def routing_table(self, provider: Optional[str] = None) -> Dict[str, str]:
        """Agent -> model for one provider (the primary by default)."""
        target = provider or self._default_provider()
        table: Dict[str, str] = {}
        for agent in self._MODEL_SETTING_MAP:
            try:
                table[agent] = self.resolve_for_provider(agent, target)
            except ValueError:
                continue
        return table

    def routing_matrix(self) -> Dict[str, Dict[str, str]]:
        """Provider -> {agent -> model} across the whole failover chain, for
        the AI Infrastructure dashboard."""
        return {
            config.name: self.routing_table(config.name)
            for config in self._get_fleet().failover_chain()
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _get_fleet(self) -> FleetConfig:
        return self._fleet or get_fleet_config()

    def _get_settings(self):
        if self._settings is not None:
            return self._settings
        from app.config import get_settings

        return get_settings()

    def _default_provider(self) -> str:
        """Highest-priority usable provider, or the pinned `AI_PROVIDER` when
        an operator has explicitly forced one (e.g. `stub` for offline dev)."""
        settings = self._get_settings()
        pinned = (getattr(settings, "ai_provider", "") or "").strip().lower()
        fleet = self._get_fleet()
        if pinned and fleet.get(pinned) is not None:
            return pinned
        chain = fleet.failover_chain()
        if chain:
            return chain[0].name
        ordered = fleet.ordered()
        return ordered[0].name if ordered else "groq"

    def _settings_model(self, agent: str) -> str:
        setting_name = self._MODEL_SETTING_MAP[agent]
        return getattr(self._get_settings(), setting_name, "") or ""


_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
