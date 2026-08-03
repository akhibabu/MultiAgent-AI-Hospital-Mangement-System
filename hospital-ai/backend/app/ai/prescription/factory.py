"""Factory selecting Prescription Agent strategy implementations by settings."""

from __future__ import annotations

from app.ai.prescription.knowledge_base import DrugKnowledgeBase
from app.ai.prescription.medication_selector import (
    MedicationSelectionStrategy,
    RuleBasedMedicationSelector,
)


class PrescriptionStrategyFactory:
    """
    Resolves engine implementations from `settings.prescription_engine`.

    Today only `rule_based` is implemented. Future engines (e.g. `llm`, or a
    real pharmacy database provider) can be registered here without changing
    pipeline or route code.
    """

    def __init__(self, engine: str = "rule_based") -> None:
        self._engine = (engine or "rule_based").strip().lower()
        self._kb = DrugKnowledgeBase()

    @property
    def engine_name(self) -> str:
        return self._engine

    def create_medication_selector(self) -> MedicationSelectionStrategy:
        if self._engine in {"rule_based", "stub", "default"}:
            return RuleBasedMedicationSelector(self._kb)
        raise ValueError(f"Unknown PRESCRIPTION_ENGINE '{self._engine}'")

    def knowledge_base(self) -> DrugKnowledgeBase:
        return self._kb


def get_prescription_strategy_factory() -> PrescriptionStrategyFactory:
    from app.config import get_settings

    settings = get_settings()
    return PrescriptionStrategyFactory(getattr(settings, "prescription_engine", "rule_based"))
