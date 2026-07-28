"""Research Agent service facade — Dependency Injection entrypoint."""

from __future__ import annotations

import time
from typing import Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.research.models import ResearchReport
from app.ai.research.pipeline import ResearchPipeline
from app.core.logging import get_logger
from app.repositories.research_repository import (
    ClinicalEvidenceRepository,
    ResearchResultRepository,
)
from app.schemas.research import (
    ClinicalEvidenceOut,
    ClinicalTrialItemOut,
    DrugEvidenceItemOut,
    GuidelineItemOut,
    LiteratureItemOut,
    ResearchHistoryItemOut,
    ResearchRecommendationOut,
    ResearchResultOut,
    ResearchStartRequest,
    ResearchStartResponse,
)

logger = get_logger("hospital_ai.research.service")


class ResearchService:
    """Facade for the Research Agent — Dependency Injection entrypoint."""

    def __init__(
        self,
        pipeline: Optional[ResearchPipeline] = None,
        results: Optional[ResearchResultRepository] = None,
        evidence: Optional[ClinicalEvidenceRepository] = None,
    ) -> None:
        self._pipeline = pipeline or ResearchPipeline()
        self._results = results or ResearchResultRepository()
        self._evidence = evidence or ClinicalEvidenceRepository()

    def start(self, request: ResearchStartRequest) -> ResearchStartResponse:
        started = time.perf_counter()
        try:
            report: ResearchReport = self._pipeline.run(
                request.patient_id,
                diagnosis_result_id=request.diagnosis_result_id,
            )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Research pipeline failed patient=%s", request.patient_id)
            raise HTTPException(status_code=500, detail=f"Research Agent failed: {exc}") from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)

        row = self._results.create(
            {
                "patient_id": str(request.patient_id),
                "diagnosis_result_id": report.diagnosis_result_id,
                "conditions_researched_json": report.conditions_researched,
                "pubmed_json": [i.model_dump(mode="json") for i in report.pubmed_results],
                "clinical_trials_json": [i.model_dump(mode="json") for i in report.clinical_trials],
                "guidelines_json": [i.model_dump(mode="json") for i in report.guidelines],
                "drug_efficacy_json": [i.model_dump(mode="json") for i in report.drug_efficacy],
                "evidence_ranking_summary_json": report.evidence_level_counts,
                "recommendation_json": [r.model_dump(mode="json") for r in report.recommendations],
                "summary": report.summary,
                "provider": report.provider,
                "status": "Completed",
                "error_message": None,
                "processing_time_ms": elapsed_ms,
            }
        )

        evidence_rows = [
            {
                "research_result_id": str(row["id"]),
                "evidence_type": e.evidence_type,
                "condition": e.condition,
                "title": e.title,
                "source": e.source,
                "reference_id": e.reference_id,
                "url": e.url,
                "publication_date": e.publication_date,
                "summary": e.summary,
                "evidence_level": e.evidence_level,
                "relevance_score": e.relevance_score,
                "confidence": e.confidence,
                "raw_json": e.raw,
            }
            for e in report.ranked_evidence
        ]
        created_evidence = self._evidence.create_many(evidence_rows)

        return ResearchStartResponse(
            patient_id=request.patient_id,
            diagnosis_result_id=(
                UUID(report.diagnosis_result_id) if report.diagnosis_result_id else None
            ),
            status="Completed",
            processing_time_ms=elapsed_ms,
            summary=report.summary,
            provider=report.provider,
            warnings=report.warnings,
            conditions_researched=report.conditions_researched,
            pubmed_results=[
                LiteratureItemOut.model_validate(i.model_dump(mode="json"))
                for i in report.pubmed_results
            ],
            clinical_trials=[
                ClinicalTrialItemOut.model_validate(i.model_dump(mode="json"))
                for i in report.clinical_trials
            ],
            guidelines=[
                GuidelineItemOut.model_validate(i.model_dump(mode="json"))
                for i in report.guidelines
            ],
            drug_efficacy=[
                DrugEvidenceItemOut.model_validate(i.model_dump(mode="json"))
                for i in report.drug_efficacy
            ],
            evidence=[
                ClinicalEvidenceOut.model_validate(row)
                for row in (created_evidence or evidence_rows)
            ],
            evidence_level_counts=report.evidence_level_counts,
            recommendations=[
                ResearchRecommendationOut.model_validate(r.model_dump(mode="json"))
                for r in report.recommendations
            ],
            research_result=ResearchResultOut.model_validate(row),
        )

    def result(self, patient_id: UUID) -> ResearchResultOut:
        row = self._results.get_latest_for_patient(patient_id)
        if not row:
            raise HTTPException(
                status_code=404,
                detail="No research found for this patient. Run the Research Agent first.",
            )
        return ResearchResultOut.model_validate(row)

    def history(self, patient_id: UUID, limit: int = 20) -> list[ResearchHistoryItemOut]:
        rows = self._results.list_for_patient(patient_id, limit=limit)
        return [
            ResearchHistoryItemOut(
                id=row["id"],
                created_at=row["created_at"],
                summary=row.get("summary"),
                conditions_researched=row.get("conditions_researched_json") or [],
                status=row.get("status") or "Completed",
            )
            for row in rows
        ]


def get_research_service() -> ResearchService:
    return ResearchService()
