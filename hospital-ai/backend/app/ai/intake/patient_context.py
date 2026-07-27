"""Canonical Patient Context JSON — sole input contract for downstream AI agents."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.ai.ner.extractor import ExtractedMedicalEntities, LabValueEntity, MedicationEntity, VitalEntity
from app.ai.risk.profiler import PatientRiskProfile


class PatientIdentity(BaseModel):
    id: str
    patient_number: Optional[str] = None
    full_name: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None


class PatientContext(BaseModel):
    """
    Standardized context produced exclusively by the Intake Agent.

    Diagnosis Agent and all other agents consume this object — never raw documents.
    """

    schema_version: str = "1.0"
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    patient: PatientIdentity
    medical_history: str = ""
    current_symptoms: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    medications: List[MedicationEntity] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    lab_results: List[LabValueEntity] = Field(default_factory=list)
    vitals: List[VitalEntity] = Field(default_factory=list)
    procedures: List[str] = Field(default_factory=list)
    medical_codes: List[str] = Field(default_factory=list)
    risk_profile: PatientRiskProfile
    knowledge_graph_references: Dict[str, Any] = Field(default_factory=dict)
    source_document_ids: List[str] = Field(default_factory=list)
    source_job_ids: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    entities: Optional[ExtractedMedicalEntities] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")
