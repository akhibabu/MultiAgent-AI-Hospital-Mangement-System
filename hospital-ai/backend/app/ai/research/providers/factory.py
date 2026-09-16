"""Factory resolving the active Research Agent provider bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from app.ai.research.providers.base import (
    ClinicalTrialProvider,
    DrugEvidenceProvider,
    MedicalKnowledgeProvider,
    PubMedProvider,
    TreatmentGuidelineProvider,
)
from app.ai.research.providers.llm_providers import (
    LLMClinicalTrialProvider,
    LLMDrugEvidenceProvider,
    LLMPubMedProvider,
    LLMTreatmentGuidelineProvider,
)
from app.ai.research.providers.mock_providers import MockMedicalKnowledgeProvider


@dataclass
class ResearchProviderBundle:
    pubmed: PubMedProvider
    clinical_trials: ClinicalTrialProvider
    guidelines: TreatmentGuidelineProvider
    drug_evidence: DrugEvidenceProvider
    medical_knowledge: MedicalKnowledgeProvider
    provider_name: str = "ai_orchestrator"


class ResearchProviderFactory:
    """
    Builds the Research Agent provider bundle. Every evidence-gathering
    provider (PubMed/ClinicalTrials/Guidelines/DrugEvidence) is now backed
    by the AI Orchestrator (`research` agent) — see
    `app/ai/research/providers/llm_providers.py`.

    `MedicalKnowledgeProvider.typical_drugs_for()` stays rule-based: it
    only picks candidate drug names to analyze from the knowledge base,
    it never makes a clinical claim.

    A bundle is created per-run (bound to a `patient_id`) so every
    provider call is attributed to the right patient in conversation
    memory and usage logs.
    """

    @staticmethod
    def create_bundle(patient_id: Optional[UUID] = None) -> ResearchProviderBundle:
        return ResearchProviderBundle(
            pubmed=LLMPubMedProvider(patient_id),
            clinical_trials=LLMClinicalTrialProvider(patient_id),
            guidelines=LLMTreatmentGuidelineProvider(patient_id),
            drug_evidence=LLMDrugEvidenceProvider(patient_id),
            medical_knowledge=MockMedicalKnowledgeProvider(),
            provider_name="ai_orchestrator",
        )


def get_research_provider_bundle(patient_id: Optional[UUID] = None) -> ResearchProviderBundle:
    return ResearchProviderFactory.create_bundle(patient_id)
