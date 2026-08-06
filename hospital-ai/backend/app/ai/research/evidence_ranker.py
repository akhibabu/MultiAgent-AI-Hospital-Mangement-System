"""Research Agent — Step 5: Evidence Ranking."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.ai.research.models import (
    ClinicalTrialItem,
    DrugEvidenceItem,
    GuidelineItem,
    LiteratureItem,
    RankedEvidence,
)

#: Hard ceiling on how many evidence records go into the ranking prompt.
#: Full dumps of every literature/trial/guideline/drug object easily blow
#: Groq's free-tier request budget (prompt + completion), leaving the model
#: with ~1k completion tokens that cut the JSON mid-string.
_MAX_RANK_INPUT = 18
_SUMMARY_CHARS = 220


class _RankedEvidenceList(BaseModel):
    items: List[RankedEvidence] = Field(default_factory=list)


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


def _clip(text: str, limit: int = _SUMMARY_CHARS) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _compact_literature(item: LiteratureItem) -> Dict[str, Any]:
    return {
        "evidence_type": "pubmed",
        "condition": item.condition,
        "title": item.title,
        "source": item.journal or "PubMed",
        "reference_id": item.reference_id,
        "url": item.url or "",
        "summary": _clip(item.summary),
        "relevance_score": item.relevance_score,
    }


def _compact_trial(item: ClinicalTrialItem) -> Dict[str, Any]:
    return {
        "evidence_type": "clinical_trial",
        "condition": item.condition,
        "title": item.title,
        "source": item.phase or item.status or "ClinicalTrials.gov",
        "reference_id": item.trial_id,
        "url": item.url or "",
        "summary": _clip(item.outcome_summary or item.eligibility_summary),
        "relevance_score": item.relevance_score,
    }


def _compact_guideline(item: GuidelineItem) -> Dict[str, Any]:
    return {
        "evidence_type": "guideline",
        "condition": item.condition,
        "title": item.title,
        "source": item.source,
        "reference_id": f"{item.source}:{item.title}"[:80],
        "url": item.url or "",
        "summary": _clip(item.recommendation),
        "relevance_score": item.relevance_score,
    }


def _compact_drug(item: DrugEvidenceItem) -> Dict[str, Any]:
    return {
        "evidence_type": "drug_efficacy",
        "condition": item.condition,
        "title": item.drug_name,
        "source": "drug_analysis",
        "reference_id": item.drug_name,
        "url": "",
        "summary": _clip(item.effectiveness_summary or item.supporting_evidence),
        "relevance_score": item.relevance_score,
    }


def _select_rank_inputs(
    literature: List[LiteratureItem],
    trials: List[ClinicalTrialItem],
    guidelines: List[GuidelineItem],
    drug_evidence: List[DrugEvidenceItem],
) -> List[Dict[str, Any]]:
    """Interleave sources and take the strongest `_MAX_RANK_INPUT` records.

    Dumping every full model into the prompt is what pushed evidence_ranking
    to ~4800 prompt tokens and left ~1100 for the JSON reply — guaranteed
    truncation. Compact slim records keep the clinical signal and leave
    room for a complete response.
    """
    pools = [
        sorted(literature, key=lambda i: i.relevance_score, reverse=True),
        sorted(trials, key=lambda i: i.relevance_score, reverse=True),
        sorted(guidelines, key=lambda i: i.relevance_score, reverse=True),
        sorted(drug_evidence, key=lambda i: i.relevance_score, reverse=True),
    ]
    compactors = (
        _compact_literature,
        _compact_trial,
        _compact_guideline,
        _compact_drug,
    )
    selected: List[Dict[str, Any]] = []
    index = 0
    while len(selected) < _MAX_RANK_INPUT and any(pools):
        pool = pools[index % len(pools)]
        if pool:
            item = pool.pop(0)
            selected.append(compactors[index % len(compactors)](item))  # type: ignore[arg-type]
        index += 1
    return selected


class LLMEvidenceRanker(OrchestratorCallMixin, EvidenceRankingStrategy):
    """
    Ranks evidence by recency, source quality, and clinical relevance
    into High / Medium / Low evidence levels via the AI Orchestrator
    (`research` agent, `evidence_ranking` task).
    """

    def __init__(self, patient_id: Optional[UUID] = None) -> None:
        self._patient_id = patient_id

    def rank(
        self,
        *,
        literature: List[LiteratureItem],
        trials: List[ClinicalTrialItem],
        guidelines: List[GuidelineItem],
        drug_evidence: List[DrugEvidenceItem],
    ) -> List[RankedEvidence]:
        if not (literature or trials or guidelines or drug_evidence):
            return []
        candidates = _select_rank_inputs(
            literature, trials, guidelines, drug_evidence
        )
        data = self._call(
            agent="research",
            task="evidence_ranking",
            patient_id=self._patient_id,
            response_model=_RankedEvidenceList,
            extra_vars={
                # One compact list instead of four full dumps — the prompt
                # template reads `{{evidence_candidates}}`.
                "evidence_candidates": candidates,
                "candidate_count": len(candidates),
            },
        )
        ranked = _RankedEvidenceList.model_validate(data).items
        ranked.sort(key=lambda e: e.confidence, reverse=True)
        return ranked
