"""
Deterministic mock provider implementations.

Every mock provider generates stable, clearly-synthetic evidence keyed by
condition/drug name — it never claims to be real literature. This keeps the
Research Agent architecture ready for a real PubMed/ClinicalTrials.gov/
guideline-body integration without any business-logic changes.
"""

from __future__ import annotations

import hashlib
from datetime import date
from typing import List

from app.ai.diagnosis.knowledge_base import ConditionKnowledgeBase
from app.ai.research.models import (
    ClinicalTrialItem,
    DrugEvidenceItem,
    GuidelineItem,
    LiteratureItem,
)
from app.ai.research.providers.base import (
    ClinicalTrialProvider,
    DrugEvidenceProvider,
    MedicalKnowledgeProvider,
    PubMedProvider,
    TreatmentGuidelineProvider,
)

_JOURNALS = [
    "New England Journal of Medicine",
    "The Lancet",
    "JAMA",
    "Annals of Internal Medicine",
    "BMJ",
]
_STUDY_TYPES = ["Randomized Controlled Trial", "Systematic Review", "Case Report", "Cohort Study"]
_GUIDELINE_SOURCES = ["WHO", "CDC", "Hospital Clinical Guidelines", "Medical Society"]
_TRIAL_STATUSES = ["Recruiting", "Active, not recruiting", "Completed", "Terminated"]
_TRIAL_PHASES = ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]


def _seed(*parts: str) -> int:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


class MockPubMedProvider(PubMedProvider):
    name = "mock_pubmed"

    def search(self, condition: str, *, limit: int = 5) -> List[LiteratureItem]:
        items: List[LiteratureItem] = []
        for i in range(limit):
            seed = _seed(condition, "pubmed", str(i))
            year = 2019 + (seed % 7)
            journal = _JOURNALS[seed % len(_JOURNALS)]
            study_type = _STUDY_TYPES[seed % len(_STUDY_TYPES)]
            relevance = round(0.55 + (seed % 45) / 100, 2)
            items.append(
                LiteratureItem(
                    reference_id=f"MOCK-PMID-{seed % 100000:05d}",
                    title=f"{study_type} of clinical outcomes in {condition} management",
                    authors=[f"Author {chr(65 + (seed + j) % 6)}." for j in range(3)],
                    journal=journal,
                    publication_year=year,
                    study_type=study_type,
                    summary=(
                        f"Mock literature summary: this {study_type.lower()} examines "
                        f"patient outcomes associated with {condition}, reporting "
                        f"findings relevant to diagnostic evaluation and monitoring. "
                        f"(Simulated data — replace with a live PubMed provider.)"
                    ),
                    url=f"https://pubmed.ncbi.nlm.nih.gov/mock-{seed % 100000}",
                    condition=condition,
                    relevance_score=relevance,
                )
            )
        return items


class MockClinicalTrialProvider(ClinicalTrialProvider):
    name = "mock_clinical_trials"

    def search(self, condition: str, *, limit: int = 5) -> List[ClinicalTrialItem]:
        items: List[ClinicalTrialItem] = []
        for i in range(limit):
            seed = _seed(condition, "trial", str(i))
            status = _TRIAL_STATUSES[seed % len(_TRIAL_STATUSES)]
            phase = _TRIAL_PHASES[seed % len(_TRIAL_PHASES)]
            relevance = round(0.5 + (seed % 50) / 100, 2)
            items.append(
                ClinicalTrialItem(
                    trial_id=f"MOCK-NCT{seed % 10000000:08d}",
                    title=f"{phase} study evaluating management strategies for {condition}",
                    status=status,
                    phase=phase,
                    outcome_summary=(
                        f"Mock trial outcome: preliminary results suggest measurable "
                        f"improvement in monitored endpoints for {condition}. "
                        "(Simulated — replace with ClinicalTrials.gov API.)"
                    ),
                    eligibility_summary=(
                        f"Adults with confirmed or suspected {condition}; "
                        "exclusion criteria include pregnancy and severe comorbidity."
                    ),
                    condition=condition,
                    url=f"https://clinicaltrials.gov/mock/{seed % 10000000}",
                    relevance_score=relevance,
                )
            )
        return items


class MockTreatmentGuidelineProvider(TreatmentGuidelineProvider):
    name = "mock_guidelines"

    def get_guidelines(self, condition: str, *, limit: int = 5) -> List[GuidelineItem]:
        items: List[GuidelineItem] = []
        for i in range(min(limit, len(_GUIDELINE_SOURCES))):
            source = _GUIDELINE_SOURCES[i]
            seed = _seed(condition, "guideline", source)
            year = 2018 + (seed % 8)
            relevance = round(0.6 + (seed % 40) / 100, 2)
            items.append(
                GuidelineItem(
                    source=source,
                    title=f"{source} clinical practice recommendation for {condition}",
                    recommendation=(
                        f"Mock guideline: {source} recommends structured evaluation, "
                        f"risk stratification, and specialist referral where indicated "
                        f"for {condition}. (Simulated — replace with a live guideline provider.)"
                    ),
                    condition=condition,
                    published_year=year,
                    url=f"https://guidelines.mock/{source.lower().replace(' ', '-')}",
                    relevance_score=relevance,
                )
            )
        return items


class MockDrugEvidenceProvider(DrugEvidenceProvider):
    name = "mock_drug_evidence"

    def analyze(self, drug_name: str, condition: str) -> DrugEvidenceItem:
        seed = _seed(drug_name, condition, "drug")
        relevance = round(0.5 + (seed % 50) / 100, 2)
        return DrugEvidenceItem(
            drug_name=drug_name,
            condition=condition,
            effectiveness_summary=(
                f"Mock evidence review: published data associates {drug_name} with "
                f"symptomatic and/or biomarker improvement in {condition} in a "
                "subset of studied populations. (Simulated — analysis only, not a "
                "prescription.)"
            ),
            known_side_effects=self._pick(seed, [
                "Nausea", "Headache", "Dizziness", "Fatigue", "GI upset", "Rash",
            ]),
            contraindications=self._pick(seed + 1, [
                "Severe renal impairment", "Pregnancy", "Known hypersensitivity",
                "Severe hepatic impairment",
            ], max_items=2),
            drug_interactions=self._pick(seed + 2, [
                "NSAIDs", "Anticoagulants", "Other antihypertensives", "CYP3A4 inhibitors",
            ], max_items=2),
            supporting_evidence=(
                f"Aggregated from {1 + seed % 4} mock literature source(s) and "
                f"{1 + seed % 3} mock guideline source(s)."
            ),
            relevance_score=relevance,
        )

    @staticmethod
    def _pick(seed: int, pool: List[str], max_items: int = 3) -> List[str]:
        count = 1 + (seed % max_items)
        return [pool[(seed + i) % len(pool)] for i in range(count)]


class MockMedicalKnowledgeProvider(MedicalKnowledgeProvider):
    name = "mock_medical_knowledge"

    def __init__(self, knowledge_base: ConditionKnowledgeBase | None = None) -> None:
        self._kb = knowledge_base or ConditionKnowledgeBase()

    def typical_drugs_for(self, condition: str) -> List[str]:
        return self._kb.typical_drugs_for(condition)


def today_iso() -> str:
    return date.today().isoformat()
