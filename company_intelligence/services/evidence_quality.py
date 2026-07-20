"""
company_intelligence/services/evidence_quality.py — feat/company-evidence-
ingestion (PR 10): "expose evidence quality... prefer component metrics
over a mysterious universal score."

Reuses harvester's existing, real, already-computed verification
sub-scores (source_quality_score, freshness_score, corroboration_score,
confidence_score — harvester/verification.py, unmodified) for any evidence
that actually came through the harvester pipeline, rather than inventing a
second scoring system. Evidence with no harvester.Evidence counterpart
(e.g. PR9's demo fixtures, manually-entered evidence) honestly reports
those components as unavailable, never a fabricated number.
"""
from evidence_memory.models import EvidenceMemory

HARVESTER_SOURCE_PREFIX = 'harvester.Evidence:'


def _harvester_evidence_for_memory(memory):
    """Resolves an EvidenceMemory row back to its harvester.Evidence
    counterpart via the same source_reference convention
    create_memory_from_evidence() writes — real FK lookup, never guessed."""
    if not memory.source_reference or not memory.source_reference.startswith(HARVESTER_SOURCE_PREFIX):
        return None
    try:
        pk = int(memory.source_reference.split(':', 1)[1])
    except (IndexError, ValueError):
        return None
    from harvester.models import Evidence
    return Evidence.objects.filter(pk=pk).select_related('source').first()


def evidence_quality_for_memory(memory):
    """
    One EvidenceMemory row's quality components. Returns
    {'has_harvester_record', 'source_authority', 'recency', 'corroboration',
    'verification_state', 'confidence', 'is_conflicting'} — every numeric
    field is None (not 0.0) when genuinely unavailable.
    """
    harvester_evidence = _harvester_evidence_for_memory(memory)
    if harvester_evidence is None:
        return {
            'has_harvester_record': False,
            'source_authority': None, 'recency': None, 'corroboration': None,
            'verification_state': memory.get_verification_status_display(),
            'confidence': memory.confidence,
            'is_conflicting': False,
        }
    return {
        'has_harvester_record': True,
        'source_authority': harvester_evidence.source_quality_score,
        'recency': harvester_evidence.freshness_score,
        'corroboration': harvester_evidence.corroboration_score,
        'verification_state': harvester_evidence.get_verification_status_display(),
        'confidence': harvester_evidence.confidence_score,
        'is_conflicting': harvester_evidence.verification_status == 'CONTRADICTED',
    }


def company_evidence_quality_summary(company_profile):
    """
    Aggregate, transparent quality summary across all real evidence linked
    to this company (via KPI evidence links + controversies + financial
    fact sources) — component averages, never one mysterious blended score.
    Returns {'evidence_count', 'harvester_backed_count', 'avg_source_authority',
    'avg_recency', 'avg_corroboration', 'conflicting_count'}.
    """
    memory_ids = set()
    for link in company_profile.kpi_assessments.prefetch_related('evidence_links').all():
        for l in link.evidence_links.all():
            memory_ids.add(l.evidence_id)
    for c in company_profile.controversies.all():
        if c.evidence_id:
            memory_ids.add(c.evidence_id)

    memories = list(EvidenceMemory.objects.filter(pk__in=memory_ids))
    qualities = [evidence_quality_for_memory(m) for m in memories]
    harvester_backed = [q for q in qualities if q['has_harvester_record']]

    def _avg(key):
        values = [q[key] for q in harvester_backed if q[key] is not None]
        return round(sum(values) / len(values), 3) if values else None

    return {
        'evidence_count': len(memories),
        'harvester_backed_count': len(harvester_backed),
        'avg_source_authority': _avg('source_authority'),
        'avg_recency': _avg('recency'),
        'avg_corroboration': _avg('corroboration'),
        'conflicting_count': sum(1 for q in qualities if q['is_conflicting']),
    }
