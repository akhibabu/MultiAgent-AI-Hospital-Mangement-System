"""Diagnosis Agent — Step 2: Differential Diagnosis."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.diagnosis.knowledge_base import ConditionKnowledgeBase
from app.ai.diagnosis.models import DifferentialDiagnosis, SymptomAnalysis
from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.repositories.patient_context_repository import PatientClinicalContext


class _DifferentialDiagnosisList(BaseModel):
    items: List[DifferentialDiagnosis] = Field(default_factory=list)


class DifferentialDiagnosisStrategy(ABC):
    """Strategy interface — pluggable differential-diagnosis engines."""

    @abstractmethod
    def generate(
        self,
        context: PatientClinicalContext,
        symptom_analysis: SymptomAnalysis,
    ) -> List[DifferentialDiagnosis]: ...


class RuleBasedDifferentialStrategy(DifferentialDiagnosisStrategy):
    """Matches symptoms/labs/vitals/history against the condition knowledge base."""

    def __init__(self, knowledge_base: ConditionKnowledgeBase | None = None) -> None:
        self._kb = knowledge_base or ConditionKnowledgeBase()

    def generate(
        self,
        context: PatientClinicalContext,
        symptom_analysis: SymptomAnalysis,
    ) -> List[DifferentialDiagnosis]:
        symptom_set = {s.lower() for s in context.symptoms}
        lab_names = {
            str(l.get("name", "")).lower()
            for l in context.lab_values
            if isinstance(l, dict)
        }
        lab_names |= {str(t).lower() for t in context.lab_tests}
        history_terms = {c.lower() for c in context.previous_diagnoses}
        history_terms |= {c.lower() for c in context.conditions}

        results: List[DifferentialDiagnosis] = []
        for profile in self._kb.all_profiles():
            symptom_hits = [
                s for s in profile.symptoms if any(s in sym or sym in s for sym in symptom_set)
            ]
            lab_hits = [
                l for l in profile.labs if any(l in lab or lab in l for lab in lab_names)
            ]
            history_hits = [
                profile.condition
            ] if any(
                profile.condition.lower() in h or h in profile.condition.lower()
                for h in history_terms
            ) else []

            if not symptom_hits and not lab_hits and not history_hits:
                continue

            symptom_score = len(symptom_hits) / max(1, len(profile.symptoms))
            lab_score = len(lab_hits) / max(1, len(profile.labs)) if profile.labs else 0.0
            history_score = 1.0 if history_hits else 0.0

            confidence = min(
                0.98,
                round(
                    symptom_score * 0.55 + lab_score * 0.3 + history_score * 0.15,
                    3,
                ),
            )
            if confidence <= 0:
                continue

            contradicting: List[str] = []
            missing_core = [s for s in profile.symptoms[:3] if s not in symptom_hits]
            if missing_core and symptom_hits:
                contradicting.append(
                    f"Core symptoms not observed: {', '.join(missing_core)}"
                )
            if not lab_hits and profile.labs:
                contradicting.append("No supporting lab values recognized yet")

            results.append(
                DifferentialDiagnosis(
                    condition=profile.condition,
                    confidence=confidence,
                    supporting_symptoms=symptom_hits,
                    supporting_labs=lab_hits,
                    supporting_history=history_hits,
                    contradicting_evidence=contradicting,
                    recommended_specialists=list(profile.specialists),
                    body_system=profile.body_system,
                )
            )

        results.sort(key=lambda d: d.confidence, reverse=True)
        return results[:10]


class LLMDifferentialStrategy(OrchestratorCallMixin, DifferentialDiagnosisStrategy):
    """
    Delegates differential-diagnosis generation to the AI Orchestrator
    (`diagnosis` agent, `differential_diagnosis` task). The
    `ConditionKnowledgeBase` (body-system/symptom/lab profiles) is passed
    in as grounding data via the Knowledge Graph / patient context rather
    than making the decision itself.
    """

    def __init__(self, knowledge_base: ConditionKnowledgeBase | None = None) -> None:
        self._kb = knowledge_base or ConditionKnowledgeBase()

    def generate(
        self,
        context: PatientClinicalContext,
        symptom_analysis: SymptomAnalysis,
    ) -> List[DifferentialDiagnosis]:
        data = self._call(
            agent="diagnosis",
            task="differential_diagnosis",
            patient_id=UUID(context.patient_id),
            response_model=_DifferentialDiagnosisList,
            extra_vars={"symptom_analysis": symptom_analysis.model_dump(mode="json")},
        )
        return _DifferentialDiagnosisList.model_validate(data).items[:10]


class DifferentialDiagnosisEngine:
    """Facade selecting a DifferentialDiagnosisStrategy (default: AI Orchestrator-backed)."""

    def __init__(self, strategy: DifferentialDiagnosisStrategy | None = None) -> None:
        self._strategy = strategy or LLMDifferentialStrategy()

    def generate(
        self,
        context: PatientClinicalContext,
        symptom_analysis: SymptomAnalysis,
    ) -> List[DifferentialDiagnosis]:
        return self._strategy.generate(context, symptom_analysis)

    @property
    def last_debug(self):
        return getattr(self._strategy, "last_debug", None)
