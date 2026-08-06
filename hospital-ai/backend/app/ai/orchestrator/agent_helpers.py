"""
Small helper mixin used by every AI Agent's LLM-backed strategy/generator
classes (Diagnosis, Research, Prescription, Medical Report).

Each pipeline stage calls the orchestrator exactly once per
`analyze()` / `generate()` / `recommend()` / etc. call. This mixin
captures the returned `OrchestratorDebugInfo` on the instance
(`self.last_debug`) so the owning pipeline can collect one `ai_debug`
entry per stage for the aggregate report and the frontend "Developer
Mode" panel, without every strategy class re-implementing that
bookkeeping.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Type
from uuid import UUID

from pydantic import BaseModel

from app.ai.orchestrator import get_orchestrator
from app.ai.orchestrator.models import OrchestratorDebugInfo


class OrchestratorCallMixin:
    """
    Mix into any Strategy/Generator/Provider class that calls the
    orchestrator.

    Tracks EVERY call made through this instance in `debug_history`
    (not just the most recent one) — some stages call the orchestrator
    once per loop iteration (e.g. once per researched condition, once
    per suggested medication), and every call should still show up in
    the aggregate report's Developer Mode panel.
    """

    last_debug: Optional[OrchestratorDebugInfo] = None
    debug_history: Optional[List[OrchestratorDebugInfo]] = None

    def _call(
        self,
        *,
        agent: str,
        task: str,
        patient_id: Optional[UUID],
        response_model: Optional[Type[BaseModel]] = None,
        extra_vars: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        response = get_orchestrator().run(
            agent=agent,
            task=task,
            patient_id=patient_id,
            response_model=response_model,
            extra_vars=extra_vars,
            use_cache=use_cache,
        )
        self.last_debug = response.debug
        if self.debug_history is None:
            self.debug_history = []
        self.debug_history.append(response.debug)
        return response.data


def collect_debug(*components: Any) -> List[OrchestratorDebugInfo]:
    """Gathers every orchestrator call's debug info from any number of instances."""
    debug_entries: List[OrchestratorDebugInfo] = []
    for component in components:
        if component is None:
            continue
        history = getattr(component, "debug_history", None)
        if history:
            debug_entries.extend(history)
        elif getattr(component, "last_debug", None) is not None:
            debug_entries.append(component.last_debug)
    return debug_entries
