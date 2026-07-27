"""NodeBuilder / RelationshipBuilder — modular KG construction helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.ai.knowledge_graph.models import EdgeType, GraphEdge, GraphNode, NodeType


class NodeBuilder:
    """Creates and deduplicates graph nodes."""

    def __init__(self) -> None:
        self.nodes: List[GraphNode] = []
        self._index: Dict[Tuple[str, str], str] = {}
        self.logs: List[str] = []

    def add(
        self,
        ntype: NodeType | str,
        label: str,
        *,
        node_id: Optional[str] = None,
        confidence: Optional[float] = None,
        source_report: Optional[str] = None,
        **props: Any,
    ) -> str:
        type_val = ntype.value if isinstance(ntype, NodeType) else str(ntype)
        clean_label = (label or "").strip()
        if not clean_label:
            return ""
        key = (type_val.lower(), clean_label.lower())
        if key in self._index:
            return self._index[key]

        properties = {k: v for k, v in props.items() if v is not None}
        if confidence is not None:
            properties["confidence"] = confidence
        if source_report:
            properties["source_report"] = source_report

        nid = node_id or f"{type_val}:{self._slug(clean_label)}:{uuid4().hex[:8]}"
        self.nodes.append(
            GraphNode(id=nid, type=type_val, label=clean_label, properties=properties)
        )
        self._index[key] = nid
        self.logs.append(f"Node {type_val}: {clean_label}")
        return nid

    def get(self, ntype: NodeType | str, label: str) -> Optional[str]:
        type_val = ntype.value if isinstance(ntype, NodeType) else str(ntype)
        return self._index.get((type_val.lower(), label.strip().lower()))

    @staticmethod
    def _slug(value: str) -> str:
        return (
            "".join(ch if ch.isalnum() else "_" for ch in value.lower())
            .strip("_")[:48]
            or "node"
        )


class RelationshipBuilder:
    """Creates relationships between existing nodes."""

    def __init__(self) -> None:
        self.edges: List[GraphEdge] = []
        self._seen: set[Tuple[str, str, str]] = set()
        self.logs: List[str] = []

    def add(
        self,
        etype: EdgeType | str,
        source: str,
        target: str,
        **props: Any,
    ) -> Optional[str]:
        if not source or not target or source == target:
            return None
        type_val = etype.value if isinstance(etype, EdgeType) else str(etype)
        key = (type_val, source, target)
        if key in self._seen:
            return None
        self._seen.add(key)
        eid = f"e:{uuid4().hex[:10]}"
        self.edges.append(
            GraphEdge(
                id=eid,
                type=type_val,
                source=source,
                target=target,
                properties={k: v for k, v in props.items() if v is not None},
            )
        )
        self.logs.append(f"Rel {type_val}: {source} → {target}")
        return eid
