"""
global_research/services/contradiction.py — deterministic contradiction
detection. See docs/research_evidence_methodology.md §4. Contradictions
are never averaged away — this module only ever records both sides.
"""
from itertools import combinations

from django.db import models

NUMERIC_TOLERANCE_PCT = 15.0
TIER_RANK = {'A': 4, 'B': 3, 'C': 2, 'D': 1}


def _numeric_conflict_pct(a, b):
    if a.numeric_value is None or b.numeric_value is None:
        return None
    base = max(abs(a.numeric_value), abs(b.numeric_value), 1e-9)
    delta_pct = abs(a.numeric_value - b.numeric_value) / base * 100
    return delta_pct if delta_pct > NUMERIC_TOLERANCE_PCT else None


def detect_contradictions(mission):
    """Compares every pair of claims sharing (subject, predicate) for this
    mission. Idempotent: get_or_create keyed on the ordered claim pair, and
    an already-`resolved_by_human` record is never overwritten."""
    from global_research.models import ContradictionRecord, ResearchClaim

    claims = list(ResearchClaim.objects.filter(mission=mission).select_related('source'))
    by_key = {}
    for claim in claims:
        by_key.setdefault((claim.subject, claim.predicate), []).append(claim)

    records = []
    for group in by_key.values():
        if len(group) < 2:
            continue
        for a, b in combinations(group, 2):
            contradiction_type, delta_pct, explanation = None, None, ''
            numeric_delta = _numeric_conflict_pct(a, b)
            if numeric_delta is not None:
                contradiction_type, delta_pct = 'value_mismatch', numeric_delta
                explanation = (
                    f'{a.subject} {a.predicate}: {a.object_value} (source: "{a.source.title}", '
                    f'vendor_provided={a.vendor_provided}) vs {b.object_value} (source: "{b.source.title}", '
                    f'vendor_provided={b.vendor_provided}) — {numeric_delta:.1f}% difference, exceeding the '
                    f'{NUMERIC_TOLERANCE_PCT:g}% tolerance.'
                )
            elif (
                a.numeric_value is None and b.numeric_value is None
                and a.object_value.strip().lower() != b.object_value.strip().lower()
            ):
                contradiction_type = 'vendor_vs_independent' if a.vendor_provided != b.vendor_provided else 'service_coverage_conflict'
                explanation = (
                    f'{a.subject} {a.predicate}: "{a.object_value}" (source: "{a.source.title}") '
                    f'vs "{b.object_value}" (source: "{b.source.title}").'
                )
            if contradiction_type is None:
                continue

            claim_a, claim_b = (a, b) if a.pk < b.pk else (b, a)
            record, created = ContradictionRecord.objects.get_or_create(
                mission=mission, claim_a=claim_a, claim_b=claim_b,
                defaults=dict(contradiction_type=contradiction_type, delta=delta_pct, explanation=explanation),
            )
            if not created and record.resolution_status == 'unresolved':
                record.delta = delta_pct
                record.explanation = explanation
                record.save(update_fields=['delta', 'explanation', 'updated_at'])
            attempt_auto_resolve(record)
            for c in (claim_a, claim_b):
                if c.contradiction_status != 'resolved':
                    ResearchClaim.objects.filter(pk=c.pk).update(contradiction_status=(
                        'resolved' if record.resolution_status != 'unresolved' else 'unresolved'
                    ))
            records.append(record)
    return records


def attempt_auto_resolve(record):
    """A contradiction is only ever `resolved_by_evidence` when a strictly
    higher-tier, non-vendor claim supersedes a lower-tier one under
    IDENTICAL stated conditions — everything else stays unresolved pending
    a human. Never touches an already-`resolved_by_human` record."""
    if record.resolution_status == 'resolved_by_human':
        return False
    a, b = record.claim_a, record.claim_b
    tier_a = TIER_RANK.get(a.source.evidence_tier, 0)
    tier_b = TIER_RANK.get(b.source.evidence_tier, 0)
    if tier_a == tier_b:
        return False
    higher, lower = (a, b) if tier_a > tier_b else (b, a)
    if higher.vendor_provided:
        return False
    if higher.conditions != lower.conditions:
        return False
    record.resolution_status = 'resolved_by_evidence'
    record.resolution_notes = (
        f'Higher-tier independent claim (tier {higher.source.evidence_tier}, source "{higher.source.title}") '
        f'supersedes lower-tier claim (tier {lower.source.evidence_tier}, source "{lower.source.title}") '
        'under identical stated conditions.'
    )
    record.save(update_fields=['resolution_status', 'resolution_notes', 'updated_at'])
    return True


def unresolved_contradiction_count(claim):
    from global_research.models import ContradictionRecord

    return ContradictionRecord.objects.filter(
        models.Q(claim_a=claim) | models.Q(claim_b=claim), resolution_status='unresolved',
    ).count()
