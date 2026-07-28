"""Research Agent domain models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

EVIDENCE_LEVELS = ("High", "Medium", "Low")

RESEARCH_DISCLAIMER = (
    "Evidence summary generated from configured research providers "
    "(mocked by default). Provides evidence only — never invents facts, "
    "never prescribes medication, never replaces clinical judgment."
)


class LiteratureItem(BaseModel):
    reference_id: str
    title: str
    authors: List[str] = Field(default_factory=list)
    journal: str = ""
    publication_year: int = 0
    study_type: str = "Review Article"
    summary: str = ""
    url: str = ""
    condition: str = ""
    relevance_score: float = 0.0


class ClinicalTrialItem(BaseModel):
    trial_id: str
    title: str
    status: str = "Unknown"
    phase: str = ""
    outcome_summary: str = ""
    eligibility_summary: str = ""
    condition: str = ""
    url: str = ""
    relevance_score: float = 0.0


class GuidelineItem(BaseModel):
    source: str  # WHO | CDC | Hospital | Medical Society
    title: str
    recommendation: str = ""
    condition: str = ""
    published_year: int = 0
    url: str = ""
    relevance_score: float = 0.0


class DrugEvidenceItem(BaseModel):
    drug_name: str
    condition: str = ""
    effectiveness_summary: str = ""
    known_side_effects: List[str] = Field(default_factory=list)
    contraindications: List[str] = Field(default_factory=list)
    drug_interactions: List[str] = Field(default_factory=list)
    supporting_evidence: str = ""
    relevance_score: float = 0.0


class RankedEvidence(BaseModel):
    """Uniform evidence record — persisted 1:1 into `clinical_evidence`."""

    evidence_type: str  # pubmed | clinical_trial | guideline | drug_efficacy
    condition: str
    title: str
    source: str
    reference_id: str = ""
    url: str = ""
    publication_date: Optional[str] = None
    summary: str = ""
    evidence_level: str = "Medium"
    relevance_score: float = 0.0
    confidence: float = 0.0
    raw: Dict[str, Any] = Field(default_factory=dict)


class ResearchRecommendation(BaseModel):
    """Clinician-facing evidence synthesis for one condition."""

    condition: str
    supporting_literature: List[str] = Field(default_factory=list)
    clinical_guidelines: List[str] = Field(default_factory=list)
    evidence_summary: str = ""
    recommended_diagnostic_tests: List[str] = Field(default_factory=list)
    research_highlights: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0


class ResearchReport(BaseModel):
    """Aggregate result of the full Research Agent pipeline."""

    patient_id: str
    diagnosis_result_id: Optional[str] = None
    conditions_researched: List[str] = Field(default_factory=list)
    pubmed_results: List[LiteratureItem] = Field(default_factory=list)
    clinical_trials: List[ClinicalTrialItem] = Field(default_factory=list)
    guidelines: List[GuidelineItem] = Field(default_factory=list)
    drug_efficacy: List[DrugEvidenceItem] = Field(default_factory=list)
    ranked_evidence: List[RankedEvidence] = Field(default_factory=list)
    evidence_level_counts: Dict[str, int] = Field(default_factory=dict)
    recommendations: List[ResearchRecommendation] = Field(default_factory=list)
    summary: str = ""
    provider: str = "mock"
    warnings: List[str] = Field(default_factory=list)
    disclaimer: str = RESEARCH_DISCLAIMER
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")
