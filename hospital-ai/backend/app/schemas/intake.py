"""Intake Agent API schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class IntakeProcessRequest(BaseModel):
    document_id: UUID
    # Optional explicit linkage checks
    patient_id: Optional[UUID] = None
    appointment_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None


class IntakeProcessResponse(BaseModel):
    job_id: str
    patient_id: str
    document_id: str
    status: str
    patient_context: Dict[str, Any]
    entities: Dict[str, Any]
    risk_profile: Dict[str, Any]
    knowledge_graph: Dict[str, Any]
    ocr: Dict[str, Any]
    timeline: List[Dict[str, Any]]
    confidence_score: float
    diagnosis_request_preview: Optional[Dict[str, Any]] = None


class DocumentJobResponse(BaseModel):
    id: UUID
    patient_id: UUID
    medical_record_id: Optional[UUID] = None
    document_id: Optional[UUID] = None
    appointment_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    status: str
    current_step: Optional[str] = None
    progress_pct: int = 0
    ocr_provider: Optional[str] = None
    ocr_text: Optional[str] = None
    ocr_confidence: Optional[float] = None
    extracted_entities: Optional[Any] = None
    risk_profile: Optional[Any] = None
    knowledge_graph_refs: Optional[Any] = None
    patient_context: Optional[Any] = None
    timeline: Optional[Any] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class DocumentJobListResponse(BaseModel):
    items: List[DocumentJobResponse]
    total: int


class PatientAIContextResponse(BaseModel):
    id: UUID
    patient_id: UUID
    context_version: int
    context_json: Dict[str, Any]
    medical_history_summary: Optional[str] = None
    risk_level: Optional[str] = None
    risk_profile: Optional[Any] = None
    confidence_score: Optional[float] = None
    knowledge_graph_id: Optional[UUID] = None
    source_job_ids: Optional[List[UUID]] = None
    source_document_ids: Optional[List[UUID]] = None
    built_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class KnowledgeGraphResponse(BaseModel):
    id: UUID
    patient_id: UUID
    graph_version: int
    nodes: List[Any] = Field(default_factory=list)
    edges: List[Any] = Field(default_factory=list)
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class IntakeDashboardResponse(BaseModel):
    patient_id: str
    context: Optional[PatientAIContextResponse] = None
    knowledge_graph: Optional[KnowledgeGraphResponse] = None
    jobs: List[DocumentJobResponse] = Field(default_factory=list)
    documents: List[Dict[str, Any]] = Field(default_factory=list)
