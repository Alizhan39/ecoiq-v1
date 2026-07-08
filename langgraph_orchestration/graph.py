"""
langgraph_orchestration/graph.py — builds and runs the Phase 1 orchestrator.

    classify_intent
          |
    (unknown target -> END, marked failed honestly, not faked as success)
          |
    retrieve_evidence_memory -> gather_geo_intelligence
          |
    (location-only target -> END after verify_output; a location has no
     company/country to run agent analysis, scoring or analytics against)
          |
    run_agent_analysis
          |
    (company -> recalculate_score_if_needed; country -> skip straight to
     analytics, since Pandas Scoring Engine only scores companies)
          |
    run_intelligence_analytics -> verify_output -> finalize -> END

Every node is wrapped by _safe_node so a raised exception inside any one
node never silently produces a fake "completed" result — it's recorded as
state['status'] = 'failed' + state['failed_node'] = <node name>, and every
conditional router checks that flag first and short-circuits to END.
"""
from langgraph.graph import END, StateGraph

from langgraph_orchestration import nodes
from langgraph_orchestration.state import OrchestratorState, new_state


def _safe_node(name):
    """
    Looks up nodes.<name> dynamically at call time (getattr), not once at
    graph-build time — the compiled graph is cached at module level
    (_get_compiled_graph), so capturing a function object directly at build
    time would keep calling the ORIGINAL function forever, even in tests
    that mock.patch langgraph_orchestration.nodes.<name> after the first
    build. A plain getattr each call costs nothing and keeps every node
    genuinely swappable.
    """
    def wrapped(state):
        try:
            fn = getattr(nodes, name)
            return fn(state)
        except Exception as exc:
            state['status'] = 'failed'
            state['failed_node'] = name
            state.setdefault('verification_notes', []).append(f'Node "{name}" raised an error: {exc}')
            return state
    wrapped.__name__ = f'safe_{name}'
    return wrapped


def _after(next_node_name):
    """Every conditional edge checks failure first, so one bad node can
    never let the graph silently continue as if nothing went wrong."""
    def route(state):
        if state.get('status') == 'failed':
            return END
        return next_node_name
    return route


def _route_after_classify(state):
    """Read-only routing decision only — see handle_unresolved_target's
    docstring for why the actual state mutation happens in a real node."""
    if state.get('status') == 'failed':
        return END
    if state.get('target_type') == 'unknown':
        return 'handle_unresolved_target'
    return 'retrieve_evidence_memory'


def _route_after_geo(state):
    if state.get('status') == 'failed':
        return END
    if state.get('target_type') == 'location':
        return 'verify_output'  # no company/country -> nothing for agent/scoring/analytics to run against
    return 'run_agent_analysis'


def _route_after_agent(state):
    if state.get('status') == 'failed':
        return END
    if state.get('target_type') == 'company':
        return 'recalculate_score_if_needed'
    return 'run_intelligence_analytics'  # country: no company scoring to run


def build_graph():
    graph = StateGraph(OrchestratorState)

    for node_name in (
        'classify_intent', 'handle_unresolved_target', 'retrieve_evidence_memory', 'gather_geo_intelligence',
        'run_agent_analysis', 'recalculate_score_if_needed', 'run_intelligence_analytics', 'verify_output', 'finalize',
    ):
        graph.add_node(node_name, _safe_node(node_name))

    graph.set_entry_point('classify_intent')
    graph.add_conditional_edges('classify_intent', _route_after_classify)
    graph.add_conditional_edges('retrieve_evidence_memory', _after('gather_geo_intelligence'))
    graph.add_conditional_edges('gather_geo_intelligence', _route_after_geo)
    graph.add_conditional_edges('run_agent_analysis', _route_after_agent)
    graph.add_conditional_edges('recalculate_score_if_needed', _after('run_intelligence_analytics'))
    graph.add_conditional_edges('run_intelligence_analytics', _after('verify_output'))
    graph.add_conditional_edges('verify_output', _after('finalize'))
    graph.add_edge('finalize', END)
    graph.add_edge('handle_unresolved_target', END)

    return graph.compile()


_compiled_graph = None


def _get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_orchestration(user_request='', target_id=None, target_type=None, latitude=None, longitude=None,
                       execution_mode='deterministic_test'):
    """
    The one entrypoint every caller (Celery task, tests, a future view)
    should use. target_type must be 'company' or 'country' when target_id
    is given (resolution happens in classify_intent) — a location is passed
    via latitude/longitude instead.
    """
    initial_state = new_state(
        user_request=user_request, target_id=target_id, target_type_hint=target_type,
        latitude=latitude, longitude=longitude, execution_mode=execution_mode,
    )
    compiled = _get_compiled_graph()
    final_state = compiled.invoke(initial_state)
    return final_state
