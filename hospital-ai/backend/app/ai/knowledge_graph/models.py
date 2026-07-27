"""Knowledge graph domain models — Neo4j-ready JSON representation."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    PATIENT = "Patient"
    DISEASE = "Disease"
    SYMPTOM = "Symptom"
    MEDICATION = "Medication"
    ALLERGY = "Allergy"
    DOCTOR = "Doctor"
    HOSPITAL = "Hospital"
    DEPARTMENT = "Department"
    APPOINTMENT = "Appointment"
    PROCEDURE = "Procedure"
    LAB_TEST = "LabTest"
    VITAL_SIGN = "VitalSign"
    MEDICAL_REPORT = "MedicalReport"
    INSURANCE = "Insurance"
    EMERGENCY_CONTACT = "EmergencyContact"
    RISK_FACTOR = "RiskFactor"
    # Legacy aliases
    MEDICAL_RECORD = "MedicalRecord"
    LAB_REPORT = "LabReport"


class EdgeType(str, Enum):
    HAS_DISEASE = "HAS_DISEASE"
    HAS_SYMPTOM = "HAS_SYMPTOM"
    TAKES_MEDICATION = "TAKES_MEDICATION"
    TREATED_WITH = "TREATED_WITH"
    HAS_ALLERGY = "HAS_ALLERGY"
    ALLERGIC_TO = "ALLERGIC_TO"
    UNDERWENT_PROCEDURE = "UNDERWENT_PROCEDURE"
    UNDERWENT = "UNDERWENT"
    VISITED_DOCTOR = "VISITED_DOCTOR"
    TREATED_BY = "TREATED_BY"
    VISITED_HOSPITAL = "VISITED_HOSPITAL"
    HAS_LAB_RESULT = "HAS_LAB_RESULT"
    HAS_LAB = "HAS_LAB"
    HAS_VITAL = "HAS_VITAL"
    HAS_RISK = "HAS_RISK"
    GENERATED_REPORT = "GENERATED_REPORT"
    HAS_RECORD = "HAS_RECORD"
    FOLLOW_UP = "FOLLOW_UP"
    REFERRED_TO = "REFERRED_TO"
    ATTENDED_APPOINTMENT = "ATTENDED_APPOINTMENT"
    HAS_APPOINTMENT = "HAS_APPOINTMENT"
    MONITORED_BY = "MONITORED_BY"
    RECORDED_IN = "RECORDED_IN"
    RELATED_TO = "RELATED_TO"
    HAS_INSURANCE = "HAS_INSURANCE"
    HAS_EMERGENCY_CONTACT = "HAS_EMERGENCY_CONTACT"
    BELONGS_TO_DEPARTMENT = "BELONGS_TO_DEPARTMENT"


class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    type: str
    source: str
    target: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphStatistics(BaseModel):
    total_nodes: int = 0
    total_relationships: int = 0
    diseases: int = 0
    symptoms: int = 0
    medications: int = 0
    doctors: int = 0
    reports: int = 0
    hospitals: int = 0
    appointments: int = 0
    procedures: int = 0
    allergies: int = 0
    vitals: int = 0
    lab_tests: int = 0
    risk_factors: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class PatientSummaryCard(BaseModel):
    patient_name: str = ""
    age: Optional[int] = None
    conditions: List[str] = Field(default_factory=list)
    current_medications: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    recent_procedures: List[str] = Field(default_factory=list)
    risk_level: Optional[str] = None
    recent_visits: List[str] = Field(default_factory=list)
    graph_statistics: Dict[str, int] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class PatientKnowledgeGraph(BaseModel):
    """
    Portable patient knowledge graph.

    Stored as JSONB today; designed so Neo4j can ingest the same
    nodes/relationships without changing upstream agents.
    """

    patient_id: str
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    relationships: List[GraphEdge] = Field(default_factory=list)  # alias for edges
    summary: Optional[str] = None
    statistics: Optional[GraphStatistics] = None
    patient_summary: Optional[PatientSummaryCard] = None
    graph_version: int = 1
    builder_logs: List[str] = Field(default_factory=list)
    validation: Dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if self.edges and not self.relationships:
            self.relationships = list(self.edges)
        elif self.relationships and not self.edges:
            self.edges = list(self.relationships)

    def preview(self, limit: int = 20) -> Dict[str, Any]:
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "nodes": [n.model_dump() for n in self.nodes[:limit]],
            "edges": [e.model_dump() for e in self.edges[:limit]],
            "summary": self.summary,
            "graph_version": self.graph_version,
        }

    def to_dict(self) -> Dict[str, Any]:
        data = self.model_dump(mode="json")
        data["relationships"] = data.get("edges") or data.get("relationships") or []
        return data
