"""
good_agents/services/mission_control.py — PR6: Global Impact Mission
Control. A pure READ/aggregation layer over models and services already
built in PR2-5. Nothing in this module runs discovery, activates an
agent, creates a project, records an outcome, or writes to Evidence
Memory — every function below either queries already-persisted rows or
calls an already-existing, already-tested pure function (e.g.
`evidence_gate.evaluate_cluster`, `orchestrator.count_shortlisted`) for
transparent display. No new intelligence engine, agent architecture,
project model, MRV model, or Evidence Memory system lives here.

State-honesty discipline (Phase 4): every dict below uses the SAME state
vocabulary the underlying model already uses (an OutreachDraft's real
`status`, a ConnectionCandidate's real `status`, ...) — this module never
collapses "draft" into "sent" or "proposed" into "approved".
"""
from django.utils import timezone

from good_agents.models import (
    ActionGate, ActionPathway, ConnectionCandidate, FundingMatch, GoodAgentDefinition, GoodDiscoveryRun,
    GoodMission, GoodOpportunity, HumanReviewDecision, ImpactReceipt, OutreachDraft, ProjectCandidate,
    ResourceMatch, ResponsibleParty, SignalCluster, SignalProvider, WorldSignal,
)
from good_agents.services.evidence_gate import evaluate_cluster
from good_agents.services.orchestrator import Signal, count_shortlisted

FLAGSHIP_MISSION_NAME = 'Global Real-Time Signal Monitoring (Live Public Sources)'

NOT_REACHED = 'Not reached'
NOT_MEASURED = 'Not measured'
NOT_VERIFIED = 'Not verified'


# --- 1. Flagship mission / mission status -----------------------------------

def get_flagship_mission():
    return GoodMission.objects.filter(name=FLAGSHIP_MISSION_NAME).first()


def latest_run_for_mission(mission):
    return mission.runs.order_by('-created_at').first() if mission else None


def mission_status(mission):
    if mission is None:
        return None
    run = latest_run_for_mission(mission)
    return {
        'mission': mission,
        'latest_run': run,
        'run_status': run.status if run else 'never_run',
        'last_completed_at': run.completed_at if run and run.status == 'completed' else None,
    }


# --- 5. Signal funnel ---------------------------------------------------

def signal_funnel(mission):
    """
    Every count here is a live query (Phase 5). `GoodDiscoveryRun` rows
    are genuinely mission-scoped (`mission_config` FK); `WorldSignal`/
    `SignalCluster` are a shared global pool ALL missions triage from
    (see discovery_engine.py's own re-derivation of `status='open'`
    clusters every run) — reported honestly as pool-wide counts rather
    than fabricating a false per-mission boundary that doesn't exist in
    the schema.
    """
    runs = mission.runs.all() if mission else GoodDiscoveryRun.objects.none()
    opportunities = GoodOpportunity.objects.filter(discovery_run__in=runs)

    return {
        'signals_fetched': sum(r.signals_reviewed for r in runs),
        'duplicates_removed': sum(r.duplicates_removed for r in runs),
        'noise_rejected_pool_wide': SignalCluster.objects.filter(status='discarded').count(),
        'signals_pool_total': WorldSignal.objects.count(),
        'clusters_reaching_evidence_gate': SignalCluster.objects.exclude(status='discarded').count(),
        'opportunities_detected': opportunities.count(),
        'opportunities_qualified': opportunities.filter(status='qualified').count(),
        'opportunities_human_reviewed': opportunities.filter(action_gate__isnull=False).exclude(
            action_gate__current_state__in=['discovered'],
        ).count(),
        'actions_approved': ActionPathway.objects.filter(opportunity__in=opportunities).count(),
        'projects_created': ProjectCandidate.objects.filter(opportunity__in=opportunities, status='created').count(),
        'outcomes_measured': opportunities.filter(status__in=['measured', 'verified']).count(),
        'outcomes_verified': opportunities.filter(status='verified').count(),
        'evidence_memory_records_created': _evidence_memory_count_for_opportunities(opportunities),
    }


def _evidence_memory_count_for_opportunities(opportunities):
    from evidence_memory.models import EvidenceMemory
    refs = [
        f'waste_to_value_capital_allocation_engine.VerifiedCapitalOutcome:{r.verified_outcome_id}'
        for r in ImpactReceipt.objects.filter(opportunity__in=opportunities, verified_outcome__isnull=False)
    ]
    if not refs:
        return 0
    return EvidenceMemory.objects.filter(source_reference__in=refs).count()


# --- 6. Noise visibility --------------------------------------------------

def noise_sample(limit=10):
    """
    A sample of real rejected signal clusters, each with the SAME
    deterministic reason `evidence_gate.evaluate_cluster` produced at
    triage time — recomputed here purely for display (a pure function
    over already-stored fields, not a second decision-making pass; the
    real decision already happened and is reflected in `status='discarded'`).
    """
    clusters = SignalCluster.objects.filter(status='discarded').order_by('-updated_at')[:limit]
    sample = []
    for cluster in clusters:
        signal = cluster.signals.first()
        result = evaluate_cluster(cluster)
        sample.append({
            'cluster': cluster,
            'source': signal.provider.name if signal and signal.provider_id else (signal.publisher if signal else ''),
            'signal_type': signal.signal_type if signal else cluster.signal_type,
            'excerpt': (signal.summary or signal.title)[:200] if signal else cluster.representative_title,
            'reason_rejected': result.reason,
            'timestamp': cluster.updated_at,
        })
    return sample


# --- 8. Attention economy -------------------------------------------------

def attention_economy(mission):
    runs = mission.runs.all() if mission else GoodDiscoveryRun.objects.none()
    opportunities = GoodOpportunity.objects.filter(discovery_run__in=runs)
    needing_attention = opportunities.filter(action_gate__current_state__in=['discovered', 'needs_review'])
    reviewed = HumanReviewDecision.objects.filter(opportunity__in=opportunities).count()
    return {
        'signals_scanned': sum(r.signals_reviewed for r in runs),
        'noise_rejected_pool_wide': SignalCluster.objects.filter(status='discarded').count(),
        'items_needing_attention': needing_attention.count(),
        'human_reviews_completed': reviewed,
        'top_3_selected': min(3, opportunities.count()),
    }


# --- 7. 114-agent transparency --------------------------------------------

def agent_transparency(opportunity):
    """
    Never implies 114 LLM calls (Phase 7's own instruction): `shortlisted`
    is recomputed via the exact same deterministic keyword-overlap scoring
    already used at discovery time (`orchestrator.count_shortlisted` — the
    same real function, just reporting a count the real pipeline discards).
    `activated`/`useful_reasoning_outputs` are the real, persisted numbers.
    """
    total_available = GoodAgentDefinition.objects.filter(is_active=True).count()
    activations = list(opportunity.agent_activations.select_related('agent').all())
    useful = sum(1 for a in activations if a.reason_activated or a.recommended_next_analysis)
    model_assisted = sum(1 for a in activations if a.cost_usd > 0)

    shortlisted = None
    lead_signal = WorldSignal.objects.filter(title__in=opportunity.detected_signals).first()
    if lead_signal is not None:
        signal = Signal(
            text=f'{lead_signal.title}. {lead_signal.summary}',
            domains=([lead_signal.sector] if lead_signal.sector else []) + list(lead_signal.tags),
            geography=lead_signal.region,
        )
        shortlisted = count_shortlisted(signal)

    return {
        'total_available': total_available,
        'shortlisted': shortlisted,
        'activated': len(activations),
        'useful_reasoning_outputs': useful,
        'model_assisted_count': model_assisted,
        'deterministic_count': len(activations) - model_assisted,
        'activations': [
            {
                'principle': a.agent.name, 'position': a.get_position_display(),
                'reason': a.reason_activated, 'concern': a.concern,
                'mode': 'model-assisted' if a.cost_usd > 0 else 'deterministic',
            }
            for a in activations
        ],
    }


# --- 3. Truth chain --------------------------------------------------------

def truth_chain(opportunity):
    """
    One node per real stage, each with a `reached` bool and a soft link
    (`url_name`/`url_args`) where a dedicated page exists — never a
    recomputation of any upstream decision, only presence/absence checks
    over already-persisted rows (Phase 3).
    """
    gate = getattr(opportunity, 'action_gate', None)
    pathway = opportunity.action_pathways.order_by('-created_at').first()
    responsible_party = opportunity.responsible_parties.order_by('-confidence').first()
    outreach = OutreachDraft.objects.filter(action_pathway__opportunity=opportunity).order_by('-created_at').first()
    connection = ConnectionCandidate.objects.filter(resource_match__need__opportunity=opportunity).order_by('-created_at').first()
    project_candidate = getattr(opportunity, 'project_candidate', None)
    receipt = getattr(opportunity, 'impact_receipt', None)

    lead_signal = WorldSignal.objects.filter(title__in=opportunity.detected_signals).first()

    nodes = [
        {'stage': 'Signal', 'reached': lead_signal is not None,
         'detail': lead_signal.title if lead_signal else 'No originating signal on record.'},
        {'stage': 'Source', 'reached': lead_signal is not None and bool(lead_signal.publisher),
         'detail': lead_signal.publisher if lead_signal and lead_signal.publisher else 'Publisher not recorded.'},
        {'stage': 'Evidence', 'reached': bool(opportunity.evidence_refs),
         'detail': f'{len(opportunity.evidence_refs)} evidence reference(s).' if opportunity.evidence_refs else 'No evidence references recorded.'},
        {'stage': 'Principles activated', 'reached': opportunity.agent_activations.exists(),
         'detail': f'{opportunity.agent_activations.count()} principle(s) activated.'},
        {'stage': 'Opportunity', 'reached': True, 'detail': opportunity.get_status_display()},
        {'stage': 'Human review', 'reached': gate is not None and gate.current_state not in ('discovered',),
         'detail': gate.get_current_state_display() if gate else 'Not yet reviewed.'},
        {'stage': 'Action pathway', 'reached': pathway is not None,
         'detail': pathway.get_pathway_type_display() if pathway else 'No action pathway yet.'},
        {'stage': 'Responsible party', 'reached': responsible_party is not None,
         'detail': f'{responsible_party.name} ({responsible_party.get_resolution_status_display()})' if responsible_party else 'No responsible party identified.'},
        {'stage': 'Connection / outreach', 'reached': outreach is not None or connection is not None,
         'detail': (outreach.get_status_display() if outreach else '') or (connection.get_status_display() if connection else '') or 'No outreach or connection yet.'},
        {'stage': 'Project candidate', 'reached': project_candidate is not None,
         'detail': project_candidate.get_status_display() if project_candidate else 'No project candidate.'},
        {'stage': 'Project', 'reached': bool(project_candidate and project_candidate.created_project_id),
         'detail': project_candidate.created_project.name if project_candidate and project_candidate.created_project_id else 'No real project created.'},
        {'stage': 'Execution', 'reached': bool(project_candidate and project_candidate.created_project_id and project_candidate.created_project.timeline_milestones.exists()),
         'detail': 'See Execution / MRV section.'},
        {'stage': 'Outcome', 'reached': opportunity.status in ('measured', 'verified'),
         'detail': opportunity.get_status_display()},
        {'stage': 'Verification', 'reached': opportunity.status == 'verified',
         'detail': 'Independently verified.' if opportunity.status == 'verified' else 'Not independently verified.'},
        {'stage': 'Impact Receipt', 'reached': receipt is not None,
         'detail': 'Receipt exists.' if receipt else 'No Impact Receipt.'},
        {'stage': 'Evidence Memory', 'reached': bool(receipt and evidence_memory_for_receipt(receipt).exists()),
         'detail': 'Entered Evidence Memory.' if receipt and evidence_memory_for_receipt(receipt).exists() else 'Not yet in Evidence Memory.'},
    ]
    return nodes


# --- 11. Zero-capital-first lane -------------------------------------------

def zero_capital_lane(mission):
    runs = mission.runs.all() if mission else GoodDiscoveryRun.objects.none()
    opportunities = GoodOpportunity.objects.filter(discovery_run__in=runs)
    pathways = ActionPathway.objects.filter(opportunity__in=opportunities).select_related('opportunity', 'owner')
    return [
        {
            'pathway': p, 'opportunity': p.opportunity,
            'capital_required_now': p.get_capital_required_display(),
            'why': p.rationale or p.zero_capital_path or 'No rationale recorded.',
            'next_step': p.next_step or 'Not yet set.',
            'human_approval_required': True,  # structurally always true — see action_pathway.py's own gate requirement
        }
        for p in pathways
    ]


# --- Resource / funding matches (part of "2. Mission Control" section list) --

def resource_matches_lane(mission):
    runs = mission.runs.all() if mission else GoodDiscoveryRun.objects.none()
    opportunities = GoodOpportunity.objects.filter(discovery_run__in=runs)
    return (
        ResourceMatch.objects.filter(need__opportunity__in=opportunities)
        .select_related('need__opportunity', 'resource')
    )


def funding_matches_lane(mission):
    runs = mission.runs.all() if mission else GoodDiscoveryRun.objects.none()
    opportunities = GoodOpportunity.objects.filter(discovery_run__in=runs)
    matches = FundingMatch.objects.filter(opportunity__in=opportunities).select_related('opportunity', 'funding_action')
    return [
        {'match': m, 'action': getattr(m, 'funding_action', None)}
        for m in matches
    ]


# --- 12. Responsible party / connection lane --------------------------------

def responsible_party_lane(mission):
    runs = mission.runs.all() if mission else GoodDiscoveryRun.objects.none()
    opportunities = GoodOpportunity.objects.filter(discovery_run__in=runs)
    parties = ResponsibleParty.objects.filter(opportunity__in=opportunities).select_related('opportunity', 'confirmed_by')
    result = []
    for party in parties:
        contact = party.contacts.first()
        outreach = OutreachDraft.objects.filter(contact__responsible_party=party).order_by('-created_at').first()
        result.append({
            'party': party, 'opportunity': party.opportunity,
            'why_identified': party.notes or 'Suggested from a real signal publisher field.',
            'provenance': party.evidence_ref or 'No provenance recorded.',
            'contact_status': contact.get_status_display() if contact else 'No contact on record.',
            'outreach_status': outreach.get_status_display() if outreach else 'No outreach drafted.',
            'human_approval': 'Confirmed' if party.resolution_status == 'known_organisation' else 'Not yet confirmed',
        })
    return result


def outreach_connection_truth(mission):
    """Explicit truth states — never shows 'contacted' for a mere draft (Phase 13)."""
    runs = mission.runs.all() if mission else GoodDiscoveryRun.objects.none()
    opportunities = GoodOpportunity.objects.filter(discovery_run__in=runs)
    outreach = list(
        OutreachDraft.objects.filter(action_pathway__opportunity__in=opportunities)
        .select_related('action_pathway__opportunity')
    )
    connections = list(
        ConnectionCandidate.objects.filter(resource_match__need__opportunity__in=opportunities)
        .select_related('resource_match__need__opportunity', 'resource_match__resource')
    )
    return {'outreach': outreach, 'connections': connections}


# --- 14. Project bridge -----------------------------------------------------

def project_bridge_chain(opportunity):
    candidate = getattr(opportunity, 'project_candidate', None)
    if candidate is None:
        return None
    return {
        'candidate': candidate,
        'originating_signal': WorldSignal.objects.filter(title__in=opportunity.detected_signals).first(),
        'opportunity': opportunity,
        'relevant_principles': [a.agent.name for a in opportunity.agent_activations.select_related('agent').all()],
        'review_decision': opportunity.review_decisions.order_by('-created_at').first(),
        'action_pathway': candidate.action_pathway,
        'created_project': candidate.created_project,
        'current_stage': candidate.created_project.get_status_display() if candidate.created_project_id else 'Not yet created.',
    }


# --- 15. Execution / MRV -----------------------------------------------------

def execution_mrv_for_project(project):
    """Reuses capital_guardian.services.execution_monitoring — no duplicate execution/MRV logic (Phase 15)."""
    if project is None:
        return None
    from capital_guardian.services.execution_monitoring import capital_decisions_for_project, expected_vs_actual

    milestone = project.timeline_milestones.exclude(status='complete').order_by('planned_start').first()
    decisions = list(capital_decisions_for_project(project))
    ctx = expected_vs_actual(decisions[0]) if decisions else None
    return {
        'current_milestone': milestone,
        'blockers': milestone.notes if milestone and milestone.status == 'delayed' else 'None recorded.',
        'expected_vs_actual': ctx,
        'verification_status': ctx['mrv_status'] if ctx else 'Not started.',
    }


# --- 16/17. Verified impact + Impact Receipts --------------------------------

def verified_impact_list(mission):
    runs = mission.runs.all() if mission else GoodDiscoveryRun.objects.none()
    return GoodOpportunity.objects.filter(discovery_run__in=runs, status='verified').select_related('impact_receipt')


def impact_receipts_list(mission):
    runs = mission.runs.all() if mission else GoodDiscoveryRun.objects.none()
    opportunities = GoodOpportunity.objects.filter(discovery_run__in=runs)
    return ImpactReceipt.objects.filter(opportunity__in=opportunities).select_related('opportunity')


def evidence_memory_for_receipt(receipt):
    from evidence_memory.models import EvidenceMemory
    if receipt is None or not receipt.verified_outcome_id:
        return EvidenceMemory.objects.none()
    source_reference = f'waste_to_value_capital_allocation_engine.VerifiedCapitalOutcome:{receipt.verified_outcome_id}'
    return EvidenceMemory.objects.filter(source_reference=source_reference)


# --- 19. Impact velocity -----------------------------------------------------

def impact_velocity(opportunity):
    """
    Real timestamps only — never fills a missing stage with zero (Phase 19).
    Pulled from ActionTimelineEvent, the one real append-only clock this
    pipeline already keeps.
    """
    events = {e.event_type: e.created_at for e in opportunity.timeline_events.order_by('created_at')}

    def gap(start_key, end_key, missing_label=NOT_REACHED):
        start, end = events.get(start_key), events.get(end_key)
        if start is None or end is None:
            return missing_label
        return end - start

    return {
        'signal_to_opportunity': 'Not tracked at signal granularity — see opportunity.created_at.',
        'opportunity_to_review': gap('discovered', 'human_reviewed'),
        'review_to_approved_action': gap('human_reviewed', 'action_approved'),
        'action_to_project': gap('action_approved', 'project_created'),
        'project_to_measurement': gap('project_created', 'outcome_measured', NOT_MEASURED),
        'measurement_to_verification': gap('outcome_measured', 'outcome_verified', NOT_VERIFIED),
    }


# --- 20. Mission health -------------------------------------------------------

def mission_health():
    providers = list(SignalProvider.objects.all())
    return {
        'providers_active': sum(1 for p in providers if p.status == 'active'),
        'providers_failed': sum(1 for p in providers if p.status == 'failed'),
        'providers': providers,
        'last_successful_ingestion': max(
            (p.last_refresh_at for p in providers if p.last_refresh_at), default=None,
        ),
        'signals_pending': WorldSignal.objects.filter(status='new').count(),
        'reviews_pending': GoodOpportunity.objects.filter(
            action_gate__current_state__in=['discovered', 'needs_review'],
        ).count(),
        'actions_pending_approval': ActionGate.objects.filter(
            current_state__in=['discovered', 'needs_review'],
        ).count(),
        'outreach_awaiting_approval': OutreachDraft.objects.filter(status='ready_for_review').count(),
        'projects_blocked': ProjectCandidate.objects.filter(status='rejected').count(),
        'outcomes_awaiting_verification': GoodOpportunity.objects.filter(status='measured').count(),
    }


# --- 21. Mission comparison ---------------------------------------------------

def mission_comparison():
    """No mystery 'mission score' (Phase 21's own instruction) — real counts only."""
    rows = []
    for mission in GoodMission.objects.all():
        runs = mission.runs.all()
        opportunities = GoodOpportunity.objects.filter(discovery_run__in=runs)
        rows.append({
            'mission': mission,
            'signals_reviewed': sum(r.signals_reviewed for r in runs),
            'opportunities_qualified': opportunities.filter(status='qualified').count(),
            'opportunities_human_reviewed': opportunities.filter(action_gate__isnull=False).exclude(
                action_gate__current_state='discovered',
            ).count(),
            'actions_approved': ActionPathway.objects.filter(opportunity__in=opportunities).count(),
            'zero_capital_actions': ActionPathway.objects.filter(opportunity__in=opportunities, capital_required='no').count(),
            'projects_created': ProjectCandidate.objects.filter(opportunity__in=opportunities, status='created').count(),
            'verified_outcomes': opportunities.filter(status='verified').count(),
        })
    return rows


# --- 27. Global Good Map (reuse, no globe/Cesium) -----------------------------

def geographic_opportunity_list(mission):
    """
    Reuses the exact same region-level fields `good_map_api` already
    exposes (Phase 27) — never a coordinate, never an individual
    identifier. No renderer/globe/Cesium here, just a real list.
    """
    runs = mission.runs.all() if mission else GoodDiscoveryRun.objects.none()
    opportunities = GoodOpportunity.objects.filter(discovery_run__in=runs).select_related('geography')
    return [
        {
            'title': o.title, 'region': o.region, 'country': o.geography.name if o.geography_id else '',
            'theme': o.get_theme_display() if o.theme else '', 'urgency': o.urgency, 'pk': o.pk,
        }
        for o in opportunities
    ]


# --- 23. Demo story mode ------------------------------------------------------

def demo_story(opportunity):
    """
    A guided, deterministic walkthrough built entirely from real stored
    fields (Phase 23) — no AI-generated narration, no unsupported claims.
    """
    lead_signal = WorldSignal.objects.filter(title__in=opportunity.detected_signals).first()
    noise_examples = noise_sample(limit=3)
    activations = list(opportunity.agent_activations.select_related('agent').all())
    gate = getattr(opportunity, 'action_gate', None)
    pathway = opportunity.action_pathways.order_by('-created_at').first()
    party = opportunity.responsible_parties.order_by('-confidence').first()
    outreach = OutreachDraft.objects.filter(action_pathway__opportunity=opportunity).order_by('-created_at').first()
    connection = ConnectionCandidate.objects.filter(resource_match__need__opportunity=opportunity).order_by('-created_at').first()
    candidate = getattr(opportunity, 'project_candidate', None)
    receipt = getattr(opportunity, 'impact_receipt', None)

    return [
        {'step': 1, 'title': 'Real signal', 'text': lead_signal.title if lead_signal else 'No originating signal on record.'},
        {'step': 2, 'title': 'Why EcoIQ noticed it', 'text': f'{len(activations)} of {GoodAgentDefinition.objects.filter(is_active=True).count()} available principle lenses activated.' if activations else 'No lens activated for this signal.'},
        {'step': 3, 'title': 'Noise rejected (examples from the same run)', 'text': f'{len(noise_examples)} example(s) shown in Mission Control\'s Noise section.'},
        {'step': 4, 'title': 'Principles activated', 'text': ', '.join(a.agent.name for a in activations) or 'None.'},
        {'step': 5, 'title': 'Opportunity', 'text': f'{opportunity.title} — {opportunity.get_status_display()}'},
        {'step': 6, 'title': 'Human review', 'text': gate.get_current_state_display() if gate else 'Not yet reviewed.'},
        {'step': 7, 'title': 'Action pathway', 'text': pathway.get_pathway_type_display() if pathway else 'None proposed yet.'},
        {'step': 8, 'title': 'Zero-capital / resource / funding option', 'text': (f'Capital required: {pathway.get_capital_required_display()}' if pathway else 'No pathway yet.')},
        {'step': 9, 'title': 'Responsible party', 'text': f'{party.name} ({party.get_resolution_status_display()})' if party else 'None identified.'},
        {'step': 10, 'title': 'Outreach / connection state', 'text': (outreach.get_status_display() if outreach else '') or (connection.get_status_display() if connection else '') or 'None yet.'},
        {'step': 11, 'title': 'Project', 'text': candidate.created_project.name if candidate and candidate.created_project_id else 'No project created.'},
        {'step': 12, 'title': 'Execution', 'text': 'See Execution / MRV section.' if candidate and candidate.created_project_id else 'Not reached.'},
        {'step': 13, 'title': 'Outcome', 'text': opportunity.get_status_display()},
        {'step': 14, 'title': 'Verification', 'text': 'Independently verified.' if opportunity.status == 'verified' else 'Not independently verified.'},
        {'step': 15, 'title': 'Impact Receipt', 'text': 'Exists.' if receipt else 'Does not exist yet.'},
        {'step': 16, 'title': 'Learning loop', 'text': 'Available as governed historical evidence.' if receipt and evidence_memory_for_receipt(receipt).exists() else 'Not yet in Evidence Memory.'},
    ]
