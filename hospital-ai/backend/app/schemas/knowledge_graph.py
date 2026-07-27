"""Pydantic schemas for Intake Stage 6 — Patient Knowledge Graph."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.registration import ProcessingJobOut


class KnowledgeGraphStartRequest(BaseModel):
    job_id: UUID


class GraphNodeOut(BaseModel):
    id: str
    type: str
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphRelationshipOut(BaseModel):
    id: str
    type: str
    source: str
    target: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphOut(BaseModel):
    id: UUID
    processing_job_id: Optional[UUID] = None
    patient_id: UUID
    nodes_json: List[Any] = Field(default_factory=list)
    relationships_json: List[Any] = Field(default_factory=list)
    statistics_json: Dict[str, Any] = Field(default_factory=dict)
    patient_summary_json: Dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None
    graph_version: int = 1
    node_count: int = 0
    relationship_count: int = 0
    builder_logs_json: List[Any] = Field(default_factory=list)
    validation_json: Dict[str, Any] = Field(default_factory=dict)
    status: str = "Completed"
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class KnowledgeGraphStartResponse(BaseModel):
    job_id: UUID
    patient_id: UUID
    status: str
    current_stage: str = "Completed"
    next_stage: str = "Completed"
    intake_completed: bool = True
    node_count: int
    relationship_count: int
    graph_version: int
    processing_time_ms: int
    summary: str
    statistics: Dict[str, Any] = Field(default_factory=dict)
    patient_summary: Dict[str, Any] = Field(default_factory=dict)
    nodes: List[GraphNodeOut] = Field(default_factory=list)
    relationships: List[GraphRelationshipOut] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    knowledge_graph: KnowledgeGraphOut
    processing_job: ProcessingJobOut
    patient_context_version: int = 1


class KnowledgeGraphStatusResponse(BaseModel):
    job_id: UUID
    status: str
    current_stage: str
    next_stage: str
    progress_pct: int
    kg_completed: bool = False
    intake_completed: bool = False
    node_count: Optional[int] = None
    relationship_count: Optional[int] = None
    error_message: Optional[str] = None
    processing_job: ProcessingJobOut
