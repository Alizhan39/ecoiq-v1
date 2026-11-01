"""Read-only EcoIQ decision-flow contracts.

A React Flow-compatible graph is a *description*, not an executable workflow.
All real project access and evidence retrieval must continue through the
existing Django permission boundary and evidence_memory retrieval_policy.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Position(StrictContract):
    x: float = Field(ge=-10000, le=10000)
    y: float = Field(ge=-10000, le=10000)


NodeKind = Literal[
    "question", "access_check", "evidence_retrieval", "ai_gateway",
    "schema_validation", "human_review", "reviewed_result",
]

STEP_KINDS = (
    "question", "access_check", "evidence_retrieval", "ai_gateway",
    "schema_validation", "human_review", "reviewed_result",
)


class NodeData(StrictContract):
    kind: NodeKind
    label: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=300)


class FlowNode(StrictContract):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    type: Literal["default"] = "default"
    position: Position
    data: NodeData


class FlowEdge(StrictContract):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,79}$")
    source: str
    target: str
    type: Literal["smoothstep"] = "smoothstep"
    animated: Literal[False] = False


class DecisionFlowPreview(StrictContract):
    """Exactly one non-executable, review-gated graph for a staff-only preview."""

    mode: Literal["preview"] = "preview"
    execution_enabled: Literal[False] = False
    nodes: list[FlowNode] = Field(min_length=7, max_length=7)
    edges: list[FlowEdge] = Field(min_length=6, max_length=6)

    @model_validator(mode="after")
    def enforce_gated_path(self):
        ids = [node.id for node in self.nodes]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate workflow node ID")
        if [node.data.kind for node in self.nodes] != list(STEP_KINDS):
            raise ValueError("Workflow must follow the fixed review-gated step order")
        expected = list(zip(ids, ids[1:]))
        if [(edge.source, edge.target) for edge in self.edges] != expected:
            raise ValueError("Only the fixed linear review path is allowed")
        if len({edge.id for edge in self.edges}) != len(self.edges):
            raise ValueError("Duplicate workflow edge ID")
        return self


class DecisionDraft(StrictContract):
    """Untrusted AI output; validation does not verify citations or approve a claim."""

    summary: str = Field(min_length=1, max_length=2000)
    uncertainties: list[str] = Field(default_factory=list, max_length=10)
    proposed_next_steps: list[str] = Field(default_factory=list, max_length=10)
    requires_human_review: Literal[True] = True
    publication_state: Literal["unverified_draft"] = "unverified_draft"


def validate_decision_draft(raw: str) -> DecisionDraft:
    """Fail closed on malformed, excessively long or self-approved AI output.

    The caller must still check project access, evidence provenance and approval
    against the database. This function NEVER publishes or executes a decision.
    """
    if not isinstance(raw, str) or len(raw) > 16000:
        raise ValueError("Invalid AI decision draft")
    try:
        return DecisionDraft.model_validate_json(raw)
    except ValidationError as exc:
        raise ValueError("Invalid AI decision draft") from exc


def preview_decision_flow() -> dict:
    """React Flow-compatible nodes/edges; no provider call, retrieval or writes."""
    specs = [
        ("question", "Decision question", "User supplies a scoped decision question."),
        ("access_check", "Permission check", "Django checks project membership before retrieving evidence."),
        ("evidence_retrieval", "Evidence search", "Existing permission-filtered Evidence Memory / pgvector retrieval."),
        ("ai_gateway", "AI draft", "Existing free-only AI Gateway prepares an unverified draft."),
        ("schema_validation", "Pydantic validation", "Reject malformed or self-approved model outputs."),
        ("human_review", "Human review", "Reviewer verifies the source-to-claim mapping and authorises next steps."),
        ("reviewed_result", "Reviewed result", "Only an explicit human-approved decision may be acted upon."),
    ]
    nodes = [
        {"id": kind, "position": {"x": float(i * 260), "y": 0.0},
         "data": {"kind": kind, "label": label, "description": description}}
        for i, (kind, label, description) in enumerate(specs)
    ]
    edges = [
        {"id": f"edge_{i}", "source": specs[i][0], "target": specs[i + 1][0]}
        for i in range(len(specs) - 1)
    ]
    graph = DecisionFlowPreview.model_validate({"nodes": nodes, "edges": edges})
    return graph.model_dump()
