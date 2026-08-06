"""Diagnosis Agent — Step 1: Symptom Analysis."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from uuid import UUID

from app.ai.diagnosis.knowledge_base import ConditionKnowledgeBase
from app.ai.diagnosis.models import SymptomAnalysis, SymptomCluster
from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.repositories.patient_context_repository import PatientClinicalContext

_DURATION_PATTERN = re.compile(
    r"(\d+\s*(?:day|days|week|weeks|month|months|year|years|hour|hours))",
    re.IGNORECASE,
)
_SEVERITY_WORDS = ("mild", "moderate", "severe", "acute", "chronic", "intermittent")


class SymptomAnalysisStrategy(ABC):
    """Strategy interface — pluggable symptom analysis engines."""

    @abstractmethod
    def analyze(self, context: PatientClinicalContext) -> SymptomAnalysis: ...


class RuleBasedSymptomAnalyzer(SymptomAnalysisStrategy):
    """Clusters symptoms by body system using the condition knowledge base."""

    def __init__(self, knowledge_base: ConditionKnowledgeBase | None = None) -> None:
        self._kb = knowledge_base or ConditionKnowledgeBase()

    def analyze(self, context: PatientClinicalContext) -> SymptomAnalysis:
        symptoms = [s for s in context.symptoms if isinstance(s, str) and s.strip()]
        text = " ".join(
            [context.medical_history_summary]
            + [str(t.get("detail", "")) for t in context.timeline if isinstance(t, dict)]
        ).lower()

        duration_hint = None
        match = _DURATION_PATTERN.search(text)
        if match:
            duration_hint = match.group(1)

        severity_hint = next((w for w in _SEVERITY_WORDS if w in text), None)

        clusters_by_system: Dict[str, SymptomCluster] = {}
        unclustered: List[str] = []

        for symptom in symptoms:
            matches = self._kb.match_symptom(symptom)
            if not matches:
                unclustered.append(symptom)
                continue
            for profile in matches:
                cluster = clusters_by_system.setdefault(
                    profile.body_system,
                    SymptomCluster(
                        body_system=profile.body_system,
                        duration_hint=duration_hint,
                        severity_hint=severity_hint,
                    ),
                )
                if symptom not in cluster.symptoms:
                    cluster.symptoms.append(symptom)
                if profile.condition not in cluster.related_conditions:
                    cluster.related_conditions.append(profile.condition)

        if unclustered:
            clusters_by_system.setdefault(
                "General / Unclassified",
                SymptomCluster(
                    body_system="General / Unclassified",
                    duration_hint=duration_hint,
                    severity_hint=severity_hint,
                ),
            ).symptoms.extend(unclustered)

        clusters = sorted(
            clusters_by_system.values(),
            key=lambda c: len(c.symptoms),
            reverse=True,
        )

        narrative = self._narrative(context, clusters, duration_hint, severity_hint)

        return SymptomAnalysis(
            clusters=clusters,
            total_symptoms=len(symptoms),
            notable_vitals=[v for v in context.vitals if isinstance(v, dict)][:10],
            notable_labs=[l for l in context.lab_values if isinstance(l, dict)][:10],
            narrative=narrative,
        )

    @staticmethod
    def _narrative(
        context: PatientClinicalContext,
        clusters: List[SymptomCluster],
        duration_hint: str | None,
        severity_hint: str | None,
    ) -> str:
        if not clusters:
            return (
                f"No recognized symptoms available for {context.patient_name}. "
                "Differential diagnosis will rely primarily on history and risk profile."
            )
        systems = ", ".join(c.body_system for c in clusters[:4])
        pieces = [
            f"{len(context.symptoms)} recognized symptom(s) span {systems} systems."
        ]
        if duration_hint:
            pieces.append(f"Reported duration: approximately {duration_hint}.")
        if severity_hint:
            pieces.append(f"Severity descriptor noted: {severity_hint}.")
        return " ".join(pieces)


class LLMSymptomAnalysisStrategy(OrchestratorCallMixin, SymptomAnalysisStrategy):
    """
    Delegates symptom clustering to the AI Orchestrator (`diagnosis` agent,
    `symptom_analysis` task) instead of the rule-based body-system matcher.

    The rule-based `ConditionKnowledgeBase` is still used elsewhere as
    grounding data (see `differential_engine.py`), but this stage's actual
    reasoning now comes from the LLM via the orchestrator.
    """

    def analyze(self, context: PatientClinicalContext) -> SymptomAnalysis:
        data = self._call(
            agent="diagnosis",
            task="symptom_analysis",
            patient_id=UUID(context.patient_id),
            response_model=SymptomAnalysis,
        )
        return SymptomAnalysis.model_validate(data)


class SymptomAnalyzer:
    """Facade selecting a SymptomAnalysisStrategy (default: AI Orchestrator-backed)."""

    def __init__(self, strategy: SymptomAnalysisStrategy | None = None) -> None:
        self._strategy = strategy or LLMSymptomAnalysisStrategy()

    def analyze(self, context: PatientClinicalContext) -> SymptomAnalysis:
        return self._strategy.analyze(context)

    @property
    def last_debug(self):
        return getattr(self._strategy, "last_debug", None)
