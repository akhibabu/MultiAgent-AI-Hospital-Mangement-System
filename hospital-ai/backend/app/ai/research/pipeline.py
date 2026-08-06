"""
Research Agent — sequential pipeline.

Diagnosis Results -> 1. PubMed Search -> 2. Clinical Trial Search ->
3. Treatment Guideline Retrieval -> 4. Drug Efficacy Analysis ->
5. Evidence Ranking -> 6. Recommendation Generation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.orchestrator.agent_helpers import collect_debug
from app.ai.research.evidence_ranker import EvidenceRankingStrategy, LLMEvidenceRanker
from app.ai.research.models import ResearchReport
from app.ai.research.providers.factory import (
    ResearchProviderBundle,
    get_research_provider_bundle,
)
from app.ai.research.recommendation_generator import RecommendationGenerator
from app.core.logging import get_logger
from app.repositories.diagnosis_repository import DiagnosisResultRepository
from app.repositories.patient_context_repository import (
    PatientClinicalContextRepository,
)

logger = get_logger("hospital_ai.research.pipeline")

_MAX_CONDITIONS = 3
_MAX_DRUGS_PER_CONDITION = 2


class ResearchPipeline:
    """Orchestrates the six-module Research Agent pipeline."""

    def __init__(
        self,
        *,
        diagnosis_repo: Optional[DiagnosisResultRepository] = None,
        context_repo: Optional[PatientClinicalContextRepository] = None,
        provider_bundle: Optional[ResearchProviderBundle] = None,
        evidence_ranker: Optional[EvidenceRankingStrategy] = None,
        recommendation_generator: Optional[RecommendationGenerator] = None,
    ) -> None:
        self._diagnosis_repo = diagnosis_repo or DiagnosisResultRepository()
        self._context_repo = context_repo or PatientClinicalContextRepository()
        # `provider_bundle` / `evidence_ranker` / `recommendation_generator`
        # are only pre-built here if the caller injects them explicitly
        # (e.g. tests). In normal operation they are built per-run inside
        # `run()`, bound to that call's `patient_id`, so every AI
        # Orchestrator call is attributed to the right patient.
        self._injected_providers = provider_bundle
        self._injected_ranker = evidence_ranker
        self._injected_recommender = recommendation_generator

    def run(
        self,
        patient_id: UUID,
        *,
        diagnosis_result_id: Optional[UUID] = None,
    ) -> ResearchReport:
        self._providers = self._injected_providers or get_research_provider_bundle(patient_id)
        self._ranker = self._injected_ranker or LLMEvidenceRanker(patient_id)
        self._recommender = self._injected_recommender or RecommendationGenerator(patient_id)

        diagnosis_row = self._load_diagnosis(patient_id, diagnosis_result_id)
        context = self._context_repo.load(patient_id)

        conditions = self._top_conditions(diagnosis_row)
        if not conditions:
            conditions = context.conditions[:_MAX_CONDITIONS]

        warnings: List[str] = []
        if not diagnosis_row:
            warnings.append(
                "No Diagnosis Agent result found for this patient — researching "
                "recorded conditions from Patient Context instead."
            )
        if not conditions:
            warnings.append(
                "No conditions available to research. Run the Diagnosis Agent first."
            )

        pubmed_results = []
        clinical_trials = []
        guidelines = []
        drug_efficacy = []

        current_drugs = [
            str(m.get("name")) if isinstance(m, dict) else str(m)
            for m in context.medications
            if (m.get("name") if isinstance(m, dict) else m)
        ]

        for condition in conditions:
            # 1. PubMed Search
            pubmed_results.extend(self._providers.pubmed.search(condition, limit=4))
            # 2. Clinical Trial Search
            clinical_trials.extend(self._providers.clinical_trials.search(condition, limit=3))
            # 3. Treatment Guideline Retrieval
            guidelines.extend(self._providers.guidelines.get_guidelines(condition, limit=3))
            # 4. Drug Efficacy Analysis (published evidence only — no prescribing)
            typical_drugs = self._providers.medical_knowledge.typical_drugs_for(condition)
            drugs_to_analyze = list(dict.fromkeys(current_drugs + typical_drugs))[
                :_MAX_DRUGS_PER_CONDITION
            ]
            for drug in drugs_to_analyze:
                drug_efficacy.append(self._providers.drug_evidence.analyze(drug, condition))

        # 5. Evidence Ranking
        ranked_evidence = self._ranker.rank(
            literature=pubmed_results,
            trials=clinical_trials,
            guidelines=guidelines,
            drug_evidence=drug_efficacy,
        )
        level_counts: Dict[str, int] = {"High": 0, "Medium": 0, "Low": 0}
        for e in ranked_evidence:
            level_counts[e.evidence_level] = level_counts.get(e.evidence_level, 0) + 1

        # 6. Recommendation Generation
        recommendations = [
            self._recommender.generate(condition, ranked_evidence) for condition in conditions
        ]

        summary = self._build_summary(conditions, ranked_evidence, level_counts)

        ai_debug = collect_debug(
            self._providers.pubmed,
            self._providers.clinical_trials,
            self._providers.guidelines,
            self._providers.drug_evidence,
            self._ranker,
            self._recommender,
        )

        logger.info(
            "Research pipeline complete patient=%s conditions=%s evidence=%s",
            patient_id,
            len(conditions),
            len(ranked_evidence),
        )

        return ResearchReport(
            patient_id=str(patient_id),
            diagnosis_result_id=str(diagnosis_row["id"]) if diagnosis_row else None,
            conditions_researched=conditions,
            pubmed_results=pubmed_results,
            clinical_trials=clinical_trials,
            guidelines=guidelines,
            drug_efficacy=drug_efficacy,
            ranked_evidence=ranked_evidence,
            evidence_level_counts=level_counts,
            recommendations=recommendations,
            summary=summary,
            provider=self._providers.provider_name,
            warnings=warnings,
            ai_debug=ai_debug,
        )

    def _load_diagnosis(
        self, patient_id: UUID, diagnosis_result_id: Optional[UUID]
    ) -> Optional[Dict[str, Any]]:
        if diagnosis_result_id:
            row = self._diagnosis_repo.get_by_id(diagnosis_result_id)
            if not row:
                raise HTTPException(status_code=404, detail="Diagnosis result not found")
            return row
        return self._diagnosis_repo.get_latest_for_patient(patient_id)

    @staticmethod
    def _top_conditions(diagnosis_row: Optional[Dict[str, Any]]) -> List[str]:
        if not diagnosis_row:
            return []
        probs = diagnosis_row.get("probability_scores_json") or []
        conditions = [p.get("condition") for p in probs if isinstance(p, dict) and p.get("condition")]
        return conditions[:_MAX_CONDITIONS]

    @staticmethod
    def _build_summary(
        conditions: List[str],
        ranked_evidence: List[Any],
        level_counts: Dict[str, int],
    ) -> str:
        if not conditions:
            return (
                "No conditions were available to research. Run the Diagnosis "
                "Agent first, or ensure Patient Context includes recognized conditions."
            )
        cond_text = ", ".join(conditions)
        return (
            f"Research Agent reviewed {len(ranked_evidence)} evidence item(s) for "
            f"{cond_text} — {level_counts.get('High', 0)} high, "
            f"{level_counts.get('Medium', 0)} medium, {level_counts.get('Low', 0)} low "
            "confidence. Evidence summary only — verify with primary sources."
        )
