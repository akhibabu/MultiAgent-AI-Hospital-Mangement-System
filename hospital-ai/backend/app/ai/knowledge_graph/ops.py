"""Graph validation, serialization, and update helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from app.ai.knowledge_graph.models import (
    GraphEdge,
    GraphNode,
    GraphStatistics,
    PatientKnowledgeGraph,
)


class GraphValidator:
    """Validate graph integrity before persistence."""

    def validate(self, graph: PatientKnowledgeGraph) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []
        node_ids: Set[str] = {n.id for n in graph.nodes}

        if not any(n.type == "Patient" for n in graph.nodes):
            errors.append("Graph must contain a Patient node")

        for edge in graph.edges:
            if edge.source not in node_ids:
                errors.append(f"Edge {edge.id} source missing: {edge.source}")
            if edge.target not in node_ids:
                errors.append(f"Edge {edge.id} target missing: {edge.target}")
            if edge.source == edge.target:
                warnings.append(f"Self-loop edge {edge.id}")

        if len(graph.nodes) < 2:
            warnings.append("Graph has fewer than 2 nodes")
        if not graph.edges:
            warnings.append("Graph has no relationships")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
        }


class GraphSerializer:
    """Serialize / deserialize portable graph JSON (Neo4j-ready shape)."""

    def to_storage(self, graph: PatientKnowledgeGraph) -> Dict[str, Any]:
        return {
            "patient_id": graph.patient_id,
            "nodes": [n.model_dump(mode="json") for n in graph.nodes],
            "relationships": [e.model_dump(mode="json") for e in graph.edges],
            "edges": [e.model_dump(mode="json") for e in graph.edges],
            "summary": graph.summary,
            "statistics": graph.statistics.to_dict() if graph.statistics else {},
            "patient_summary": (
                graph.patient_summary.to_dict() if graph.patient_summary else {}
            ),
            "graph_version": graph.graph_version,
            "builder_logs": graph.builder_logs[-80:],
            "validation": graph.validation,
            "format": "hospital_ai_kg_v1",
            "neo4j_ready": True,
        }

    def from_storage(self, data: Dict[str, Any]) -> PatientKnowledgeGraph:
        nodes = [GraphNode.model_validate(n) for n in (data.get("nodes") or [])]
        raw_edges = data.get("relationships") or data.get("edges") or []
        edges = [GraphEdge.model_validate(e) for e in raw_edges]
        stats = data.get("statistics") or {}
        return PatientKnowledgeGraph(
            patient_id=str(data.get("patient_id") or ""),
            nodes=nodes,
            edges=edges,
            relationships=edges,
            summary=data.get("summary"),
            statistics=GraphStatistics.model_validate(stats) if stats else None,
            graph_version=int(data.get("graph_version") or 1),
            builder_logs=list(data.get("builder_logs") or []),
            validation=dict(data.get("validation") or {}),
        )


class GraphUpdater:
    """Merge incremental facts into an existing graph (future Neo4j upsert path)."""

    def __init__(self) -> None:
        from app.ai.knowledge_graph.builders import NodeBuilder, RelationshipBuilder

        self._nodes = NodeBuilder
        self._rels = RelationshipBuilder

    def merge(
        self,
        existing: PatientKnowledgeGraph,
        incoming: PatientKnowledgeGraph,
    ) -> PatientKnowledgeGraph:
        by_key: Dict[tuple, GraphNode] = {}
        for n in existing.nodes + incoming.nodes:
            key = (n.type.lower(), n.label.lower())
            by_key[key] = n
        nodes = list(by_key.values())
        id_map = {(n.type.lower(), n.label.lower()): n.id for n in nodes}

        # Remap incoming edges to merged node ids when labels match
        edge_keys = set()
        edges: List[GraphEdge] = []
        node_by_id = {n.id: n for n in existing.nodes + incoming.nodes}

        for e in existing.edges + incoming.edges:
            src = node_by_id.get(e.source)
            tgt = node_by_id.get(e.target)
            if not src or not tgt:
                continue
            src_id = id_map.get((src.type.lower(), src.label.lower()), e.source)
            tgt_id = id_map.get((tgt.type.lower(), tgt.label.lower()), e.target)
            key = (e.type, src_id, tgt_id)
            if key in edge_keys:
                continue
            edge_keys.add(key)
            edges.append(
                GraphEdge(
                    id=e.id,
                    type=e.type,
                    source=src_id,
                    target=tgt_id,
                    properties=e.properties,
                )
            )

        return PatientKnowledgeGraph(
            patient_id=incoming.patient_id or existing.patient_id,
            nodes=nodes,
            edges=edges,
            relationships=edges,
            summary=incoming.summary or existing.summary,
            statistics=incoming.statistics or existing.statistics,
            patient_summary=incoming.patient_summary or existing.patient_summary,
            graph_version=max(existing.graph_version, incoming.graph_version) + 1,
            builder_logs=(existing.builder_logs + incoming.builder_logs)[-100:],
            validation=incoming.validation or existing.validation,
        )


def compute_statistics(nodes: List[GraphNode], edges: List[GraphEdge]) -> GraphStatistics:
    def count(type_name: str) -> int:
        return sum(1 for n in nodes if n.type == type_name)

    return GraphStatistics(
        total_nodes=len(nodes),
        total_relationships=len(edges),
        diseases=count("Disease"),
        symptoms=count("Symptom"),
        medications=count("Medication"),
        doctors=count("Doctor"),
        reports=count("MedicalReport") + count("MedicalRecord"),
        hospitals=count("Hospital"),
        appointments=count("Appointment"),
        procedures=count("Procedure"),
        allergies=count("Allergy"),
        vitals=count("VitalSign"),
        lab_tests=count("LabTest") + count("LabReport"),
        risk_factors=count("RiskFactor"),
    )
