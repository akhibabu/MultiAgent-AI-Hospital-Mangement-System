"""
KnowledgeGraphBuilder — Intake Agent Stage 6.

Builds a portable patient knowledge graph from NER, risk, history, and context.
JSON storage today; Neo4j-compatible node/relationship shape for later migration.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from app.ai.knowledge_graph.builders import NodeBuilder, RelationshipBuilder
from app.ai.knowledge_graph.models import (
    EdgeType,
    NodeType,
    PatientKnowledgeGraph,
    PatientSummaryCard,
)
from app.ai.knowledge_graph.ops import GraphSerializer, GraphValidator, compute_statistics
from app.ai.ner.extractor import ExtractedMedicalEntities
from app.ai.risk.profiler import PatientRiskAssessment, PatientRiskProfile
from app.core.logging import get_logger

logger = get_logger("hospital_ai.knowledge_graph.builder")


class KnowledgeGraphBuilder:
    """
    Orchestrates NodeBuilder + RelationshipBuilder + validation + serialization.
    """

    def __init__(
        self,
        *,
        validator: Optional[GraphValidator] = None,
        serializer: Optional[GraphSerializer] = None,
    ) -> None:
        self._validator = validator or GraphValidator()
        self._serializer = serializer or GraphSerializer()

    def build(
        self,
        *,
        patient_id: str,
        patient_label: str,
        entities: ExtractedMedicalEntities,
        risk: Optional[PatientRiskAssessment | PatientRiskProfile | Dict[str, Any]] = None,
        medical_history: Optional[Dict[str, Any]] = None,
        timeline: Optional[List[Any]] = None,
        doctor_ids: Optional[List[str]] = None,
        appointment_ids: Optional[List[str]] = None,
        medical_record_ids: Optional[List[str]] = None,
        document_name: Optional[str] = None,
        graph_version: int = 1,
        age_years: Optional[int] = None,
        hospital_names: Optional[List[str]] = None,
        department: Optional[str] = None,
    ) -> PatientKnowledgeGraph:
        nodes = NodeBuilder()
        rels = RelationshipBuilder()
        history = medical_history or {}
        source = document_name or "Intake report"

        overall_level, overall_score, risk_factors = self._risk_fields(risk)

        patient_node = nodes.add(
            NodeType.PATIENT,
            patient_label or "Patient",
            patient_id=patient_id,
            risk_level=overall_level,
            risk_score=overall_score,
            age_years=age_years,
            confidence=1.0,
            source_report=source,
        )

        # Diseases + medications (with treated_with / monitored_by)
        disease_ids: Dict[str, str] = {}
        for disease in entities.diseases or []:
            did = nodes.add(
                NodeType.DISEASE,
                disease,
                confidence=0.9,
                source_report=source,
            )
            disease_ids[disease.lower()] = did
            rels.add(EdgeType.HAS_DISEASE, patient_node, did)

        for med in entities.medications or []:
            mid = nodes.add(
                NodeType.MEDICATION,
                med.name,
                dosage=med.dosage,
                frequency=med.frequency,
                confidence=0.88,
                source_report=source,
            )
            rels.add(EdgeType.TAKES_MEDICATION, patient_node, mid)
            # Link common disease→medication when both present
            for dlabel, did in disease_ids.items():
                if any(
                    k in dlabel
                    for k in ("diabetes", "hypertension", "pneumonia", "asthma", "copd")
                ):
                    rels.add(EdgeType.TREATED_WITH, did, mid)

        for symptom in entities.symptoms or []:
            sid = nodes.add(
                NodeType.SYMPTOM, symptom, confidence=0.82, source_report=source
            )
            rels.add(EdgeType.HAS_SYMPTOM, patient_node, sid)

        for allergy in entities.allergies or history.get("allergies") or []:
            label = allergy if isinstance(allergy, str) else str(allergy)
            aid = nodes.add(
                NodeType.ALLERGY, label, confidence=0.85, source_report=source
            )
            rels.add(EdgeType.HAS_ALLERGY, patient_node, aid)
            rels.add(EdgeType.ALLERGIC_TO, patient_node, aid)

        for proc in entities.procedures or []:
            pid = nodes.add(
                NodeType.PROCEDURE, proc, confidence=0.84, source_report=source
            )
            rels.add(EdgeType.UNDERWENT_PROCEDURE, patient_node, pid)

        for lab in entities.lab_values or []:
            lid = nodes.add(
                NodeType.LAB_TEST,
                lab.name,
                value=lab.value,
                unit=lab.unit,
                confidence=0.9,
                source_report=source,
            )
            rels.add(EdgeType.HAS_LAB_RESULT, patient_node, lid)
            # Diabetes monitored by glucose labs
            for dlabel, did in disease_ids.items():
                if "diabetes" in dlabel and (
                    "glucose" in lab.name.lower() or "hba1c" in lab.name.lower()
                ):
                    rels.add(EdgeType.MONITORED_BY, did, lid)

        for test in entities.lab_tests or []:
            if nodes.get(NodeType.LAB_TEST, test):
                continue
            tid = nodes.add(
                NodeType.LAB_TEST, test, confidence=0.8, source_report=source
            )
            rels.add(EdgeType.HAS_LAB_RESULT, patient_node, tid)

        for vital in entities.vitals or []:
            vid = nodes.add(
                NodeType.VITAL_SIGN,
                vital.name,
                value=vital.value,
                unit=vital.unit,
                confidence=0.92,
                source_report=source,
            )
            rels.add(EdgeType.HAS_VITAL, patient_node, vid)
            for dlabel, did in disease_ids.items():
                if "hypertension" in dlabel or "blood pressure" in vital.name.lower():
                    if "blood pressure" in vital.name.lower() or vital.name.upper() == "BP":
                        rels.add(EdgeType.MONITORED_BY, did, vid)

        for doc_name in entities.doctor_names or []:
            did = nodes.add(
                NodeType.DOCTOR, doc_name, confidence=0.85, source_report=source
            )
            rels.add(EdgeType.VISITED_DOCTOR, patient_node, did)
            rels.add(EdgeType.TREATED_BY, patient_node, did)

        hospitals = list(entities.hospital_names or []) + list(hospital_names or [])
        for hosp in hospitals:
            hid = nodes.add(
                NodeType.HOSPITAL, hosp, confidence=0.9, source_report=source
            )
            rels.add(EdgeType.VISITED_HOSPITAL, patient_node, hid)

        if department:
            dep_id = nodes.add(NodeType.DEPARTMENT, department)
            rels.add(EdgeType.BELONGS_TO_DEPARTMENT, patient_node, dep_id)

        for appt_id in appointment_ids or []:
            aid = nodes.add(
                NodeType.APPOINTMENT,
                f"Appointment {str(appt_id)[:8]}",
                appointment_id=str(appt_id),
            )
            rels.add(EdgeType.ATTENDED_APPOINTMENT, patient_node, aid)
            rels.add(EdgeType.HAS_APPOINTMENT, patient_node, aid)

        for record_id in medical_record_ids or []:
            rid = nodes.add(
                NodeType.MEDICAL_REPORT,
                f"Report {str(record_id)[:8]}",
                medical_record_id=str(record_id),
                source_report=source,
            )
            rels.add(EdgeType.GENERATED_REPORT, patient_node, rid)
            rels.add(EdgeType.HAS_RECORD, patient_node, rid)
            # Link diseases to report
            for did in disease_ids.values():
                rels.add(EdgeType.RECORDED_IN, did, rid)

        if document_name:
            rid = nodes.add(
                NodeType.MEDICAL_REPORT,
                document_name,
                source_report=document_name,
                confidence=0.95,
            )
            rels.add(EdgeType.GENERATED_REPORT, patient_node, rid)

        # Risk factors
        for factor in risk_factors[:12]:
            fid = nodes.add(
                NodeType.RISK_FACTOR,
                factor[:120],
                risk_level=overall_level,
                confidence=0.75,
                source_report=source,
            )
            rels.add(EdgeType.HAS_RISK, patient_node, fid)

        # History enrichments
        for cond in history.get("previous_diagnoses") or history.get("conditions") or []:
            label = str(cond)
            if not nodes.get(NodeType.DISEASE, label):
                did = nodes.add(NodeType.DISEASE, label, source="medical_history")
                rels.add(EdgeType.HAS_DISEASE, patient_node, did)

        for med in history.get("medications") or []:
            label = str(med) if not isinstance(med, dict) else str(med.get("name") or med)
            if label and not nodes.get(NodeType.MEDICATION, label):
                mid = nodes.add(NodeType.MEDICATION, label, source="medical_history")
                rels.add(EdgeType.TAKES_MEDICATION, patient_node, mid)

        # Insurance / emergency contact if present in history patient blob
        patient_blob = history.get("patient") or {}
        if patient_blob.get("insurance_provider") or patient_blob.get("insurance"):
            ins = str(
                patient_blob.get("insurance_provider")
                or patient_blob.get("insurance")
            )
            iid = nodes.add(NodeType.INSURANCE, ins)
            rels.add(EdgeType.HAS_INSURANCE, patient_node, iid)
        if patient_blob.get("emergency_contact") or patient_blob.get(
            "emergency_contact_name"
        ):
            ec = str(
                patient_blob.get("emergency_contact_name")
                or patient_blob.get("emergency_contact")
            )
            eid = nodes.add(NodeType.EMERGENCY_CONTACT, ec)
            rels.add(EdgeType.HAS_EMERGENCY_CONTACT, patient_node, eid)

        # Follow-up dates
        for fu in entities.follow_up_dates or []:
            # Soft relationship via appointment-like node
            fid = nodes.add(NodeType.APPOINTMENT, f"Follow-up: {fu}", follow_up=fu)
            rels.add(EdgeType.FOLLOW_UP, patient_node, fid)

        # Timeline visits
        recent_visits: List[str] = []
        for item in (timeline or [])[-5:]:
            if isinstance(item, dict):
                title = str(item.get("title") or item.get("event") or "Visit")
                recent_visits.append(title)

        stats = compute_statistics(nodes.nodes, rels.edges)
        summary_card = PatientSummaryCard(
            patient_name=patient_label,
            age=age_years,
            conditions=list(entities.diseases or [])[:10],
            current_medications=[
                " ".join(
                    filter(
                        None,
                        [m.name, m.dosage or "", m.frequency or ""],
                    )
                ).strip()
                for m in (entities.medications or [])
            ][:10],
            allergies=list(entities.allergies or history.get("allergies") or [])[:10],
            recent_procedures=list(entities.procedures or [])[:8],
            risk_level=overall_level,
            recent_visits=recent_visits,
            graph_statistics=stats.to_dict(),
        )

        summary = (
            f"Knowledge graph for {patient_label}: "
            f"{stats.total_nodes} nodes, {stats.total_relationships} relationships; "
            f"overall risk={overall_level or 'n/a'}"
        )

        graph = PatientKnowledgeGraph(
            patient_id=patient_id,
            nodes=nodes.nodes,
            edges=rels.edges,
            relationships=rels.edges,
            summary=summary,
            statistics=stats,
            patient_summary=summary_card,
            graph_version=graph_version,
            builder_logs=nodes.logs + rels.logs,
        )
        graph.validation = self._validator.validate(graph)
        if not graph.validation.get("valid"):
            logger.warning(
                "KG validation issues patient=%s errors=%s",
                patient_id,
                graph.validation.get("errors"),
            )
        return graph

    def serialize(self, graph: PatientKnowledgeGraph) -> Dict[str, Any]:
        return self._serializer.to_storage(graph)

    def _risk_fields(
        self, risk: Any
    ) -> tuple[Optional[str], Optional[float], List[str]]:
        if risk is None:
            return None, None, []
        if isinstance(risk, PatientRiskAssessment):
            return (
                risk.overall_level,
                risk.overall_score,
                list(risk.top_risk_factors or []),
            )
        if isinstance(risk, PatientRiskProfile):
            return risk.risk_level, float(risk.score), list(risk.risk_factors or [])
        if isinstance(risk, dict):
            return (
                risk.get("overall_level") or risk.get("risk_level"),
                risk.get("overall_score") or risk.get("score"),
                list(
                    risk.get("top_risk_factors")
                    or risk.get("risk_factors")
                    or []
                ),
            )
        return None, None, []


# Backward-compatible alias used by legacy intake pipeline
class DefaultKnowledgeGraphBuilder(KnowledgeGraphBuilder):
    """Legacy name — same builder."""

    def build(self, **kwargs: Any) -> PatientKnowledgeGraph:  # type: ignore[override]
        # Adapt old risk profile only API
        return super().build(**kwargs)


knowledge_graph_builder = KnowledgeGraphBuilder()
