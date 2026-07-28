"""Diagnosis Agent service facade — Dependency Injection entrypoint."""

from __future__ import annotations

import time
from typing import Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.diagnosis.models import DiagnosisReport
from app.ai.diagnosis.pipeline import DiagnosisPipeline
from app.core.logging import get_logger
from app.repositories.diagnosis_repository import DiagnosisResultRepository
from app.repositories.intake_repositories import DocumentProcessingJobRepository
from app.schemas.diagnosis import (
    ClinicalDecisionSupportOut,
    DiagnosisHistoryItemOut,
    DiagnosisResultOut,
    DiagnosisStartRequest,
    DiagnosisStartResponse,
    DifferentialDiagnosisOut,
    DiseaseProbabilityOut,
    SeverityAssessmentOut,
    SymptomAnalysisOut,
    TreatmentPathOut,
)

logger = get_logger("hospital_ai.diagnosis.service")


class DiagnosisService:
    """Facade for the Diagnosis Agent — Dependency Injection entrypoint."""

    def __init__(
        self,
        pipeline: Optional[DiagnosisPipeline] = None,
        results: Optional[DiagnosisResultRepository] = None,
    ) -> None:
        self._pipeline = pipeline or DiagnosisPipeline()
        self._results = results or DiagnosisResultRepository()

    def start(self, request: DiagnosisStartRequest) -> DiagnosisStartResponse:
        started = time.perf_counter()
        try:
            report: DiagnosisReport = self._pipeline.run(
                request.patient_id,
                chief_complaint=request.chief_complaint,
                focus_symptoms=request.focus_symptoms,
            )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Diagnosis pipeline failed patient=%s", request.patient_id)
            raise HTTPException(status_code=500, detail=f"Diagnosis Agent failed: {exc}") from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)

        jobs = DocumentProcessingJobRepository()
        latest_job = jobs.latest_for_patient(request.patient_id)

        row = self._results.create(
            {
                "patient_id": str(request.patient_id),
                "processing_job_id": str(latest_job["id"]) if latest_job else None,
                "chief_complaint": report.chief_complaint,
                "focus_symptoms_json": report.focus_symptoms,
                "symptom_analysis_json": report.symptom_analysis.model_dump(mode="json"),
                "differential_diagnoses_json": [
                    d.model_dump(mode="json") for d in report.differential_diagnoses
                ],
                "probability_scores_json": [
                    p.model_dump(mode="json") for p in report.probability_scores
                ],
                "severity_assessment_json": report.severity_assessment.model_dump(mode="json"),
                "treatment_path_json": report.treatment_path.model_dump(mode="json"),
                "clinical_decision_support_json": report.clinical_decision_support.model_dump(
                    mode="json"
                ),
                "summary": report.summary,
                "engine": report.engine,
                "status": "Completed",
                "error_message": None,
                "processing_time_ms": elapsed_ms,
            }
        )

        return DiagnosisStartResponse(
            patient_id=request.patient_id,
            status="Completed",
            processing_time_ms=elapsed_ms,
            summary=report.summary,
            engine=report.engine,
            warnings=report.warnings,
            symptom_analysis=SymptomAnalysisOut.model_validate(
                report.symptom_analysis.model_dump(mode="json")
            ),
            differential_diagnoses=[
                DifferentialDiagnosisOut.model_validate(d.model_dump(mode="json"))
                for d in report.differential_diagnoses
            ],
            probability_scores=[
                DiseaseProbabilityOut.model_validate(p.model_dump(mode="json"))
                for p in report.probability_scores
            ],
            severity_assessment=SeverityAssessmentOut.model_validate(
                report.severity_assessment.model_dump(mode="json")
            ),
            treatment_path=TreatmentPathOut.model_validate(
                report.treatment_path.model_dump(mode="json")
            ),
            clinical_decision_support=ClinicalDecisionSupportOut.model_validate(
                report.clinical_decision_support.model_dump(mode="json")
            ),
            diagnosis_result=DiagnosisResultOut.model_validate(row),
        )

    def result(self, patient_id: UUID) -> DiagnosisResultOut:
        row = self._results.get_latest_for_patient(patient_id)
        if not row:
            raise HTTPException(
                status_code=404,
                detail="No diagnosis found for this patient. Run the Diagnosis Agent first.",
            )
        return DiagnosisResultOut.model_validate(row)

    def history(self, patient_id: UUID, limit: int = 20) -> list[DiagnosisHistoryItemOut]:
        rows = self._results.list_for_patient(patient_id, limit=limit)
        items: list[DiagnosisHistoryItemOut] = []
        for row in rows:
            severity = (row.get("severity_assessment_json") or {}).get("level")
            probs = row.get("probability_scores_json") or []
            top_condition = probs[0].get("condition") if probs else None
            items.append(
                DiagnosisHistoryItemOut(
                    id=row["id"],
                    created_at=row["created_at"],
                    summary=row.get("summary"),
                    severity_level=severity,
                    top_condition=top_condition,
                    status=row.get("status") or "Completed",
                )
            )
        return items


def get_diagnosis_service() -> DiagnosisService:
    return DiagnosisService()
