"""
capital_guardian/services/evidence.py — Phase 2 Evidence Centre aggregation.
Reuses evidence_memory.EvidenceMemory and its existing source_reference
soft-pointer convention directly — no second evidence model. This service
only gathers, for one project, the union of EvidenceMemory rows attached to
every kind of object Capital Guardian tracks (capital movements, equipment,
milestones, governance, red flags, operational snapshots) and reports honest
verification-status counts. It never marks anything verified itself.
"""
from evidence_memory.models import EvidenceMemory


def source_reference_for(instance):
    """The same "app_label.ModelName:pk" string every model's own
    `evidence_documents` property already builds — centralised here so the
    Evidence Centre can build the same key for objects that don't have their
    own property (e.g. bulk-listing without loading each row)."""
    return f'{instance._meta.app_label}.{instance.__class__.__name__}:{instance.pk}'


def _refs_for_queryset(queryset, app_label, model_name):
    return [f'{app_label}.{model_name}:{pk}' for pk in queryset.values_list('pk', flat=True)]


def evidence_for_project(project):
    """Every real EvidenceMemory row attached to anything belonging to this
    project — a capital movement, a piece of equipment, a milestone, a red
    flag, its governance record, an operational snapshot, or (PR7) a verified
    capital outcome synced from this project's own capital allocation
    decisions."""
    refs = []
    refs.append(f'gold_intelligence.GoldProject:{project.pk}')
    refs += _refs_for_queryset(project.capital_trace_entries.all(), 'capital_guardian', 'CapitalTraceEntry')
    refs += _refs_for_queryset(project.equipment_specs.all(), 'gold_intelligence', 'EquipmentSpec')
    refs += _refs_for_queryset(project.timeline_milestones.all(), 'gold_intelligence', 'MineTimelineMilestone')
    refs += _refs_for_queryset(project.red_flags.all(), 'capital_guardian', 'RedFlag')
    refs += _refs_for_queryset(project.operational_snapshots.all(), 'capital_guardian', 'OperationalSnapshot')
    governance = getattr(project, 'governance', None)
    if governance is not None:
        refs.append(f'capital_guardian.ProjectGovernance:{governance.pk}')

    # Vertical-slice PR 7 — a decision has no FK to GoldProject (see PR5's
    # capital_guardian_handoff.py docstring), so this is the same honest
    # name-match already used by execution_monitoring.capital_decisions_for_
    # project(), not a new lookup mechanism.
    from waste_to_value_capital_allocation_engine.models import CapitalAllocationDecision
    outcome_ids = CapitalAllocationDecision.objects.filter(
        project=project.name, verified_outcome__isnull=False,
    ).values_list('verified_outcome__pk', flat=True)
    refs += [f'waste_to_value_capital_allocation_engine.VerifiedCapitalOutcome:{pk}' for pk in outcome_ids]

    return EvidenceMemory.objects.filter(source_reference__in=refs)


def verification_summary(evidence_qs):
    """Real counts by verification_status — an honest breakdown, never a
    single blended "verified" percentage that hides rejected/expired rows."""
    evidence_qs = list(evidence_qs)
    counts = {choice: 0 for choice, _ in EvidenceMemory.VERIFICATION_STATUS_CHOICES}
    for e in evidence_qs:
        counts[e.verification_status] = counts.get(e.verification_status, 0) + 1
    return {'total': len(evidence_qs), 'by_status': counts}


RELATED_LABEL_PREFIXES = {
    'capital_guardian.CapitalTraceEntry': 'Capital Trace Entry',
    'gold_intelligence.EquipmentSpec': 'Equipment',
    'gold_intelligence.MineTimelineMilestone': 'Milestone',
    'capital_guardian.RedFlag': 'Red Flag',
    'capital_guardian.OperationalSnapshot': 'Operational Snapshot',
    'capital_guardian.ProjectGovernance': 'Governance',
    'gold_intelligence.GoldProject': 'Project',
    'waste_to_value_capital_allocation_engine.VerifiedCapitalOutcome': 'Verified Capital Outcome',
}


def related_object_label(source_reference):
    """A human label for an evidence row's source_reference, without a hard
    FK lookup — honest ("Capital Trace Entry #42") rather than silently
    resolving to a stale/deleted row's __str__."""
    if not source_reference or ':' not in source_reference:
        return 'Not linked'
    key, _, pk = source_reference.rpartition(':')
    return f'{RELATED_LABEL_PREFIXES.get(key, key)} #{pk}'
