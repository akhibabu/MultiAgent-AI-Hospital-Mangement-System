"""Factory resolving the active Research Agent provider bundle."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.research.providers.base import (
    ClinicalTrialProvider,
    DrugEvidenceProvider,
    MedicalKnowledgeProvider,
    PubMedProvider,
    TreatmentGuidelineProvider,
)
from app.ai.research.providers.mock_providers import (
    MockClinicalTrialProvider,
    MockDrugEvidenceProvider,
    MockMedicalKnowledgeProvider,
    MockPubMedProvider,
    MockTreatmentGuidelineProvider,
)


@dataclass
class ResearchProviderBundle:
    pubmed: PubMedProvider
    clinical_trials: ClinicalTrialProvider
    guidelines: TreatmentGuidelineProvider
    drug_evidence: DrugEvidenceProvider
    medical_knowledge: MedicalKnowledgeProvider
    provider_name: str = "mock"


class ResearchProviderFactory:
    """
    Resolves the provider bundle from `settings.research_provider`.

    Today only `mock` is implemented (deterministic, clearly-labeled
    synthetic evidence). Future values (e.g. `live`) can wire real
    PubMed / ClinicalTrials.gov / guideline-body APIs here without
    changing pipeline or route code.
    """

    @staticmethod
    def create_bundle(provider: str = "mock") -> ResearchProviderBundle:
        name = (provider or "mock").strip().lower()
        if name in {"mock", "stub", "default"}:
            return ResearchProviderBundle(
                pubmed=MockPubMedProvider(),
                clinical_trials=MockClinicalTrialProvider(),
                guidelines=MockTreatmentGuidelineProvider(),
                drug_evidence=MockDrugEvidenceProvider(),
                medical_knowledge=MockMedicalKnowledgeProvider(),
                provider_name=name,
            )
        raise ValueError(f"Unknown RESEARCH_PROVIDER '{name}'")


def get_research_provider_bundle() -> ResearchProviderBundle:
    from app.config import get_settings

    settings = get_settings()
    return ResearchProviderFactory.create_bundle(
        getattr(settings, "research_provider", "mock")
    )
