"""Pydantic schemas for Intake Stage 4 — Medical Entity Recognition."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.registration import ProcessingJobOut


class NERStartRequest(BaseModel):
    job_id: UUID


class MedicalEntityOut(BaseModel):
    id: Optional[UUID] = None
    type: str
    value: str
    confidence: float
    source_document: Optional[str] = None
    page: int = 1
    sentence: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    extraction_time: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EntityStatistics(BaseModel):
    disease_count: int = 0
    medication_count: int = 0
    symptom_count: int = 0
    allergy_count: int = 0
    vital_count: int = 0
    lab_value_count: int = 0
    lab_test_count: int = 0
    procedure_count: int = 0
    dosage_count: int = 0
    date_count: int = 0
    doctor_count: int = 0
    hospital_count: int = 0
    body_part_count: int = 0
    total_entities: int = 0


class PatientEntitySummary(BaseModel):
    conditions: List[str] = Field(default_factory=list)
    current_medications: List[Dict[str, Any]] = Field(default_factory=list)
    symptoms: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    recent_tests: List[str] = Field(default_factory=list)
    recent_procedures: List[str] = Field(default_factory=list)
    vitals: List[Dict[str, Any]] = Field(default_factory=list)
    follow_up: List[str] = Field(default_factory=list)
    doctors: List[str] = Field(default_factory=list)
    hospitals: List[str] = Field(default_factory=list)


class NERResultOut(BaseModel):
    id: UUID
    processing_job_id: UUID
    patient_id: UUID
    ocr_result_id: Optional[UUID] = None
    entity_count: int = 0
    statistics_json: Dict[str, Any] = Field(default_factory=dict)
    summary_json: Dict[str, Any] = Field(default_factory=dict)
    entities_json: List[Any] = Field(default_factory=list)
    source_text_preview: Optional[str] = None
    confidence: Optional[float] = None
    processing_time_ms: Optional[int] = None
    status: str = "Completed"
    error_message: Optional[str] = None
    created_at: datetime


class NERStartResponse(BaseModel):
    job_id: UUID
    patient_id: UUID
    status: str
    current_stage: str
    next_stage: str = "Patient Risk Profiling"
    entity_count: int
    confidence: float
    processing_time_ms: int
    statistics: EntityStatistics
    summary: PatientEntitySummary
    entities: List[MedicalEntityOut]
    source_text: str
    warnings: List[str] = Field(default_factory=list)
    ner_result: NERResultOut
    processing_job: ProcessingJobOut
    patient_context_version: int = 1


class NERStatusResponse(BaseModel):
    job_id: UUID
    status: str
    current_stage: str
    next_stage: str
    progress_pct: int
    ner_completed: bool = False
    entity_count: Optional[int] = None
    confidence: Optional[float] = None
    error_message: Optional[str] = None
    processing_job: ProcessingJobOut
