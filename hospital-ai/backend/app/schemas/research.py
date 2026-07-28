"""Pydantic schemas for the Research Agent."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ResearchStartRequest(BaseModel):
    patient_id: UUID
    diagnosis_result_id: Optional[UUID] = None


class LiteratureItemOut(BaseModel):
    reference_id: str
    title: str
    authors: List[str] = Field(default_factory=list)
    journal: str = ""
    publication_year: int = 0
    study_type: str = ""
    summary: str = ""
    url: str = ""
    condition: str = ""
    relevance_score: float = 0.0


class ClinicalTrialItemOut(BaseModel):
    trial_id: str
    title: str
    status: str = ""
    phase: str = ""
    outcome_summary: str = ""
    eligibility_summary: str = ""
    condition: str = ""
    url: str = ""
    relevance_score: float = 0.0


class GuidelineItemOut(BaseModel):
    source: str
    title: str
    recommendation: str = ""
    condition: str = ""
    published_year: int = 0
    url: str = ""
    relevance_score: float = 0.0


class DrugEvidenceItemOut(BaseModel):
    drug_name: str
    condition: str = ""
    effectiveness_summary: str = ""
    known_side_effects: List[str] = Field(default_factory=list)
    contraindications: List[str] = Field(default_factory=list)
    drug_interactions: List[str] = Field(default_factory=list)
    supporting_evidence: str = ""
    relevance_score: float = 0.0


class ClinicalEvidenceOut(BaseModel):
    id: Optional[UUID] = None
    evidence_type: str
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


class ResearchRecommendationOut(BaseModel):
    condition: str
    supporting_literature: List[str] = Field(default_factory=list)
    clinical_guidelines: List[str] = Field(default_factory=list)
    evidence_summary: str = ""
    recommended_diagnostic_tests: List[str] = Field(default_factory=list)
    research_highlights: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0


class ResearchResultOut(BaseModel):
    id: UUID
    patient_id: UUID
    diagnosis_result_id: Optional[UUID] = None
    conditions_researched_json: List[Any] = Field(default_factory=list)
    pubmed_json: List[Any] = Field(default_factory=list)
    clinical_trials_json: List[Any] = Field(default_factory=list)
    guidelines_json: List[Any] = Field(default_factory=list)
    drug_efficacy_json: List[Any] = Field(default_factory=list)
    evidence_ranking_summary_json: Dict[str, Any] = Field(default_factory=dict)
    recommendation_json: List[Any] = Field(default_factory=list)
    summary: Optional[str] = None
    provider: str = "mock"
    status: str = "Completed"
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ResearchStartResponse(BaseModel):
    patient_id: UUID
    diagnosis_result_id: Optional[UUID] = None
    status: str = "Completed"
    processing_time_ms: int
    summary: str
    provider: str
    warnings: List[str] = Field(default_factory=list)
    conditions_researched: List[str] = Field(default_factory=list)
    pubmed_results: List[LiteratureItemOut] = Field(default_factory=list)
    clinical_trials: List[ClinicalTrialItemOut] = Field(default_factory=list)
    guidelines: List[GuidelineItemOut] = Field(default_factory=list)
    drug_efficacy: List[DrugEvidenceItemOut] = Field(default_factory=list)
    evidence: List[ClinicalEvidenceOut] = Field(default_factory=list)
    evidence_level_counts: Dict[str, int] = Field(default_factory=dict)
    recommendations: List[ResearchRecommendationOut] = Field(default_factory=list)
    research_result: ResearchResultOut


class ResearchHistoryItemOut(BaseModel):
    id: UUID
    created_at: datetime
    summary: Optional[str] = None
    conditions_researched: List[str] = Field(default_factory=list)
    status: str = "Completed"
