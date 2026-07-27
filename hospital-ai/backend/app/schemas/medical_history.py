"""Pydantic schemas for Intake Medical History Extraction (stage 2)."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.registration import ProcessingJobOut


class TimelineEvent(BaseModel):
    date: Optional[str] = None
    event_type: str
    doctor: Optional[str] = None
    department: Optional[str] = None
    summary: str
    reference_id: Optional[str] = None


class UnifiedMedicalHistory(BaseModel):
    patient: Dict[str, Any] = Field(default_factory=dict)
    allergies: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    surgeries: List[str] = Field(default_factory=list)
    lab_reports: List[Dict[str, Any]] = Field(default_factory=list)
    appointments: List[Dict[str, Any]] = Field(default_factory=list)
    reports: List[Dict[str, Any]] = Field(default_factory=list)
    doctors: List[Dict[str, Any]] = Field(default_factory=list)
    departments: List[Dict[str, Any]] = Field(default_factory=list)
    insurance: Dict[str, Any] = Field(default_factory=dict)
    previous_treatments: List[str] = Field(default_factory=list)
    previous_diagnoses: List[str] = Field(default_factory=list)
    previous_ai_context: Optional[Dict[str, Any]] = None
    timeline: List[TimelineEvent] = Field(default_factory=list)
    latest_summary: str = ""
    warnings: List[str] = Field(default_factory=list)


class PatientMedicalHistoryRecord(BaseModel):
    id: UUID
    patient_id: UUID
    processing_job_id: Optional[UUID] = None
    medical_history_json: Dict[str, Any]
    timeline_json: List[Any] = Field(default_factory=list)
    last_updated: datetime
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MedicalHistoryExtractRequest(BaseModel):
    job_id: UUID


class MedicalHistoryResponse(BaseModel):
    """GET /ai/intake/history/{patient_id} (+ extract response)."""

    patient_id: UUID
    processing_job: Optional[ProcessingJobOut] = None
    medical_history: Optional[UnifiedMedicalHistory] = None
    timeline: List[TimelineEvent] = Field(default_factory=list)
    current_stage: str
    next_stage: str = "OCR"
    warnings: List[str] = Field(default_factory=list)
    history_record: Optional[PatientMedicalHistoryRecord] = None
