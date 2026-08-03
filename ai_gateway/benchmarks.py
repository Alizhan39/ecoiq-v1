"""
ai_gateway/benchmarks.py — benchmark cases for candidate models.

These are **definitions, not executions**. Nothing here calls a provider, and
no test in this project runs them: a live benchmark is a real (if free) load on
an upstream service and belongs in a deliberate, human-run session, not in CI.

`settings.AI_BENCHMARK_CANDIDATES` lists models that are verified free and
available but deliberately **not** allowlisted — they stay outside public
routing until someone reviews benchmark results and adds them to
`AI_MODEL_ALLOWLIST` by hand. Nothing in this module approves anything.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BenchmarkCase:
    key: str
    title: str
    #: What the case is actually testing — the property a reviewer must judge.
    measures: str
    language: str = 'en'
    #: Capabilities a candidate must declare to be eligible for this case.
    requires: frozenset[str] = frozenset({'chat'})
    #: What a reviewer should check in the output. Deliberately qualitative:
    #: EcoIQ has no automated grader, and pretending otherwise would make the
    #: results look more objective than they are.
    review_criteria: tuple[str, ...] = ()
    notes: str = ''


BENCHMARK_CASES: tuple[BenchmarkCase, ...] = (
    BenchmarkCase(
        key='company_analysis_en',
        title='English company analysis',
        measures='Analytical quality and fact/assumption separation in English.',
        language='en',
        review_criteria=(
            'Facts, assumptions, estimates and recommendations are labelled separately.',
            'No invented metrics, regulations or figures.',
            'Missing data is stated plainly rather than filled in.',
        ),
    ),
    BenchmarkCase(
        key='company_analysis_ar',
        title='Arabic company analysis',
        measures='Same analysis quality in Arabic, with correct script handling.',
        language='ar',
        review_criteria=(
            'Answers in Arabic, not transliterated Latin script.',
            'Diacritics and RTL text preserved intact.',
            'Same fact/assumption labelling as the English case.',
        ),
    ),
    BenchmarkCase(
        key='company_analysis_ru',
        title='Russian company analysis',
        measures='Same analysis quality in Russian.',
        language='ru',
        review_criteria=(
            'Answers in Russian throughout, no language drift mid-answer.',
            'Same fact/assumption labelling as the English case.',
        ),
    ),
    BenchmarkCase(
        key='khalifah_explanation',
        title='Khalifah explanation',
        measures='Islamic stewardship framing treated as decision support, never as a ruling.',
        review_criteria=(
            'Explicitly not presented as a fatwa or religious ruling.',
            'No fabricated Qur\'anic or hadith references.',
            'Defers to a qualified scholar where a ruling would be required.',
        ),
    ),
    BenchmarkCase(
        key='structured_json_validity',
        title='Structured JSON validity',
        measures='Whether the model returns parseable JSON matching a requested shape.',
        requires=frozenset({'chat', 'tools'}),
        review_criteria=(
            'Output parses as JSON on the first attempt.',
            'All requested keys present; no extra prose around the object.',
            'Types match the requested schema.',
        ),
    ),
    BenchmarkCase(
        key='citation_grounding',
        title='Citation grounding',
        measures='Whether claims are attributed only to supplied context.',
        review_criteria=(
            'Every citation traces to text actually provided in the prompt.',
            'No invented sources, URLs, standards or document titles.',
            'Says so when the supplied context does not support a claim.',
        ),
    ),
    BenchmarkCase(
        key='incomplete_data_handling',
        title='Incomplete-data handling',
        measures='Behaviour when the context is deliberately missing key figures.',
        review_criteria=(
            'States what is missing instead of estimating silently.',
            'Any estimate is labelled as an estimate with its basis.',
            'Does not fabricate a plausible-looking number.',
        ),
    ),
    BenchmarkCase(
        key='document_and_chart_analysis',
        title='Document and chart analysis',
        measures='Reading figures and structure out of an image or chart.',
        requires=frozenset({'chat', 'vision'}),
        review_criteria=(
            'Values read from the chart match the source.',
            'Declines to read values that are genuinely illegible.',
            'Does not hallucinate series, axes or labels that are not present.',
        ),
        notes='Vision-only. Text-only candidates are not eligible for this case.',
    ),
    BenchmarkCase(
        key='latency_and_rate_limits',
        title='Latency and rate-limit behaviour',
        measures='Wall-clock latency and how the free tier behaves under repeat load.',
        review_criteria=(
            'Median and p95 latency for a typical analysis prompt.',
            'Whether 429s appear, and how quickly the model recovers.',
            'Whether free-tier limits make the model unusable as a primary route.',
        ),
        notes='Run manually and deliberately — never in CI, and never as a load test.',
    ),
)

#: Cases keyed for lookup.
BENCHMARK_CASES_BY_KEY = {case.key: case for case in BENCHMARK_CASES}


def cases_for(capabilities: frozenset[str]) -> list[BenchmarkCase]:
    """Which cases a candidate with these capabilities can actually be run on."""
    return [c for c in BENCHMARK_CASES if c.requires <= capabilities]


def candidates() -> tuple[str, ...]:
    """
    Models awaiting benchmarking. These are NOT approved and NOT in the routing
    pool — reading this list grants nothing.
    """
    from django.conf import settings
    return tuple(getattr(settings, 'AI_BENCHMARK_CANDIDATES', ()))
