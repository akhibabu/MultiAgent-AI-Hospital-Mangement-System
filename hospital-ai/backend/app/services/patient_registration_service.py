"""
Patient Registration — Intake Agent stage 1.

Validates patient / appointment / doctor / upload, creates a processing job,
and initializes Patient AI Context. Does NOT run OCR or any later stage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol
from uuid import UUID

from fastapi import HTTPException, UploadFile

from app.core.logging import get_logger
from app.repositories.intake_repositories import (
    AppointmentRepository,
    DoctorRepository,
    DocumentProcessingJobRepository,
    PatientAIContextRepository,
    PatientRepository,
)
from app.schemas.registration import (
    PatientAIContextOut,
    PatientRegistrationResponse,
    ProcessingJobOut,
)
from app.services.medical_storage_service import (
    medical_storage_service,
)

logger = get_logger("hospital_ai.intake.registration")

CURRENT_STAGE = "Patient Registration"
NEXT_STAGE = "Medical History Extraction"
JOB_STATUS_PENDING = "Pending"
CONTEXT_STATUS_INITIALIZED = "Initialized"


class StoragePort(Protocol):
    def validate_file(self, *, filename: str, content_type: str, size: int) -> str: ...

    def build_storage_path(
        self,
        *,
        patient_id: str,
        appointment_id: Optional[str],
        filename: str,
    ) -> str: ...

    def upload_bytes(
        self,
        *,
        storage_path: str,
        data: bytes,
        content_type: str,
    ) -> str: ...

    def delete_object(self, storage_path: str) -> None: ...


@dataclass
class ValidatedUpload:
    filename: str
    content_type: str
    size: int
    data: bytes


class PatientRegistrationService:
    """
    Intake Stage 1 — Patient Registration.

    Dependency-injected repositories + storage port for testability.
    """

    def __init__(
        self,
        *,
        patients: Optional[PatientRepository] = None,
        appointments: Optional[AppointmentRepository] = None,
        doctors: Optional[DoctorRepository] = None,
        jobs: Optional[DocumentProcessingJobRepository] = None,
        contexts: Optional[PatientAIContextRepository] = None,
        storage: Optional[StoragePort] = None,
    ) -> None:
        self._patients = patients or PatientRepository()
        self._appointments = appointments or AppointmentRepository()
        self._doctors = doctors or DoctorRepository()
        self._jobs = jobs or DocumentProcessingJobRepository()
        self._contexts = contexts or PatientAIContextRepository()
        self._storage: StoragePort = storage or medical_storage_service

    # ------------------------------------------------------------------
    # Validations
    # ------------------------------------------------------------------

    def validate_patient(self, patient_id: UUID) -> dict:
        patient = self._patients.get(patient_id)
        if not patient:
            raise HTTPException(status_code=400, detail="Patient not found")
        return patient

    def validate_doctor(self, doctor_id: UUID) -> dict:
        doctor = self._doctors.get(doctor_id)
        if not doctor:
            raise HTTPException(status_code=400, detail="Doctor not found")
        return doctor

    def validate_appointment(
        self,
        *,
        appointment_id: UUID,
        patient_id: UUID,
        doctor_id: UUID,
    ) -> dict:
        appointment = self._appointments.get(appointment_id)
        if not appointment:
            raise HTTPException(status_code=400, detail="Appointment not found")

        appt_patient = str(appointment.get("patient_id") or "")
        appt_doctor = str(appointment.get("doctor_id") or "")

        if appt_patient != str(patient_id):
            raise HTTPException(
                status_code=400,
                detail="Appointment does not belong to the selected patient",
            )
        if appt_doctor != str(doctor_id):
            raise HTTPException(
                status_code=400,
                detail="Appointment does not belong to the selected doctor",
            )
        return appointment

    async def validate_upload(
        self,
        *,
        patient_id: UUID,
        uploaded_document: UploadFile,
    ) -> ValidatedUpload:
        filename = (uploaded_document.filename or "").strip() or "upload.bin"
        data = await uploaded_document.read()
        size = len(data)
        content_type = uploaded_document.content_type or "application/octet-stream"

        mime = self._storage.validate_file(
            filename=filename,
            content_type=content_type,
            size=size,
        )

        duplicate = self._jobs.find_duplicate(
            patient_id=patient_id,
            document_name=filename,
            file_size=size,
        )
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Duplicate upload: same document name and size already "
                    "registered for this patient"
                ),
            )

        return ValidatedUpload(
            filename=filename,
            content_type=mime,
            size=size,
            data=data,
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def create_processing_job(
        self,
        *,
        patient_id: UUID,
        appointment_id: UUID,
        doctor_id: UUID,
        document_name: str,
        document_type: str,
        file_url: str,
        storage_path: str,
        file_size: int,
        created_by: Optional[UUID],
    ) -> dict:
        body = {
            "patient_id": str(patient_id),
            "appointment_id": str(appointment_id),
            "doctor_id": str(doctor_id),
            "document_name": document_name,
            "document_type": document_type,
            "file_url": file_url,
            "storage_path": storage_path,
            "file_size": file_size,
            "status": JOB_STATUS_PENDING,
            "current_stage": CURRENT_STAGE,
            "created_by": str(created_by) if created_by else None,
        }
        job = self._jobs.create(body)
        logger.info(
            "Created processing job id=%s patient=%s stage=%s",
            job.get("id"),
            patient_id,
            CURRENT_STAGE,
        )
        return job

    def initialize_patient_context(
        self,
        *,
        patient_id: UUID,
        processing_job_id: UUID,
        patient_label: str,
        document_name: str,
    ) -> dict:
        summary = (
            f"Patient Registration complete for {patient_label}. "
            f"Document '{document_name}' queued. "
            f"Ready for {NEXT_STAGE}."
        )
        context = self._contexts.upsert_for_patient(
            patient_id=patient_id,
            processing_job_id=processing_job_id,
            status=CONTEXT_STATUS_INITIALIZED,
            current_summary=summary,
        )
        logger.info(
            "Initialized patient AI context id=%s patient=%s job=%s",
            context.get("id"),
            patient_id,
            processing_job_id,
        )
        return context

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    async def register(
        self,
        *,
        patient_id: UUID,
        appointment_id: UUID,
        doctor_id: UUID,
        uploaded_document: UploadFile,
        created_by: Optional[UUID] = None,
    ) -> PatientRegistrationResponse:
        """
        Full Patient Registration workflow.

        Does not perform OCR, history extraction, NER, risk, or KG.
        """
        logger.info(
            "Patient Registration start patient=%s appointment=%s doctor=%s",
            patient_id,
            appointment_id,
            doctor_id,
        )

        patient = self.validate_patient(patient_id)
        doctor = self.validate_doctor(doctor_id)
        self.validate_appointment(
            appointment_id=appointment_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
        )
        upload = await self.validate_upload(
            patient_id=patient_id,
            uploaded_document=uploaded_document,
        )

        storage_path = self._storage.build_storage_path(
            patient_id=str(patient_id),
            appointment_id=str(appointment_id),
            filename=upload.filename,
        )
        file_url = self._storage.upload_bytes(
            storage_path=storage_path,
            data=upload.data,
            content_type=upload.content_type,
        )

        try:
            job = self.create_processing_job(
                patient_id=patient_id,
                appointment_id=appointment_id,
                doctor_id=doctor_id,
                document_name=upload.filename,
                document_type=upload.content_type,
                file_url=file_url,
                storage_path=storage_path,
                file_size=upload.size,
                created_by=created_by,
            )
            job_id = UUID(str(job["id"]))

            patient_label = (
                f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
                or str(patient_id)
            )
            context = self.initialize_patient_context(
                patient_id=patient_id,
                processing_job_id=job_id,
                patient_label=patient_label,
                document_name=upload.filename,
            )
        except Exception:
            self._storage.delete_object(storage_path)
            raise

        logger.info(
            "Patient Registration complete job=%s next_stage=%s doctor=%s",
            job_id,
            NEXT_STAGE,
            doctor.get("id"),
        )

        return PatientRegistrationResponse(
            job_id=job_id,
            status=str(job.get("status") or JOB_STATUS_PENDING),
            current_stage=str(job.get("current_stage") or CURRENT_STAGE),
            next_stage=NEXT_STAGE,
            ready_for_medical_history_extraction=True,
            processing_job=ProcessingJobOut.model_validate(job),
            patient_ai_context=PatientAIContextOut.model_validate(context),
        )


def get_patient_registration_service() -> PatientRegistrationService:
    """FastAPI dependency injection factory."""
    return PatientRegistrationService()
