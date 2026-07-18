"""
ai_observatory/services/comparison.py — EcoIQ workflow vs. a generic
LLM workflow, as COMPARATIVE INDICATORS.

The EcoIQ side of the comparison is real recorded telemetry. The generic
side is an ESTIMATE — clearly labelled as such everywhere it appears —
constructed from documented, configurable assumptions applied to the same
real workload:

BASELINE ASSUMPTIONS (settings.AI_OBSERVATORY_BASELINE_ASSUMPTIONS
overrides; rendered verbatim on the Methodology page):

- generations_per_stage (default 1): a generic chat-based workflow answers
  each analytical question EcoIQ solves with a deterministic/retrieval/
  governance stage by prompting a model instead — one generation per
  recorded stage.
- context_chars_per_token (default 4): standard rough character-per-token
  heuristic used ONLY for the baseline estimate, never for EcoIQ's own
  recorded numbers.
- output_tokens_per_generation (default 800): assumed length of each
  generated analytical answer.
- context_reuse_factor (default 1.0): a generic workflow re-sends the
  project's evidence corpus as context with every generation (no vector
  retrieval); 1.0 = full corpus each time.
- The baseline has no deterministic engines, no retrieval index, no safety
  gate (0 blocked outputs) and no enforced human review step — that is what
  "generic" means here, and it is stated on the page.

The baseline's estimated input tokens per generation are derived from the
project's REAL evidence corpus size (total characters of its evidence
memory text divided by context_chars_per_token) — the corpus is real, only
the "would be re-sent every time" behaviour is assumed.

WHAT THIS DOES NOT CLAIM: that any specific product behaves exactly like
the baseline, or that the indices convert to kWh/gCO2e/currency. Both
columns are computed under the SAME proxy weights, so only their RATIO is
meaningful.
"""
from django.conf import settings

from ai_observatory.services import proxies

DEFAULT_BASELINE_ASSUMPTIONS = {
    'generations_per_stage': 1,
    'context_chars_per_token': 4,
    'output_tokens_per_generation': 800,
    'context_reuse_factor': 1.0,
}


def baseline_assumptions():
    return {**DEFAULT_BASELINE_ASSUMPTIONS, **getattr(settings, 'AI_OBSERVATORY_BASELINE_ASSUMPTIONS', {})}


def _project_corpus_chars(project):
    """Real total size of the project's evidence memory text — the corpus a
    generic workflow would have to stuff into context."""
    from evidence_memory.models import EvidenceMemory

    return sum(len(m.text_chunk) for m in EvidenceMemory.objects.filter(project=project).only('text_chunk'))


def compare(project, sessions):
    """Returns the comparison table for the given real sessions of one
    project. `ecoiq` numbers are recorded; `generic` numbers are estimates
    under baseline_assumptions() — the caller/template must keep the
    'estimated' labelling this dict provides."""
    assumptions = baseline_assumptions()
    ecoiq_counts = proxies.workload_counts(sessions)

    stage_total = (
        ecoiq_counts['retrieval_stage'] + ecoiq_counts['deterministic_stage'] + ecoiq_counts['governance_stage']
    )
    baseline_calls = stage_total * assumptions['generations_per_stage'] + ecoiq_counts['llm_call_fresh'] + ecoiq_counts['llm_call_cached']

    corpus_chars = _project_corpus_chars(project)
    context_tokens = int(corpus_chars / assumptions['context_chars_per_token'] * assumptions['context_reuse_factor'])
    baseline_tokens = baseline_calls * (context_tokens + assumptions['output_tokens_per_generation'])

    baseline_counts = {
        'llm_call_fresh': baseline_calls,
        'llm_call_cached': 0,
        'llm_reported_tokens': baseline_tokens,   # estimated, not reported — labelled below
        'llm_unreported_calls': 0,
        'retrieval_stage': 0,
        'deterministic_stage': 0,
        'governance_stage': 0,
        'llm_stage': 0,
    }

    compute_w, cost_w = proxies.compute_weights(), proxies.cost_weights()
    real_sessions = list(sessions)
    blocked = sum(s.blocked_recommendation_count for s in real_sessions)
    human_reviews = sum(1 for s in real_sessions if s.human_review_required)
    evidence_used = sum(s.evidence_retrieved_count or 0 for s in real_sessions)

    return {
        'assumptions': assumptions,
        'corpus_chars': corpus_chars,
        'ecoiq': {
            'label': 'EcoIQ workflow (recorded)',
            'estimated': False,
            'model_calls': ecoiq_counts['llm_call_fresh'] + ecoiq_counts['llm_call_cached'],
            'tokens': ecoiq_counts['llm_reported_tokens'],
            'tokens_unreported_calls': ecoiq_counts['llm_unreported_calls'],
            'retrieval_operations': ecoiq_counts['retrieval_stage'],
            'deterministic_steps': ecoiq_counts['deterministic_stage'] + ecoiq_counts['governance_stage'],
            'unsafe_outputs_blocked': blocked,
            'human_review_steps': human_reviews,
            'evidence_records_used': evidence_used,
            'compute_index': proxies.weighted_index(ecoiq_counts, compute_w),
            'cost_index': proxies.weighted_index(ecoiq_counts, cost_w),
            'carbon_proxy': proxies.weighted_index(ecoiq_counts, compute_w),
        },
        'generic': {
            'label': 'Generic LLM workflow (estimated baseline)',
            'estimated': True,
            'model_calls': baseline_calls,
            'tokens': baseline_tokens,
            'tokens_unreported_calls': 0,
            'retrieval_operations': 0,
            'deterministic_steps': 0,
            'unsafe_outputs_blocked': 0,
            'human_review_steps': 0,
            'evidence_records_used': 0,
            'compute_index': proxies.weighted_index(baseline_counts, compute_w),
            'cost_index': proxies.weighted_index(baseline_counts, cost_w),
            'carbon_proxy': proxies.weighted_index(baseline_counts, compute_w),
        },
    }
