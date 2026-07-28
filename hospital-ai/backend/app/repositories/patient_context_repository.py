"""
Shared read-only aggregator over Intake Agent outputs.

Diagnosis Agent and Research Agent MUST consume patient data exclusively
through this repository. It never writes to Intake-owned tables
(`patient_ai_context`, `patient_medical_history`, `patient_risk_profiles`,
`medical_entity_results`, `patient_knowledge_graphs`) — read only.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.repositories.intake_repositories import (
    PatientAIContextRepository,
    PatientMedicalHistoryRepository,
    PatientRepository,
)
from app.repositories.knowledge_graph_repository import (
    PatientKnowledgeGraphRepository,
)
from app.repositories.risk_repository import PatientRiskProfileRepository


def _flat_ner_entities(ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """`ner_result.entities` is a FLAT list of `{type, value, metadata, ...}` dicts."""
    ner_result = ctx.get("ner_result")
    if isinstance(ner_result, dict):
        entities = ner_result.get("entities")
        if isinstance(entities, list):
            return [e for e in entities if isinstance(e, dict)]
    entities = ctx.get("medical_entities")
    return [e for e in entities if isinstance(e, dict)] if isinstance(entities, list) else []


def _entities_of_type(entities: List[Dict[str, Any]], type_name: str) -> List[Dict[str, Any]]:
    return [e for e in entities if str(e.get("type", "")).lower() == type_name.lower()]


def _lab_values_from_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    labs = []
    for e in _entities_of_type(entities, "Lab Value"):
        meta = e.get("metadata") or {}
        labs.append(
            {
                "name": meta.get("name") or e.get("value"),
                "value": meta.get("value") or "",
                "unit": meta.get("unit"),
            }
        )
    return labs


class PatientClinicalContext(BaseModel):
    """Aggregated, read-only view of everything the Intake Agent produced."""

    patient_id: str
    patient_name: str = "Patient"
    patient_number: Optional[str] = None
    age_years: Optional[int] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None

    medical_history_summary: str = ""
    conditions: List[str] = Field(default_factory=list)
    symptoms: List[str] = Field(default_factory=list)
    medications: List[Dict[str, Any]] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    vitals: List[Dict[str, Any]] = Field(default_factory=list)
    lab_values: List[Dict[str, Any]] = Field(default_factory=list)
    lab_tests: List[str] = Field(default_factory=list)
    procedures: List[str] = Field(default_factory=list)
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    previous_diagnoses: List[str] = Field(default_factory=list)

    risk_overall_level: Optional[str] = None
    risk_overall_score: Optional[float] = None
    risk_categories: List[Dict[str, Any]] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    risk_alerts: List[Dict[str, Any]] = Field(default_factory=list)

    knowledge_graph_nodes: List[Dict[str, Any]] = Field(default_factory=list)
    knowledge_graph_relationships: List[Dict[str, Any]] = Field(default_factory=list)
    knowledge_graph_summary: Optional[str] = None
    knowledge_graph_version: int = 0

    is_valid: bool = False
    validation_warnings: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class PatientClinicalContextRepository:
    """
    Loads and validates the full Intake output bundle for one patient.

    Sole entry point for the "Patient Context -> Load Knowledge Graph ->
    Validate Patient Information" steps shared by Diagnosis and Research.
    """

    def __init__(
        self,
        *,
        patients: Optional[PatientRepository] = None,
        contexts: Optional[PatientAIContextRepository] = None,
        histories: Optional[PatientMedicalHistoryRepository] = None,
        risk_repo: Optional[PatientRiskProfileRepository] = None,
        graphs: Optional[PatientKnowledgeGraphRepository] = None,
    ) -> None:
        self._patients = patients or PatientRepository()
        self._contexts = contexts or PatientAIContextRepository()
        self._histories = histories or PatientMedicalHistoryRepository()
        self._risk_repo = risk_repo or PatientRiskProfileRepository()
        self._graphs = graphs or PatientKnowledgeGraphRepository()

    def load(self, patient_id: UUID) -> PatientClinicalContext:
        patient_row = self._patients.get_full(patient_id) or {}
        ctx_row = self._contexts.get_by_patient(patient_id) or {}
        ctx: Dict[str, Any] = (
            ctx_row.get("patient_context_json")
            if isinstance(ctx_row.get("patient_context_json"), dict)
            else {}
        ) or {}

        history_row = self._histories.get_by_patient(patient_id) or {}
        history_json: Dict[str, Any] = (
            history_row.get("medical_history_json")
            if isinstance(history_row.get("medical_history_json"), dict)
            else {}
        ) or {}
        timeline = history_row.get("timeline_json") or ctx.get("timeline") or []

        risk_row = self._risk_repo.get_by_job(
            UUID(str(ctx_row["processing_job_id"]))
        ) if ctx_row.get("processing_job_id") else None
        if not risk_row:
            overall = ctx.get("overall_risk") or {}
            risk_row = {
                "overall_level": overall.get("level"),
                "overall_score": overall.get("score"),
                "categories_json": ctx.get("risk_categories") or [],
                "top_risk_factors_json": ctx.get("risk_factors") or [],
                "alerts_json": ctx.get("risk_alerts") or [],
            }

        graph_row = self._graphs.get_latest_for_patient(patient_id) or {}

        full_name = (
            patient_row.get("full_name")
            or " ".join(
                filter(
                    None,
                    [patient_row.get("first_name"), patient_row.get("last_name")],
                )
            ).strip()
            or "Patient"
        )

        age_years = self._age_years(patient_row.get("date_of_birth"))

        flat_entities = _flat_ner_entities(ctx)

        symptoms = ctx.get("recognized_symptoms") or [
            e.get("value") for e in _entities_of_type(flat_entities, "Symptom")
        ]
        conditions = (
            ctx.get("recognized_diseases")
            or history_json.get("conditions")
            or []
        )
        medications = (
            ctx.get("recognized_medications")
            or history_json.get("medications")
            or []
        )
        if medications and isinstance(medications[0], str):
            medications = [{"name": m} for m in medications]

        allergies = (
            ctx.get("recognized_allergies")
            or history_json.get("allergies")
            or patient_row.get("allergies")
            or []
        )
        if isinstance(allergies, str):
            allergies = [a.strip() for a in allergies.split(",") if a.strip()]

        vitals = ctx.get("recognized_vitals") or []
        lab_tests = ctx.get("recognized_tests") or []
        lab_values = _lab_values_from_entities(flat_entities)
        procedures = ctx.get("recognized_procedures") or []

        previous_diagnoses = (
            history_json.get("previous_diagnoses")
            or history_json.get("conditions")
            or []
        )

        warnings: List[str] = []
        if not patient_row:
            warnings.append("Patient record not found.")
        if not symptoms and not conditions:
            warnings.append(
                "No recognized symptoms or conditions found — diagnosis "
                "confidence will be limited."
            )
        if not ctx_row:
            warnings.append(
                "Patient has no Intake Agent context yet — complete Intake "
                "stages before running Diagnosis."
            )

        is_valid = bool(patient_row) and (bool(symptoms) or bool(conditions))

        return PatientClinicalContext(
            patient_id=str(patient_id),
            patient_name=full_name,
            patient_number=patient_row.get("patient_number"),
            age_years=age_years,
            gender=patient_row.get("gender"),
            blood_group=patient_row.get("blood_group"),
            medical_history_summary=(
                history_json.get("latest_summary")
                or ctx.get("knowledge_graph_summary")
                or ""
            ),
            conditions=list(conditions),
            symptoms=list(symptoms),
            medications=list(medications),
            allergies=list(allergies),
            vitals=list(vitals),
            lab_values=list(lab_values),
            lab_tests=list(lab_tests),
            procedures=list(procedures),
            timeline=list(timeline) if isinstance(timeline, list) else [],
            previous_diagnoses=list(previous_diagnoses),
            risk_overall_level=risk_row.get("overall_level"),
            risk_overall_score=risk_row.get("overall_score"),
            risk_categories=risk_row.get("categories_json") or [],
            risk_factors=risk_row.get("top_risk_factors_json") or [],
            risk_alerts=risk_row.get("alerts_json") or [],
            knowledge_graph_nodes=graph_row.get("nodes_json") or [],
            knowledge_graph_relationships=graph_row.get("relationships_json") or [],
            knowledge_graph_summary=graph_row.get("summary"),
            knowledge_graph_version=int(graph_row.get("graph_version") or 0),
            is_valid=is_valid,
            validation_warnings=warnings,
        )

    @staticmethod
    def _age_years(dob: Optional[str]) -> Optional[int]:
        if not dob:
            return None
        try:
            from datetime import date

            born = date.fromisoformat(str(dob)[:10])
            today = date.today()
            return today.year - born.year - (
                (today.month, today.day) < (born.month, born.day)
            )
        except Exception:  # noqa: BLE001
            return None
