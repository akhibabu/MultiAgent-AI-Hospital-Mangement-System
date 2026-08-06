"""Factory selecting Prescription Agent strategy implementations.

Medication selection now delegates to the AI Orchestrator (see
`app/ai/orchestrator/`). `DrugKnowledgeBase` remains available as
grounding/reference data (and as a deterministic safety cross-check
layer for interactions/allergies elsewhere in the pipeline) — it no
longer makes the medication-selection decision itself. This factory is
kept so a future strategy can be registered here without touching
`pipeline.py` or any route code.
"""
from __future__ import annotations

from app.ai.prescription.knowledge_base import DrugKnowledgeBase
from app.ai.prescription.medication_selector import (
    LLMMedicationSelector,
    MedicationSelectionStrategy,
)


class PrescriptionStrategyFactory:
    def __init__(self, engine: str = "ai_orchestrator") -> None:
        self._engine = (engine or "ai_orchestrator").strip().lower()
        self._kb = DrugKnowledgeBase()

    @property
    def engine_name(self) -> str:
        return self._engine

    def create_medication_selector(self) -> MedicationSelectionStrategy:
        return LLMMedicationSelector(self._kb)

    def knowledge_base(self) -> DrugKnowledgeBase:
        return self._kb


def get_prescription_strategy_factory() -> PrescriptionStrategyFactory:
    return PrescriptionStrategyFactory("ai_orchestrator")
