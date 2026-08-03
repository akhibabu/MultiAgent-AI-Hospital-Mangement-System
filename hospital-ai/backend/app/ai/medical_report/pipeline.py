"""
Medical Report Agent — sequential pipeline.

Patient Context + Knowledge Graph + Diagnosis Results + Research Results +
Prescription Results -> 1. Clinical Summary -> 2. Doctor Notes Generation ->
3. Discharge Summary -> 4. Referral Letter Creation -> 5. Insurance
Documentation -> 6. Patient Report Generation.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.medical_report.clinical_summary_generator import ClinicalSummaryGenerator
from app.ai.medical_report.discharge_summary_generator import DischargeSummaryGenerator
from app.ai.medical_report.doctor_notes_generator import DoctorNotesGenerator
from app.ai.medical_report.insurance_documentation_generator import (
    InsuranceDocumentationGenerator,
)
from app.ai.medical_report.models import MedicalReportBundle
from app.ai.medical_report.patient_report_generator import PatientReportGenerator
from app.ai.medical_report.referral_letter_generator import ReferralLetterGenerator
from app.core.logging import get_logger
from app.repositories.diagnosis_repository import DiagnosisResultRepository
from app.repositories.patient_context_repository import (
    PatientClinicalContextRepository,
)
from app.repositories.prescription_repository import PrescriptionResultRepository
from app.repositories.research_repository import ResearchResultRepository

logger = get_logger("hospital_ai.medical_report.pipeline")


class MedicalReportPipeline:
    """Orchestrates the six-stage Medical Report Agent pipeline."""

    def __init__(
        self,
        *,
        context_repo: Optional[PatientClinicalContextRepository] = None,
        diagnosis_repo: Optional[DiagnosisResultRepository] = None,
        research_repo: Optional[ResearchResultRepository] = None,
        prescription_repo: Optional[PrescriptionResultRepository] = None,
        clinical_summary_generator: Optional[ClinicalSummaryGenerator] = None,
        doctor_notes_generator: Optional[DoctorNotesGenerator] = None,
        discharge_summary_generator: Optional[DischargeSummaryGenerator] = None,
        referral_letter_generator: Optional[ReferralLetterGenerator] = None,
        insurance_documentation_generator: Optional[InsuranceDocumentationGenerator] = None,
        patient_report_generator: Optional[PatientReportGenerator] = None,
    ) -> None:
        self._context_repo = context_repo or PatientClinicalContextRepository()
        self._diagnosis_repo = diagnosis_repo or DiagnosisResultRepository()
        self._research_repo = research_repo or ResearchResultRepository()
        self._prescription_repo = prescription_repo or PrescriptionResultRepository()
        self._clinical_summary = clinical_summary_generator or ClinicalSummaryGenerator()
        self._doctor_notes = doctor_notes_generator or DoctorNotesGenerator()
        self._discharge_summary = discharge_summary_generator or DischargeSummaryGenerator()
        self._referral_letter = referral_letter_generator or ReferralLetterGenerator()
        self._insurance_documentation = (
            insurance_documentation_generator or InsuranceDocumentationGenerator()
        )
        self._patient_report = patient_report_generator or PatientReportGenerator()

    def run(
        self,
        patient_id: UUID,
        *,
        diagnosis_result_id: Optional[UUID] = None,
        research_result_id: Optional[UUID] = None,
        prescription_result_id: Optional[UUID] = None,
        receiving_specialist: Optional[str] = None,
        version: int = 1,
    ) -> MedicalReportBundle:
        context = self._context_repo.load(patient_id)
        if not context.patient_id:
            raise HTTPException(status_code=404, detail="Patient not found")

        diagnosis_row = self._load_by_id_or_latest(
            self._diagnosis_repo, patient_id, diagnosis_result_id
        )
        research_row = self._load_by_id_or_latest(
            self._research_repo, patient_id, research_result_id
        )
        prescription_row = self._load_by_id_or_latest(
            self._prescription_repo, patient_id, prescription_result_id
        )

        warnings = list(context.validation_warnings)
        if not diagnosis_row:
            warnings.append(
                "No Diagnosis Agent result found — clinical summary and notes will be "
                "limited to Patient Context only."
            )
        if not prescription_row:
            warnings.append(
                "No Prescription Agent result found — medication and treatment plan "
                "sections will be limited."
            )

        # 1. Clinical Summary
        clinical_summary = self._clinical_summary.generate(context, diagnosis_row)

        # 2. Doctor Notes Generation
        doctor_notes = self._doctor_notes.generate(context, diagnosis_row)

        # 3. Discharge Summary
        discharge_summary = self._discharge_summary.generate(context, diagnosis_row, prescription_row)

        # 4. Referral Letter Creation
        referral_letter = self._referral_letter.generate(
            context, diagnosis_row, receiving_specialist=receiving_specialist
        )

        # 5. Insurance Documentation
        insurance_documentation = self._insurance_documentation.generate(
            context, diagnosis_row, research_row
        )

        # 6. Patient Report Generation
        patient_report = self._patient_report.generate(context, diagnosis_row, prescription_row)

        summary = (
            f"Medical Report Agent generated {clinical_summary.diagnosis_summary and 'a full'} "
            "documentation bundle: Clinical Summary, Doctor Notes, Discharge Summary, "
            f"Referral Letter ({referral_letter.receiving_specialist}), Insurance Documentation, "
            "and a patient-friendly report."
        )

        logger.info(
            "Medical Report pipeline complete patient=%s version=%s",
            patient_id,
            version,
        )

        return MedicalReportBundle(
            patient_id=str(patient_id),
            diagnosis_result_id=str(diagnosis_row["id"]) if diagnosis_row else None,
            research_result_id=str(research_row["id"]) if research_row else None,
            prescription_result_id=str(prescription_row["id"]) if prescription_row else None,
            clinical_summary=clinical_summary,
            doctor_notes=doctor_notes,
            discharge_summary=discharge_summary,
            referral_letter=referral_letter,
            insurance_documentation=insurance_documentation,
            patient_report=patient_report,
            summary=summary,
            version=version,
            warnings=warnings,
        )

    @staticmethod
    def _load_by_id_or_latest(
        repo: Any,
        patient_id: UUID,
        result_id: Optional[UUID],
    ) -> Optional[Dict[str, Any]]:
        if result_id:
            row = repo.get_by_id(result_id) if hasattr(repo, "get_by_id") else None
            if not row:
                raise HTTPException(status_code=404, detail="Referenced result not found")
            return row
        return repo.get_latest_for_patient(patient_id)
