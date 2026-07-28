"""Research Agent — Step 5: Evidence Ranking."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import List

from app.ai.research.models import (
    ClinicalTrialItem,
    DrugEvidenceItem,
    GuidelineItem,
    LiteratureItem,
    RankedEvidence,
)

_JOURNAL_QUALITY = {
    "New England Journal of Medicine": 0.95,
    "The Lancet": 0.93,
    "JAMA": 0.9,
    "Annals of Internal Medicine": 0.85,
    "BMJ": 0.85,
}


class EvidenceRankingStrategy(ABC):
    """Strategy interface — pluggable evidence-ranking engines."""

    @abstractmethod
    def rank(
        self,
        *,
        literature: List[LiteratureItem],
        trials: List[ClinicalTrialItem],
        guidelines: List[GuidelineItem],
        drug_evidence: List[DrugEvidenceItem],
    ) -> List[RankedEvidence]: ...


class HeuristicEvidenceRanker(EvidenceRankingStrategy):
    """
    Ranks evidence by recency, source quality, clinical relevance, and
    confidence into High / Medium / Low evidence levels.
    """

    def rank(
        self,
        *,
        literature: List[LiteratureItem],
        trials: List[ClinicalTrialItem],
        guidelines: List[GuidelineItem],
        drug_evidence: List[DrugEvidenceItem],
    ) -> List[RankedEvidence]:
        ranked: List[RankedEvidence] = []

        for item in literature:
            recency = self._recency_score(item.publication_year)
            journal_quality = _JOURNAL_QUALITY.get(item.journal, 0.7)
            confidence = round(
                recency * 0.3 + journal_quality * 0.35 + item.relevance_score * 0.35, 3
            )
            ranked.append(
                RankedEvidence(
                    evidence_type="pubmed",
                    condition=item.condition,
                    title=item.title,
                    source=item.journal,
                    reference_id=item.reference_id,
                    url=item.url,
                    publication_date=f"{item.publication_year}-01-01",
                    summary=item.summary,
                    evidence_level=self._level(confidence),
                    relevance_score=item.relevance_score,
                    confidence=confidence,
                    raw=item.model_dump(mode="json"),
                )
            )

        for trial in trials:
            status_weight = 0.9 if trial.status == "Completed" else 0.65
            confidence = round(status_weight * 0.5 + trial.relevance_score * 0.5, 3)
            ranked.append(
                RankedEvidence(
                    evidence_type="clinical_trial",
                    condition=trial.condition,
                    title=trial.title,
                    source=f"ClinicalTrials ({trial.phase})",
                    reference_id=trial.trial_id,
                    url=trial.url,
                    publication_date=None,
                    summary=trial.outcome_summary,
                    evidence_level=self._level(confidence),
                    relevance_score=trial.relevance_score,
                    confidence=confidence,
                    raw=trial.model_dump(mode="json"),
                )
            )

        for guideline in guidelines:
            recency = self._recency_score(guideline.published_year)
            confidence = round(recency * 0.4 + guideline.relevance_score * 0.6, 3)
            ranked.append(
                RankedEvidence(
                    evidence_type="guideline",
                    condition=guideline.condition,
                    title=guideline.title,
                    source=guideline.source,
                    reference_id="",
                    url=guideline.url,
                    publication_date=f"{guideline.published_year}-01-01",
                    summary=guideline.recommendation,
                    evidence_level=self._level(confidence),
                    relevance_score=guideline.relevance_score,
                    confidence=confidence,
                    raw=guideline.model_dump(mode="json"),
                )
            )

        for drug in drug_evidence:
            confidence = round(drug.relevance_score, 3)
            ranked.append(
                RankedEvidence(
                    evidence_type="drug_efficacy",
                    condition=drug.condition,
                    title=f"Evidence review: {drug.drug_name} for {drug.condition}",
                    source="Aggregated drug evidence",
                    reference_id="",
                    url="",
                    publication_date=None,
                    summary=drug.effectiveness_summary,
                    evidence_level=self._level(confidence),
                    relevance_score=drug.relevance_score,
                    confidence=confidence,
                    raw=drug.model_dump(mode="json"),
                )
            )

        ranked.sort(key=lambda e: e.confidence, reverse=True)
        return ranked

    @staticmethod
    def _recency_score(year: int) -> float:
        if not year:
            return 0.5
        age = max(0, date.today().year - year)
        return max(0.3, 1.0 - age * 0.08)

    @staticmethod
    def _level(confidence: float) -> str:
        if confidence >= 0.75:
            return "High"
        if confidence >= 0.5:
            return "Medium"
        return "Low"
