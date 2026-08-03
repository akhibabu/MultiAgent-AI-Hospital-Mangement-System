"""Medical Report Agent service facade — Dependency Injection entrypoint."""

from __future__ import annotations

import time
from typing import Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.medical_report.models import MedicalReportBundle
from app.ai.medical_report.pipeline import MedicalReportPipeline
from app.core.logging import get_logger
from app.repositories.medical_report_repository import (
    GeneratedMedicalReportRepository,
    InsuranceDocumentRepository,
    ReferralLetterRepository,
)
from app.schemas.medical_report import (
    ClinicalSummaryOut,
    DischargeSummaryOut,
    DoctorNotesOut,
    GeneratedMedicalReportOut,
    InsuranceDocumentationOut,
    MedicalReportHistoryItemOut,
    MedicalReportStartRequest,
    MedicalReportStartResponse,
    MedicalReportStatusOut,
    PatientReportOut,
    ReferralLetterOut,
)

logger = get_logger("hospital_ai.medical_report.service")


class MedicalReportService:
    """Facade for the Medical Report Agent — Dependency Injection entrypoint."""

    def __init__(
        self,
        pipeline: Optional[MedicalReportPipeline] = None,
        results: Optional[GeneratedMedicalReportRepository] = None,
        referral_letters: Optional[ReferralLetterRepository] = None,
        insurance_documents: Optional[InsuranceDocumentRepository] = None,
    ) -> None:
        self._pipeline = pipeline or MedicalReportPipeline()
        self._results = results or GeneratedMedicalReportRepository()
        self._referral_letters = referral_letters or ReferralLetterRepository()
        self._insurance_documents = insurance_documents or InsuranceDocumentRepository()

    def start(self, request: MedicalReportStartRequest) -> MedicalReportStartResponse:
        started = time.perf_counter()
        next_version = self._results.count_for_patient(request.patient_id) + 1
        try:
            bundle: MedicalReportBundle = self._pipeline.run(
                request.patient_id,
                diagnosis_result_id=request.diagnosis_result_id,
                research_result_id=request.research_result_id,
                prescription_result_id=request.prescription_result_id,
                receiving_specialist=request.receiving_specialist,
                version=next_version,
            )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Medical Report pipeline failed patient=%s", request.patient_id)
            raise HTTPException(status_code=500, detail=f"Medical Report Agent failed: {exc}") from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)

        row = self._results.create(
            {
                "patient_id": str(request.patient_id),
                "diagnosis_result_id": bundle.diagnosis_result_id,
                "research_result_id": bundle.research_result_id,
                "prescription_result_id": bundle.prescription_result_id,
                "clinical_summary_json": bundle.clinical_summary.model_dump(mode="json"),
                "doctor_notes_json": bundle.doctor_notes.model_dump(mode="json"),
                "discharge_summary_json": bundle.discharge_summary.model_dump(mode="json"),
                "referral_letter_json": bundle.referral_letter.model_dump(mode="json"),
                "insurance_documentation_json": bundle.insurance_documentation.model_dump(mode="json"),
                "patient_report_json": bundle.patient_report.model_dump(mode="json"),
                "summary": bundle.summary,
                "engine": bundle.engine,
                "version": bundle.version,
                "status": "Completed",
                "error_message": None,
                "processing_time_ms": elapsed_ms,
            }
        )
        generated_report_id = row["id"]

        referral_row = self._referral_letters.create(
            {
                "generated_report_id": str(generated_report_id),
                "patient_id": str(request.patient_id),
                "receiving_specialist": bundle.referral_letter.receiving_specialist,
                "reason": bundle.referral_letter.reason,
                "history_summary": bundle.referral_letter.history,
                "important_findings_json": bundle.referral_letter.important_findings,
                "investigations_json": bundle.referral_letter.investigations,
                "requested_evaluation": bundle.referral_letter.requested_evaluation,
                "letter_body": bundle.referral_letter.letter_body,
            }
        )

        insurance_row = self._insurance_documents.create(
            {
                "generated_report_id": str(generated_report_id),
                "patient_id": str(request.patient_id),
                "diagnosis_codes_json": bundle.insurance_documentation.diagnosis_codes,
                "procedure_codes_json": bundle.insurance_documentation.procedure_codes,
                "supporting_documents_json": bundle.insurance_documentation.supporting_documents,
                "medical_necessity": bundle.insurance_documentation.medical_necessity,
                "claim_summary": bundle.insurance_documentation.claim_summary,
                "supporting_evidence_json": bundle.insurance_documentation.supporting_evidence,
            }
        )

        return MedicalReportStartResponse(
            patient_id=request.patient_id,
            diagnosis_result_id=(
                UUID(bundle.diagnosis_result_id) if bundle.diagnosis_result_id else None
            ),
            research_result_id=(
                UUID(bundle.research_result_id) if bundle.research_result_id else None
            ),
            prescription_result_id=(
                UUID(bundle.prescription_result_id) if bundle.prescription_result_id else None
            ),
            status="Completed",
            processing_time_ms=elapsed_ms,
            summary=bundle.summary,
            engine=bundle.engine,
            version=bundle.version,
            warnings=bundle.warnings,
            clinical_summary=ClinicalSummaryOut.model_validate(
                bundle.clinical_summary.model_dump(mode="json")
            ),
            doctor_notes=DoctorNotesOut.model_validate(bundle.doctor_notes.model_dump(mode="json")),
            discharge_summary=DischargeSummaryOut.model_validate(
                bundle.discharge_summary.model_dump(mode="json")
            ),
            referral_letter=ReferralLetterOut.model_validate(
                {**bundle.referral_letter.model_dump(mode="json"), "id": referral_row.get("id")}
            ),
            insurance_documentation=InsuranceDocumentationOut.model_validate(
                {
                    **bundle.insurance_documentation.model_dump(mode="json"),
                    "id": insurance_row.get("id"),
                }
            ),
            patient_report=PatientReportOut.model_validate(
                bundle.patient_report.model_dump(mode="json")
            ),
            generated_report=GeneratedMedicalReportOut.model_validate(row),
        )

    def result(self, patient_id: UUID) -> GeneratedMedicalReportOut:
        row = self._results.get_latest_for_patient(patient_id)
        if not row:
            raise HTTPException(
                status_code=404,
                detail="No medical report found for this patient. Run the Medical Report Agent first.",
            )
        return GeneratedMedicalReportOut.model_validate(row)

    def status(self, patient_id: UUID) -> MedicalReportStatusOut:
        row = self._results.get_latest_for_patient(patient_id)
        if not row:
            return MedicalReportStatusOut(patient_id=patient_id, has_result=False, status="Not Started")
        return MedicalReportStatusOut(
            patient_id=patient_id,
            has_result=True,
            status=row.get("status") or "Completed",
            version=row.get("version"),
            summary=row.get("summary"),
            processing_time_ms=row.get("processing_time_ms"),
            created_at=row.get("created_at"),
        )

    def history(self, patient_id: UUID, limit: int = 20) -> list[MedicalReportHistoryItemOut]:
        rows = self._results.list_for_patient(patient_id, limit=limit)
        return [
            MedicalReportHistoryItemOut(
                id=row["id"],
                created_at=row["created_at"],
                version=row.get("version") or 1,
                summary=row.get("summary"),
                status=row.get("status") or "Completed",
            )
            for row in rows
        ]


def get_medical_report_service() -> MedicalReportService:
    return MedicalReportService()
