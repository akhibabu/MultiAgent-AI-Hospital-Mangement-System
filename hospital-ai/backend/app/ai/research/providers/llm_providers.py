"""
AI Orchestrator-backed Research Agent providers.

Each provider still implements the same narrow ABC from `base.py` — only
the concrete implementation changed, from deterministic mock data to an
LLM call routed through the AI Orchestrator (`research` agent). This
keeps `pipeline.py`, `research_repository.py`, the API schemas, and the
frontend completely unchanged.

Every provider clearly labels its output as an AI-generated evidence
summary (see the `research/*.md` prompts) — never a verified citation —
consistent with the Research Agent's "evidence only, never fact" rule.
"""
from __future__ import annotations

from typing import List
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.ai.research.models import (
    ClinicalTrialItem,
    DrugEvidenceItem,
    GuidelineItem,
    LiteratureItem,
)
from app.ai.research.providers.base import (
    ClinicalTrialProvider,
    DrugEvidenceProvider,
    PubMedProvider,
    TreatmentGuidelineProvider,
)


class _LiteratureList(BaseModel):
    items: List[LiteratureItem] = Field(default_factory=list)


class _ClinicalTrialList(BaseModel):
    items: List[ClinicalTrialItem] = Field(default_factory=list)


class _GuidelineList(BaseModel):
    items: List[GuidelineItem] = Field(default_factory=list)


class LLMPubMedProvider(OrchestratorCallMixin, PubMedProvider):
    name = "llm_pubmed"

    def __init__(self, patient_id: UUID | None = None) -> None:
        self._patient_id = patient_id

    def search(self, condition: str, *, limit: int = 5) -> List[LiteratureItem]:
        data = self._call(
            agent="research",
            task="pubmed_search",
            patient_id=self._patient_id,
            response_model=_LiteratureList,
            extra_vars={"condition": condition, "limit": limit},
        )
        return _LiteratureList.model_validate(data).items[:limit]


class LLMClinicalTrialProvider(OrchestratorCallMixin, ClinicalTrialProvider):
    name = "llm_clinical_trials"

    def __init__(self, patient_id: UUID | None = None) -> None:
        self._patient_id = patient_id

    def search(self, condition: str, *, limit: int = 5) -> List[ClinicalTrialItem]:
        data = self._call(
            agent="research",
            task="clinical_trials",
            patient_id=self._patient_id,
            response_model=_ClinicalTrialList,
            extra_vars={"condition": condition, "limit": limit},
        )
        return _ClinicalTrialList.model_validate(data).items[:limit]


class LLMTreatmentGuidelineProvider(OrchestratorCallMixin, TreatmentGuidelineProvider):
    name = "llm_guidelines"

    def __init__(self, patient_id: UUID | None = None) -> None:
        self._patient_id = patient_id

    def get_guidelines(self, condition: str, *, limit: int = 5) -> List[GuidelineItem]:
        data = self._call(
            agent="research",
            task="treatment_guidelines",
            patient_id=self._patient_id,
            response_model=_GuidelineList,
            extra_vars={"condition": condition, "limit": limit},
        )
        return _GuidelineList.model_validate(data).items[:limit]


class LLMDrugEvidenceProvider(OrchestratorCallMixin, DrugEvidenceProvider):
    name = "llm_drug_evidence"

    def __init__(self, patient_id: UUID | None = None) -> None:
        self._patient_id = patient_id

    def analyze(self, drug_name: str, condition: str) -> DrugEvidenceItem:
        data = self._call(
            agent="research",
            task="drug_analysis",
            patient_id=self._patient_id,
            response_model=DrugEvidenceItem,
            extra_vars={"drug_name": drug_name, "condition": condition},
        )
        return DrugEvidenceItem.model_validate(data)
