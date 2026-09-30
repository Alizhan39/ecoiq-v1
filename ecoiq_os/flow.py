"""Universal Flow Graph for EcoIQ OS.

One graph shape represents physical and economic flows across mining, energy,
water, processing, manufacturing, cities, government and households.

The graph stores observations. It does not infer missing quantities, convert
units silently or decide that a loss is unjustified.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


RESOURCE_TYPES = (
    "material",
    "mineral",
    "energy",
    "water",
    "money",
    "labour",
    "land",
    "time",
    "data",
    "emissions",
    "waste",
    "service",
)

NODE_TYPES = (
    "source",
    "process",
    "storage",
    "organisation",
    "household",
    "market",
    "public_system",
    "sink",
)


@dataclass(frozen=True)
class FlowNode:
    id: str
    name: str
    node_type: str
    scope: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Flow node id is required.")
        if self.node_type not in NODE_TYPES:
            raise ValueError(f"Unknown flow node type: {self.node_type}")


@dataclass(frozen=True)
class FlowEdge:
    id: str
    source: str
    target: str
    resource_type: str
    value: float | None = None
    unit: str | None = None
    period: str | None = None
    purpose: str | None = None
    evidence_refs: tuple[str, ...] = ()
    is_loss: bool = False

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Flow edge id is required.")
        if self.source == self.target:
            raise ValueError("A flow edge must connect two different nodes.")
        if self.resource_type not in RESOURCE_TYPES:
            raise ValueError(f"Unknown resource type: {self.resource_type}")
        if self.value is not None and not self.unit:
            raise ValueError("A known flow value must declare its unit.")
        if self.value is not None and self.value < 0:
            raise ValueError("Flow values must be non-negative; direction carries the sign.")


@dataclass(frozen=True)
class FlowValidationIssue:
    code: str
    message: str
    edge_id: str | None = None


@dataclass(frozen=True)
class UniversalFlowGraph:
    nodes: tuple[FlowNode, ...]
    edges: tuple[FlowEdge, ...]
    graph_version: str = "1"

    def validation_issues(self) -> tuple[FlowValidationIssue, ...]:
        issues: list[FlowValidationIssue] = []
        node_ids = [node.id for node in self.nodes]
        edge_ids = [edge.id for edge in self.edges]

        duplicate_nodes = sorted({item for item in node_ids if node_ids.count(item) > 1})
        duplicate_edges = sorted({item for item in edge_ids if edge_ids.count(item) > 1})

        for node_id in duplicate_nodes:
            issues.append(FlowValidationIssue("DUPLICATE_NODE", f"Duplicate node id: {node_id}"))
        for edge_id in duplicate_edges:
            issues.append(FlowValidationIssue("DUPLICATE_EDGE", f"Duplicate edge id: {edge_id}", edge_id))

        known_nodes = set(node_ids)
        for edge in self.edges:
            if edge.source not in known_nodes:
                issues.append(
                    FlowValidationIssue(
                        "UNKNOWN_SOURCE",
                        f"Edge {edge.id} references unknown source node {edge.source}.",
                        edge.id,
                    )
                )
            if edge.target not in known_nodes:
                issues.append(
                    FlowValidationIssue(
                        "UNKNOWN_TARGET",
                        f"Edge {edge.id} references unknown target node {edge.target}.",
                        edge.id,
                    )
                )
        return tuple(issues)

    @property
    def is_valid(self) -> bool:
        return not self.validation_issues()

    def known_edges(self, resource_type: str | None = None) -> tuple[FlowEdge, ...]:
        if resource_type is not None and resource_type not in RESOURCE_TYPES:
            raise ValueError(f"Unknown resource type: {resource_type}")
        return tuple(
            edge
            for edge in self.edges
            if edge.value is not None
            and (resource_type is None or edge.resource_type == resource_type)
        )

    def losses(self) -> tuple[FlowEdge, ...]:
        return tuple(edge for edge in self.edges if edge.is_loss)

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_version": self.graph_version,
            "nodes": [asdict(node) for node in self.nodes],
            "edges": [asdict(edge) for edge in self.edges],
            "validation_issues": [asdict(issue) for issue in self.validation_issues()],
        }


def build_graph(nodes: Iterable[FlowNode], edges: Iterable[FlowEdge]) -> UniversalFlowGraph:
    return UniversalFlowGraph(tuple(nodes), tuple(edges))
