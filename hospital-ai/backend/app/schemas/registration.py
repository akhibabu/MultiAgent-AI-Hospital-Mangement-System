"""Pydantic schemas for Intake Patient Registration (stage 1)."""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProcessingJobOut(BaseModel):
    id: UUID
    patient_id: UUID
    appointment_id: UUID
    doctor_id: UUID
    document_name: str
    document_type: str
    file_url: str
    storage_path: Optional[str] = None
    file_size: Optional[int] = None
    status: str
    current_stage: str
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PatientAIContextOut(BaseModel):
    id: UUID
    patient_id: UUID
    processing_job_id: Optional[UUID] = None
    status: str
    current_summary: Optional[str] = None
    ocr_completed: Optional[bool] = None
    ocr_provider: Optional[str] = None
    ocr_confidence: Optional[float] = None
    ocr_timestamp: Optional[datetime] = None
    patient_context_json: Optional[Dict] = None
    context_version: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class PatientRegistrationResponse(BaseModel):
    """Output of POST /ai/intake/register."""

    job_id: UUID
    status: str
    current_stage: str
    next_stage: str = Field(
        default="Medical History Extraction",
        description="Next Intake stage — not executed by this endpoint",
    )
    ready_for_medical_history_extraction: bool = True
    processing_job: ProcessingJobOut
    patient_ai_context: PatientAIContextOut
