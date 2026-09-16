"""Factory selecting Diagnosis Agent strategy implementations.

Every stage now delegates its reasoning to the AI Orchestrator (see
`app/ai/orchestrator/`). `ConditionKnowledgeBase` remains available as
grounding/reference data for prompt context — it no longer makes the
diagnostic decision itself. This factory is kept (rather than
constructing strategies inline) so a future strategy — e.g. a
hybrid/ensemble approach — can be registered here without touching
`pipeline.py` or any route code.
"""
from __future__ import annotations

from app.ai.diagnosis.differential_engine import (
    DifferentialDiagnosisStrategy,
    LLMDifferentialStrategy,
)
from app.ai.diagnosis.knowledge_base import ConditionKnowledgeBase
from app.ai.diagnosis.symptom_analyzer import (
    LLMSymptomAnalysisStrategy,
    SymptomAnalysisStrategy,
)


class DiagnosisStrategyFactory:
    """Resolves the active (AI Orchestrator-backed) strategy implementations."""

    def __init__(self, engine: str = "ai_orchestrator") -> None:
        self._engine = (engine or "ai_orchestrator").strip().lower()
        self._kb = ConditionKnowledgeBase()

    @property
    def engine_name(self) -> str:
        return self._engine

    def create_symptom_strategy(self) -> SymptomAnalysisStrategy:
        return LLMSymptomAnalysisStrategy()

    def create_differential_strategy(self) -> DifferentialDiagnosisStrategy:
        return LLMDifferentialStrategy(self._kb)

    def knowledge_base(self) -> ConditionKnowledgeBase:
        return self._kb


def get_diagnosis_strategy_factory() -> DiagnosisStrategyFactory:
    return DiagnosisStrategyFactory("ai_orchestrator")
