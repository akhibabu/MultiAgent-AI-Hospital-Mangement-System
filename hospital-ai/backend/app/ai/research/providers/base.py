"""
Research Agent provider interfaces.

Each provider is a narrow abstract interface so a mocked implementation
today can be swapped for a live external API later (real PubMed E-utilities,
ClinicalTrials.gov API, etc.) without touching pipeline/business logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from app.ai.research.models import (
    ClinicalTrialItem,
    DrugEvidenceItem,
    GuidelineItem,
    LiteratureItem,
)


class PubMedProvider(ABC):
    """Searches medical literature (papers, reviews, case reports)."""

    name: str = "pubmed"

    @abstractmethod
    def search(self, condition: str, *, limit: int = 5) -> List[LiteratureItem]: ...


class ClinicalTrialProvider(ABC):
    """Retrieves relevant clinical trials, status, outcomes, and eligibility."""

    name: str = "clinical_trials"

    @abstractmethod
    def search(self, condition: str, *, limit: int = 5) -> List[ClinicalTrialItem]: ...


class TreatmentGuidelineProvider(ABC):
    """Retrieves WHO/CDC/hospital/medical-society treatment guidelines."""

    name: str = "guidelines"

    @abstractmethod
    def get_guidelines(self, condition: str, *, limit: int = 5) -> List[GuidelineItem]: ...


class DrugEvidenceProvider(ABC):
    """Analyzes published drug effectiveness, side effects, and interactions."""

    name: str = "drug_evidence"

    @abstractmethod
    def analyze(self, drug_name: str, condition: str) -> DrugEvidenceItem: ...


class MedicalKnowledgeProvider(ABC):
    """General medical-knowledge lookups (e.g. typical drug classes per condition)."""

    name: str = "medical_knowledge"

    @abstractmethod
    def typical_drugs_for(self, condition: str) -> List[str]: ...
