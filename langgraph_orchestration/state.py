"""
langgraph_orchestration/state.py — the shared state every node in the graph
reads from and writes back to. A plain TypedDict, matching LangGraph's own
state-schema convention — no new persistence layer, this is the in-memory
shape passed between nodes for the lifetime of one graph run. The final
state is what OrchestrationRun.result (see models.py) stores.
"""
from typing import Any, Optional, TypedDict


class OrchestratorState(TypedDict, total=False):
    # Input
    user_request: str
    target_type: str            # 'company' | 'country' | 'location' | 'unknown'
    target_id: Optional[int]    # CompanyProfile.pk or CountryProfile.pk, when resolved
    company: Optional[dict]     # {id, name, country} once resolved
    country: Optional[dict]     # {id, name} once resolved
    location: Optional[dict]    # {latitude, longitude} when given directly
    execution_mode: str         # passed through to run_agent_analysis — never defaults to 'live'

    # Node outputs
    evidence_context: dict
    geo_context: dict
    scoring_context: dict
    analytics_context: dict
    agent_outputs: list

    # Verification
    verification_notes: list
    confidence: Optional[float]
    human_review_required: bool

    # Output
    final_recommendations: list
    next_actions: list
    status: str                 # 'running' | 'completed' | 'needs_human_review' | 'failed'

    # Observability — surfaced in Django Admin (OrchestrationRun)
    nodes_executed: list
    failed_node: Optional[str]


def new_state(user_request='', target_id=None, target_type_hint=None, latitude=None, longitude=None,
              execution_mode='deterministic_test') -> OrchestratorState:
    """The one place an initial state is constructed, so every entrypoint
    (Celery task, tests, a future view) starts from an identical shape."""
    location = {'latitude': latitude, 'longitude': longitude} if latitude is not None and longitude is not None else None
    return OrchestratorState(
        user_request=user_request or '',
        target_type=target_type_hint or '',
        target_id=target_id,
        company=None, country=None, location=location,
        execution_mode=execution_mode,
        evidence_context={}, geo_context={}, scoring_context={}, analytics_context={},
        agent_outputs=[],
        verification_notes=[], confidence=None, human_review_required=False,
        final_recommendations=[], next_actions=[], status='running',
        nodes_executed=[], failed_node=None,
    )


def record_node(state: OrchestratorState, node_name: str) -> None:
    """Every node calls this first — guarantees nodes_executed is always
    accurate even if the node raises partway through."""
    state.setdefault('nodes_executed', []).append(node_name)
