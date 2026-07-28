"""Research Agent — validates and enriches Diagnosis Agent output with evidence.

Never invents medical information. All providers are pluggable — mocked
today, swappable for live APIs later without changing business logic.
"""

from app.ai.research.models import (
    ClinicalTrialItem,
    DrugEvidenceItem,
    GuidelineItem,
    LiteratureItem,
    RankedEvidence,
    ResearchRecommendation,
    ResearchReport,
)
from app.ai.research.pipeline import ResearchPipeline

__all__ = [
    "ClinicalTrialItem",
    "DrugEvidenceItem",
    "GuidelineItem",
    "LiteratureItem",
    "RankedEvidence",
    "ResearchPipeline",
    "ResearchRecommendation",
    "ResearchReport",
]
