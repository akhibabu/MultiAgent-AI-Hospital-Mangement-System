"""Factory selecting Diagnosis Agent strategy implementations by settings."""

from __future__ import annotations

from app.ai.diagnosis.differential_engine import (
    DifferentialDiagnosisStrategy,
    RuleBasedDifferentialStrategy,
)
from app.ai.diagnosis.knowledge_base import ConditionKnowledgeBase
from app.ai.diagnosis.symptom_analyzer import (
    RuleBasedSymptomAnalyzer,
    SymptomAnalysisStrategy,
)


class DiagnosisStrategyFactory:
    """
    Resolves engine implementations from `settings.diagnosis_engine`.

    Today only `rule_based` is implemented. Future engines (e.g. `llm`) can be
    registered here without changing pipeline or route code.
    """

    def __init__(self, engine: str = "rule_based") -> None:
        self._engine = (engine or "rule_based").strip().lower()
        self._kb = ConditionKnowledgeBase()

    @property
    def engine_name(self) -> str:
        return self._engine

    def create_symptom_strategy(self) -> SymptomAnalysisStrategy:
        if self._engine in {"rule_based", "stub", "default"}:
            return RuleBasedSymptomAnalyzer(self._kb)
        raise ValueError(f"Unknown DIAGNOSIS_ENGINE '{self._engine}'")

    def create_differential_strategy(self) -> DifferentialDiagnosisStrategy:
        if self._engine in {"rule_based", "stub", "default"}:
            return RuleBasedDifferentialStrategy(self._kb)
        raise ValueError(f"Unknown DIAGNOSIS_ENGINE '{self._engine}'")

    def knowledge_base(self) -> ConditionKnowledgeBase:
        return self._kb


def get_diagnosis_strategy_factory() -> DiagnosisStrategyFactory:
    from app.config import get_settings

    settings = get_settings()
    return DiagnosisStrategyFactory(getattr(settings, "diagnosis_engine", "rule_based"))
