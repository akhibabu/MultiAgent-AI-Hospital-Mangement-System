"""Pydantic schemas for Intake Stage 3 — Document Processing / OCR."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.registration import ProcessingJobOut


class OCRStartRequest(BaseModel):
    job_id: UUID


class OCRResultOut(BaseModel):
    id: UUID
    processing_job_id: UUID
    patient_id: UUID
    document_id: Optional[UUID] = None
    provider: str
    raw_text: str
    clean_text: Optional[str] = None
    tables_json: List[Any] = Field(default_factory=list)
    images_json: List[Any] = Field(default_factory=list)
    detected_language: Optional[str] = None
    page_count: int = 1
    processing_time_ms: Optional[int] = None
    confidence: Optional[float] = None
    provenance_json: Dict[str, Any] = Field(default_factory=dict)
    extraction_method: Optional[str] = None
    processing_method: Optional[str] = None
    document_type: Optional[str] = None
    ocr_provider: Optional[str] = None
    library_used: Optional[str] = None
    fallback_used: Optional[bool] = None
    document_status: Optional[str] = None
    status: Optional[str] = None
    character_count: Optional[int] = None
    word_count: Optional[int] = None
    processing_logs: Optional[List[Any]] = None
    error_message: Optional[str] = None
    created_at: datetime


class OCRStartResponse(BaseModel):
    job_id: UUID
    patient_id: UUID
    status: str
    current_stage: str
    next_stage: str = "Medical Entity Recognition"
    provider: str
    confidence: float
    page_count: int
    processing_time_ms: int
    detected_language: str
    extraction_method: str = "embedded_text"
    processing_method: str = "embedded_text"
    document_type: str = "digital_pdf"
    ocr_provider: Optional[str] = None
    library_used: str = ""
    fallback_used: bool = False
    document_status: str = "Completed"
    character_count: int = 0
    word_count: int = 0
    warnings: List[str] = Field(default_factory=list)
    ocr_result: OCRResultOut
    processing_job: ProcessingJobOut
    patient_context_version: int = 1


class OCRStatusResponse(BaseModel):
    job_id: UUID
    status: str
    current_stage: str
    next_stage: str
    progress_pct: int
    provider: Optional[str] = None
    confidence: Optional[float] = None
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    ocr_completed: bool = False
    processing_job: ProcessingJobOut


class OCRReportOut(BaseModel):
    """Staff-facing medical report view — cleaned text only."""

    report_id: str
    file_name: str
    document_type: str
    processing_method: Optional[str] = None
    extraction_method: Optional[str] = None
    ocr_provider: Optional[str] = None
    upload_date: Optional[datetime] = None
    language: Optional[str] = None
    pages: int = 1
    confidence: Optional[float] = None
    processing_time_ms: Optional[int] = None
    status: str
    character_count: Optional[int] = None
    word_count: Optional[int] = None
    text_preview: str
    full_text: str


class PatientContextResponse(BaseModel):
    patient_id: UUID
    status: str
    current_summary: Optional[str] = None
    ocr_completed: bool = False
    ocr_provider: Optional[str] = None
    ocr_confidence: Optional[float] = None
    ocr_timestamp: Optional[datetime] = None
    context_version: int = 1
    patient_context_json: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
