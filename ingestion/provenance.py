"""
ingestion/provenance.py — trusted-ingestion provenance (D3C-4).

THE DECISION THIS MODULE ENCODES
--------------------------------
A real source does not make a 0–100 EcoIQ score `MEASURED`.

The pipeline reads filings, ESG reports and news, and an LLM turns them into
five 0–100 pillar signals, which are then fanned out across sixteen material
fields. The *source fact* may well be measured — "Scope 1 emissions were
1,250,000 t" is a measurement someone made. The number EcoIQ stores is not that
fact. It is an assessment derived from it.

So every material score written by ingestion is **INFERRED**.

`MEASURED` is reserved for a value taken directly from a source without
EcoIQ judgement in between. The pipeline writes no such field today: the
closest candidates, `annual_revenue` and `employees`, are not registered
metrics. If ingestion ever writes a registered metric straight from a filing,
that one field — and only that one — becomes `MEASURED`.

This matters because `MEASURED` is the strongest claim in the vocabulary and,
with `INFERRED`, one of the origins that can make a metric publicly
defensible. Labelling an LLM's reading of a PDF as `MEASURED` would put the
strongest available claim behind the weakest available evidence.

WHAT THE LINEAGE HONESTLY SAYS
------------------------------
Sixteen fields, five source signals. `waste_management_score`,
`water_impact_score` and `biodiversity_impact_score` all receive the *same*
number, from the same single pollution assessment. The provenance rows say so:
each carries the assessment it came from in `methodology`, so a reader can see
that three "independent" metrics are one signal wearing three hats.

That is not a defect this module introduces. It is a defect this module stops
concealing.
"""
from __future__ import annotations

import logging

from companies.evidence import PROVENANCE_INFERRED

log = logging.getLogger(__name__)

INGESTION_METHOD = 'ecoiq-ingestion-llm-assessment'
INGESTION_VERSION = '1'
INGESTION_WRITER = 'ingestion.pipeline.IngestionPipeline._step_save'

#: Which source signal each written material metric is derived from.
#:
#: The pipeline fans five LLM-assessed pillar signals across sixteen fields.
#: Recording the signal per field is what makes the duplication visible: three
#: environmental metrics that all read `pollution_footprint` are one assessment,
#: not three.
#:
#: Keys are registry metric keys. `pollution_level` is deliberately absent — it
#: is a categorical field, not a registered metric (see
#: docs/product/CALCULATION_CONTEXT_PROVENANCE.md).
SIGNAL_FOR_METRIC: dict[str, str] = {
    # Environmental — all three from one pollution assessment
    'waste_management_score':            'pollution_footprint',
    'water_impact_score':                'pollution_footprint',
    'biodiversity_impact_score':         'pollution_footprint',

    # Modernization — all four from one reduction-progress assessment
    'energy_transition_score':           'reduction_progress',
    'digitalization_score':              'reduction_progress',
    'infrastructure_upgrade_score':      'reduction_progress',
    'future_readiness_score':            'reduction_progress',

    # Public benefit — all four from one investment assessment
    'jobs_created_score':                'investment',
    'regional_development_score':        'investment',
    'infrastructure_contribution_score': 'investment',
    'national_value_score':              'investment',

    # Governance — all four from one transparency assessment
    'transparency_score_detail':         'transparency',
    'audit_quality_score':               'transparency',
    'procurement_transparency_score':    'transparency',
    'anti_corruption_score':             'transparency',

    # Ethical alignment — inverted community-impact assessment
    'controversy_risk_score':            'community_impact',
}


#: Document types in descending order of evidential strength. Used to choose
#: which source a provenance row cites when a run downloaded several.
_DOC_TYPE_RANK = ('audit_report', 'government_report', 'press_release', 'other')


def best_evidence_memory(evidence_rows):
    """
    The strongest EvidenceMemory among the sources this run persisted.

    NOTE ON LINKAGE. `EvidenceMemory.company` is a FK to CompanyProfile, and
    `create_memory_from_league_evidence` deliberately never sets it: a
    league.Company pk written into that column would silently point at a
    different table's row. Provenance there is carried by `source_reference`
    instead, so this looks memories up the same way rather than by company.

    Best available, not exact. All sixteen scores come from a whole corpus, not
    from one identified passage, so citing the strongest document records which
    source was in play; it does not claim to be a citation for any one metric.

    Returns None when nothing was downloaded, which is normal and must stay
    cheap to handle: a provenance row with no evidence link is still worth far
    more than no row.
    """
    if not evidence_rows:
        return None
    try:
        from evidence_memory.models import EvidenceMemory

        ranked = sorted(
            evidence_rows,
            key=lambda e: _DOC_TYPE_RANK.index(e.doc_type)
            if e.doc_type in _DOC_TYPE_RANK else len(_DOC_TYPE_RANK),
        )
        references = [f'league.Evidence:{e.pk}' for e in ranked]
        memories = {
            m.source_reference: m
            for m in EvidenceMemory.objects.filter(source_reference__in=references)
        }
        for reference in references:
            if reference in memories:
                return memories[reference]
    except Exception as exc:                      # pragma: no cover - defensive
        log.debug('Evidence memory lookup failed: %s', exc)
    return None


def record_ingestion_write(profile, written: dict, *, evidence=None) -> dict:
    """
    Record INFERRED provenance for the material metrics ingestion just wrote.

    MUST be called inside the caller's transaction, alongside the value write.
    A value saved without provenance is indistinguishable from a legacy value
    and would be relabelled LEGACY_UNKNOWN_PROVENANCE by the next backfill —
    laundering a known origin into an unknown one.

    `written` maps profile field names to the values just written. Only keys in
    SIGNAL_FOR_METRIC are recorded; anything else the pipeline wrote (text,
    URLs, revenue, pollution_level) is not a registered metric.

    review_status stays 'proposed'. Automatic ingestion may propose, never
    confirm — the repository already made that decision for KPI links, and
    provenance follows it. No reviewer, no verification and no confidence
    figure is invented: an unknown confidence is NULL, because a fabricated
    confidence is worse than an absent one.

    Returns a count of what was recorded, for the job log.
    """
    from companies import provenance as prov

    recorded, skipped = 0, 0
    for metric_key, signal in SIGNAL_FOR_METRIC.items():
        if metric_key not in written:
            continue
        if written[metric_key] is None:
            # Nothing was written, so there is nothing to attest to. Recording
            # an origin for an absent value asserts a number that was never
            # stored.
            skipped += 1
            continue

        prov.record(
            profile, metric_key, PROVENANCE_INFERRED,
            written_by=INGESTION_WRITER,
            methodology=f'{INGESTION_METHOD}:{signal}',
            calculation_version=INGESTION_VERSION,
            evidence=evidence,
        )
        recorded += 1

    return {'recorded': recorded, 'skipped': skipped,
            'evidence_linked': evidence is not None}


def fmt_score(value) -> str:
    """Progress-message rendering for a score that may not exist yet."""
    from core.unknown import format_known

    return format_known(value, spec='.1f', absent='not yet scored')
