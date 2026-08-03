"""Prescription Agent service facade — Dependency Injection entrypoint."""

from __future__ import annotations

import time
from typing import Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.prescription.models import PrescriptionReport
from app.ai.prescription.pipeline import PrescriptionPipeline
from app.core.logging import get_logger
from app.repositories.prescription_repository import (
    InteractionReportRepository,
    MedicationRecommendationRepository,
    PrescriptionResultRepository,
    ValidationReportRepository,
)
from app.schemas.prescription import (
    AllergyCheckItemOut,
    DosageRecommendationOut,
    DrugInteractionOut,
    MedicationRecommendationOut,
    PrescriptionHistoryItemOut,
    PrescriptionResultOut,
    PrescriptionStartRequest,
    PrescriptionStartResponse,
    PrescriptionStatusOut,
    PrescriptionValidationOut,
    TreatmentPlanOut,
)

logger = get_logger("hospital_ai.prescription.service")


class PrescriptionService:
    """Facade for the Prescription Agent — Dependency Injection entrypoint."""

    def __init__(
        self,
        pipeline: Optional[PrescriptionPipeline] = None,
        results: Optional[PrescriptionResultRepository] = None,
        medications: Optional[MedicationRecommendationRepository] = None,
        interactions: Optional[InteractionReportRepository] = None,
        validations: Optional[ValidationReportRepository] = None,
    ) -> None:
        self._pipeline = pipeline or PrescriptionPipeline()
        self._results = results or PrescriptionResultRepository()
        self._medications = medications or MedicationRecommendationRepository()
        self._interactions = interactions or InteractionReportRepository()
        self._validations = validations or ValidationReportRepository()

    def start(self, request: PrescriptionStartRequest) -> PrescriptionStartResponse:
        started = time.perf_counter()
        try:
            report: PrescriptionReport = self._pipeline.run(
                request.patient_id,
                diagnosis_result_id=request.diagnosis_result_id,
                research_result_id=request.research_result_id,
            )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Prescription pipeline failed patient=%s", request.patient_id)
            raise HTTPException(status_code=500, detail=f"Prescription Agent failed: {exc}") from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)

        row = self._results.create(
            {
                "patient_id": str(request.patient_id),
                "diagnosis_result_id": report.diagnosis_result_id,
                "research_result_id": report.research_result_id,
                "target_conditions_json": report.target_conditions,
                "medication_recommendations_json": [
                    m.model_dump(mode="json") for m in report.medication_recommendations
                ],
                "drug_interactions_json": [
                    i.model_dump(mode="json") for i in report.drug_interactions
                ],
                "allergy_checks_json": [
                    a.model_dump(mode="json") for a in report.allergy_checks
                ],
                "dosage_recommendations_json": [
                    d.model_dump(mode="json") for d in report.dosage_recommendations
                ],
                "treatment_plan_json": report.treatment_plan.model_dump(mode="json"),
                "validation_summary_json": report.validation.model_dump(mode="json"),
                "summary": report.summary,
                "engine": report.engine,
                "status": "Completed",
                "error_message": None,
                "processing_time_ms": elapsed_ms,
            }
        )
        prescription_result_id = row["id"]

        self._medications.create_many(
            [
                {
                    "prescription_result_id": str(prescription_result_id),
                    "condition": m.condition,
                    "medication_name": m.medication_name,
                    "drug_class": m.drug_class,
                    "purpose": m.purpose,
                    "evidence_source": m.evidence_source,
                    "clinical_guideline": m.clinical_guideline,
                    "confidence": m.confidence,
                    "alternative_drugs_json": m.alternative_drugs,
                    "expected_outcome": m.expected_outcome,
                }
                for m in report.medication_recommendations
            ]
        )

        self._interactions.create_many(
            [
                {
                    "prescription_result_id": str(prescription_result_id),
                    "drug_a": i.drug_a,
                    "drug_b": i.drug_b,
                    "interaction_level": i.interaction_level,
                    "explanation": i.explanation,
                    "recommendation": i.recommendation,
                }
                for i in report.drug_interactions
            ]
        )

        self._validations.create(
            {
                "prescription_result_id": str(prescription_result_id),
                "confidence_score": report.validation.confidence_score,
                "approval_status": report.validation.approval_status,
                "duplicate_drugs_json": report.validation.duplicate_drugs,
                "contraindications_json": report.validation.contraindications_found,
                "max_dose_exceeded_json": report.validation.max_dose_exceeded,
                "allergy_conflicts_json": report.validation.allergy_conflicts,
                "drug_warnings_json": report.validation.drug_warnings,
                "notes_json": report.validation.notes,
            }
        )

        return PrescriptionStartResponse(
            patient_id=request.patient_id,
            diagnosis_result_id=(
                UUID(report.diagnosis_result_id) if report.diagnosis_result_id else None
            ),
            research_result_id=(
                UUID(report.research_result_id) if report.research_result_id else None
            ),
            status="Completed",
            processing_time_ms=elapsed_ms,
            summary=report.summary,
            engine=report.engine,
            warnings=report.warnings,
            target_conditions=report.target_conditions,
            medication_recommendations=[
                MedicationRecommendationOut.model_validate(m.model_dump(mode="json"))
                for m in report.medication_recommendations
            ],
            drug_interactions=[
                DrugInteractionOut.model_validate(i.model_dump(mode="json"))
                for i in report.drug_interactions
            ],
            allergy_checks=[
                AllergyCheckItemOut.model_validate(a.model_dump(mode="json"))
                for a in report.allergy_checks
            ],
            dosage_recommendations=[
                DosageRecommendationOut.model_validate(d.model_dump(mode="json"))
                for d in report.dosage_recommendations
            ],
            treatment_plan=TreatmentPlanOut.model_validate(
                report.treatment_plan.model_dump(mode="json")
            ),
            validation=PrescriptionValidationOut.model_validate(
                report.validation.model_dump(mode="json")
            ),
            prescription_result=PrescriptionResultOut.model_validate(row),
        )

    def result(self, patient_id: UUID) -> PrescriptionResultOut:
        row = self._results.get_latest_for_patient(patient_id)
        if not row:
            raise HTTPException(
                status_code=404,
                detail="No prescription found for this patient. Run the Prescription Agent first.",
            )
        return PrescriptionResultOut.model_validate(row)

    def status(self, patient_id: UUID) -> PrescriptionStatusOut:
        row = self._results.get_latest_for_patient(patient_id)
        if not row:
            return PrescriptionStatusOut(patient_id=patient_id, has_result=False, status="Not Started")
        validation = row.get("validation_summary_json") or {}
        return PrescriptionStatusOut(
            patient_id=patient_id,
            has_result=True,
            status=row.get("status") or "Completed",
            approval_status=validation.get("approval_status"),
            confidence_score=validation.get("confidence_score"),
            target_conditions=row.get("target_conditions_json") or [],
            summary=row.get("summary"),
            processing_time_ms=row.get("processing_time_ms"),
            created_at=row.get("created_at"),
        )

    def history(self, patient_id: UUID, limit: int = 20) -> list[PrescriptionHistoryItemOut]:
        rows = self._results.list_for_patient(patient_id, limit=limit)
        items: list[PrescriptionHistoryItemOut] = []
        for row in rows:
            validation = row.get("validation_summary_json") or {}
            items.append(
                PrescriptionHistoryItemOut(
                    id=row["id"],
                    created_at=row["created_at"],
                    summary=row.get("summary"),
                    approval_status=validation.get("approval_status"),
                    target_conditions=row.get("target_conditions_json") or [],
                    status=row.get("status") or "Completed",
                )
            )
        return items


def get_prescription_service() -> PrescriptionService:
    return PrescriptionService()
