"""
ai_observatory/services/proxies.py — Relative Compute / Cost / Carbon
proxies. NOT energy meters and NOT carbon accounting.

METHODOLOGY (rendered verbatim on the Methodology page):

EcoIQ does not measure electricity or emissions — no defensible per-request
measurement methodology exists for a mixed local/provider-hosted workload,
and pretending otherwise would be fabrication. Instead the observatory
computes three RELATIVE indices over the real recorded work units:

    weighted_units = Σ (count(unit_type) × weight(unit_type))

Unit types and default weights (every weight is configurable via
settings.AI_OBSERVATORY_PROXY_WEIGHTS — the dashboard always shows the
weights actually used):

    llm_call_fresh    25.0   one un-cached model generation
    llm_call_cached    5.0   a generation the provider served ≥50% from
                             prompt cache (cheaper, not free)
    llm_1k_tokens      1.0   per 1,000 real reported tokens (in + out),
                             added on top of the per-call weight
    retrieval_stage    2.0   one vector-retrieval operation over stored
                             evidence (cheaper than generation)
    deterministic_stage 1.0  one deterministic engine execution (the
                             baseline unit)
    governance_stage   1.0   one safety/governance check

Rationale for the ordering (generation ≫ retrieval > deterministic): a
single LLM generation performs orders of magnitude more floating-point work
than an in-process deterministic scoring pass over tens of rows, and a
cached generation avoids most prefill compute. The exact numbers are
deliberately coarse, visibly configurable, and only meaningful for
COMPARING two workloads under the SAME weights — never as absolute units.

- Relative Compute Index = weighted_units (dimensionless).
- Relative Cost Index    = weighted_units under COST_WEIGHTS (defaults
                           identical to compute weights except retrieval/
                           deterministic are near-zero, mirroring that
                           self-hosted deterministic work has no per-call
                           provider fee).
- Relative Carbon Proxy  = the compute index unchanged. Carbon scales with
                           compute for a fixed grid/provider mix; since the
                           mix is unknown, no gCO2e conversion is applied
                           or implied.

WHAT THIS DOES NOT CLAIM: kWh, gCO2e, monetary cost, or comparability
between two systems measured with different weights.
"""
from django.conf import settings

DEFAULT_COMPUTE_WEIGHTS = {
    'llm_call_fresh': 25.0,
    'llm_call_cached': 5.0,
    'llm_1k_tokens': 1.0,
    'retrieval_stage': 2.0,
    'deterministic_stage': 1.0,
    'governance_stage': 1.0,
}

DEFAULT_COST_WEIGHTS = {
    'llm_call_fresh': 25.0,
    'llm_call_cached': 5.0,
    'llm_1k_tokens': 1.0,
    'retrieval_stage': 0.1,
    'deterministic_stage': 0.05,
    'governance_stage': 0.05,
}


def compute_weights():
    return {**DEFAULT_COMPUTE_WEIGHTS, **getattr(settings, 'AI_OBSERVATORY_PROXY_WEIGHTS', {})}


def cost_weights():
    return {**DEFAULT_COST_WEIGHTS, **getattr(settings, 'AI_OBSERVATORY_COST_WEIGHTS', {})}


def workload_counts(sessions):
    """Real work-unit counts across an iterable/queryset of sessions.
    Token totals only include values providers actually reported."""
    from ai_observatory.models import ModelInvocation, PipelineStageExecution

    session_ids = [s.pk for s in sessions]
    stages = PipelineStageExecution.objects.filter(session_id__in=session_ids)
    invocations = ModelInvocation.objects.filter(session_id__in=session_ids)

    fresh_calls = 0
    cached_calls = 0
    reported_tokens = 0
    unreported_calls = 0
    for inv in invocations:
        total = (inv.input_tokens or 0) + (inv.output_tokens or 0)
        if inv.input_tokens is None and inv.output_tokens is None:
            unreported_calls += 1
        reported_tokens += total
        cached = inv.cached_tokens or 0
        if inv.input_tokens and cached >= inv.input_tokens * 0.5:
            cached_calls += 1
        else:
            fresh_calls += 1

    return {
        'llm_call_fresh': fresh_calls,
        'llm_call_cached': cached_calls,
        'llm_reported_tokens': reported_tokens,
        'llm_unreported_calls': unreported_calls,
        'retrieval_stage': stages.filter(category='retrieval').count(),
        'deterministic_stage': stages.filter(category='deterministic').count(),
        'governance_stage': stages.filter(category='governance').count(),
        'llm_stage': stages.filter(category='llm').count(),
    }


def weighted_index(counts, weights):
    return round(
        counts['llm_call_fresh'] * weights['llm_call_fresh']
        + counts['llm_call_cached'] * weights['llm_call_cached']
        + (counts['llm_reported_tokens'] / 1000.0) * weights['llm_1k_tokens']
        + counts['retrieval_stage'] * weights['retrieval_stage']
        + counts['deterministic_stage'] * weights['deterministic_stage']
        + counts['governance_stage'] * weights['governance_stage'],
        2,
    )


def proxy_indices(sessions):
    """The three relative indices plus the counts and weights they came
    from — the dashboard shows all of it, never a bare number."""
    counts = workload_counts(sessions)
    cw, kw = compute_weights(), cost_weights()
    compute_index = weighted_index(counts, cw)
    return {
        'counts': counts,
        'compute_weights': cw,
        'cost_weights': kw,
        'relative_compute_index': compute_index,
        'relative_cost_index': weighted_index(counts, kw),
        # Proportional to compute by construction — see module docstring.
        'relative_carbon_proxy': compute_index,
    }
