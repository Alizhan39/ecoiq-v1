"""
good_agents/services/pilot_launchpad.py — PR11: Real-World Pilot
Launchpad. A pure READ/computation layer over models and services
already built in PR2-10 (good_agents, capability_graph,
partner_participation, collaboration_rooms, capital_guardian,
gold_intelligence, evidence_memory). Nothing here runs discovery,
activates an agent, creates a project, sends outreach, records a
capital decision, or writes to Evidence Memory — every function below
either queries already-persisted rows or composes them into one
honest, deterministic read.

Same state-honesty discipline as mission_control.py: never collapses a
real model's status into something stronger than it is, never invents
a numeric "readiness score", never marks a stage complete that has not
actually happened. Where information genuinely does not exist yet the
functions below say so explicitly (MISSING / Not tracked / Unknown)
rather than omitting the field.
"""
from django.urls import reverse
from django.utils import timezone

from good_agents.models import (
    ActionContact, ConnectionCandidate, GoodOpportunity, OutreachDraft, ResponsibleParty, WorldSignal,
)

CONTROLLED_TEST_PREFIX = '[CONTROLLED TEST]'


def _link(label, url_name, *args):
    """
    Resolves a real URL now, in Python, rather than passing a
    dynamically-named `{% url %}` tag to the template — Django templates
    cannot cleanly vary both the URL name AND its argument shape per row
    (the exact "no variable-key dict lookup" lesson from PR6). Returns
    None if the name doesn't resolve (e.g. an app not installed in this
    environment) rather than crashing the page.
    """
    try:
        return {'label': label, 'url': reverse(url_name, args=args)}
    except Exception:
        return {'label': label, 'url': None}

# --- Provenance vocabulary (Phase 5 / 26) -----------------------------------
# Every truth-chain node and every organisation reference in this module
# carries one of these labels — never a plain "done"/"not done" boolean
# once a human could otherwise mistake demo/estimated/controlled data for
# a real, verified fact.
PROV_MEASURED = 'MEASURED'
PROV_VERIFIED = 'VERIFIED'
PROV_PUBLIC_SOURCE = 'PUBLIC_SOURCE'
PROV_HUMAN_APPROVED = 'HUMAN_APPROVED'
PROV_PARTNER_DECLARED = 'PARTNER_DECLARED'
PROV_DETERMINISTIC = 'DETERMINISTIC'
PROV_ESTIMATED = 'ESTIMATED'
PROV_MISSING = 'MISSING'
PROV_BLOCKED = 'BLOCKED'
PROV_NOT_YET_OCCURRED = 'NOT_YET_OCCURRED'

READY, PARTIAL, BLOCKED, UNKNOWN, NOT_APPLICABLE = 'READY', 'PARTIAL', 'BLOCKED', 'UNKNOWN', 'NOT_APPLICABLE'


# --- Real vs controlled-test labelling (Phase 12 / 26) ----------------------

def is_controlled_test_organisation(organisation):
    return bool(organisation and organisation.name.startswith(CONTROLLED_TEST_PREFIX))


def data_provenance_label(organisation):
    """
    Distinguishes REAL_PUBLIC_ORGANISATION / REAL_PARTICIPATING_ORGANISATION
    / CONTROLLED_TEST_ORGANISATION — never blended (Phase 12). Participation
    is read straight from partner_participation, never inferred from a
    capability-graph match alone (a discovered organisation with no verified
    membership has NOT agreed to participate).
    """
    if organisation is None:
        return 'UNKNOWN'
    if is_controlled_test_organisation(organisation):
        return 'CONTROLLED_TEST_ORGANISATION'
    from partner_participation.models import OrganisationMembership
    if OrganisationMembership.objects.filter(organisation=organisation, status='verified_member').exists():
        return 'REAL_PARTICIPATING_ORGANISATION'
    return 'REAL_DISCOVERED_ORGANISATION'


# --- 1/2. Flagship pilot selection ------------------------------------------

def flagship_pilot_criteria(opportunity):
    """
    The explicit, deterministic criteria a candidate flagship pilot is
    judged against (Phase 2) — every check here is a real query over
    already-persisted rows, never a subjective/LLM judgement of "which
    looks best."
    """
    return {
        'evidence_backed': bool(opportunity.evidence_refs) and not opportunity.insufficient_evidence,
        'understandable': bool(opportunity.problem_statement),
        'location_known': bool(opportunity.geography_id or opportunity.region),
        'multi_principle_relevance': opportunity.agent_activations.count() >= 2,
        'real_organisation_identified': opportunity.responsible_parties.filter(
            organisation__isnull=False,
        ).exclude(organisation__name__startswith=CONTROLLED_TEST_PREFIX).exists(),
        'measurable_eventually': bool(opportunity.potential_benefit),
    }


def select_flagship_pilot(candidates=None):
    """
    Deterministic selection over real (non-controlled-test) opportunities.
    Minimum bar to even be considered: evidence-backed + understandable +
    at least one principle activated — anything short of that returns
    None (NOT_READY_FOR_PILOT is an honest, legitimate outcome, Phase 2's
    own explicit instruction). Among opportunities that clear the bar, the
    one satisfying the most criteria wins; ties broken by higher urgency,
    then earliest created_at (the longest-known real candidate, not a
    freshness bias).
    """
    qs = candidates if candidates is not None else GoodOpportunity.objects.all()
    scored = []
    for opportunity in qs:
        criteria = flagship_pilot_criteria(opportunity)
        if not (criteria['evidence_backed'] and criteria['understandable'] and opportunity.agent_activations.exists()):
            continue
        scored.append((sum(1 for v in criteria.values() if v), opportunity.urgency, opportunity))
    if not scored:
        return None
    scored.sort(key=lambda row: (row[0], row[1], -row[2].created_at.timestamp()), reverse=True)
    return scored[0][2]


# --- 3. Pilot readiness scorecard --------------------------------------------

def readiness_scorecard(opportunity):
    """
    Deterministic checklist (Phase 3) — never a fabricated numeric score.
    Each item's state is READY / PARTIAL / BLOCKED / UNKNOWN /
    NOT_APPLICABLE, derived purely from presence/absence of real rows.
    """
    gate = getattr(opportunity, 'action_gate', None)
    pathway = opportunity.action_pathways.order_by('-created_at').first()
    responsible_party = opportunity.responsible_parties.order_by('-confidence').first()
    organisation = responsible_party.organisation if responsible_party and responsible_party.organisation_id else None
    contact = ActionContact.objects.filter(responsible_party__opportunity=opportunity).order_by('-last_verified').first()
    outreach = OutreachDraft.objects.filter(action_pathway__opportunity=opportunity).order_by('-created_at').first()

    routing_candidate = None
    if organisation is not None and not is_controlled_test_organisation(organisation):
        from partner_participation.models import RoutingCandidate
        routing_candidate = RoutingCandidate.objects.filter(organisation=organisation, opportunity=opportunity).first()

    capability_evidence = organisation is not None and organisation.capabilities.exclude(
        verification_state__in=('unverified', 'disputed', 'expired'),
    ).exists()

    items = [
        ('Evidence sufficient?', READY if opportunity.evidence_refs and not opportunity.insufficient_evidence else BLOCKED),
        ('Problem/need clear?', READY if opportunity.problem_statement else BLOCKED),
        ('Location known?', READY if (opportunity.geography_id or opportunity.region) else PARTIAL),
        ('Affected party known?', READY if opportunity.affected_population else UNKNOWN),
        ('Relevant principles identified?', READY if opportunity.agent_activations.exists() else BLOCKED),
        ('Better Way / action pathway exists?', READY if pathway else PARTIAL),
        ('Responsible organisation identified?', READY if organisation else BLOCKED),
        ('Capability evidence exists?', READY if capability_evidence else (PARTIAL if organisation else NOT_APPLICABLE)),
        ('Public contact route verified?', READY if (contact and contact.status == 'verified') else (PARTIAL if contact else BLOCKED)),
        ('Human outreach approval obtained?', READY if (outreach and outreach.status in ('approved', 'sent', 'replied')) else (PARTIAL if outreach else NOT_APPLICABLE)),
        ('Partner response received?', READY if (routing_candidate and routing_candidate.status not in ('routing_candidate', 'ready_for_ecoiq_review', 'approved_to_share', 'shared', 'no_response')) else (PARTIAL if routing_candidate else NOT_APPLICABLE)),
        ('Collaboration possible?', READY if getattr(routing_candidate, 'collaboration_room', None) else NOT_APPLICABLE),
        ('Missing evidence known?', READY if pathway is not None else UNKNOWN),
        ('Funding/resource dependency known?', READY if opportunity.capital_required_usd is not None or opportunity.zero_capital_possible else UNKNOWN),
        ('Measurement plan possible?', READY if opportunity.potential_benefit else UNKNOWN),
    ]
    return [{'item': label, 'state': state} for label, state in items]


# --- 6. 114-principle relevance ---------------------------------------------

def principle_relevance(opportunity):
    """
    Wraps AgentActivationRecord — the real, persisted per-principle
    reasoning already produced at discovery time (Phase 6). Never
    re-derives or re-scores; conflicting positions are surfaced, not
    averaged away.
    """
    activations = opportunity.agent_activations.select_related('agent').order_by('-confidence')
    return [
        {
            'principle': a.agent.name,
            'principle_id': a.agent.principle_id,
            'relationship_type': a.get_position_display(),
            'confidence': a.confidence,
            'evidence_considered': a.evidence_considered,
            'reason': a.reason_activated,
            'concern': a.concern,
            'provenance': PROV_DETERMINISTIC if a.cost_usd == 0 else PROV_ESTIMATED,
        }
        for a in activations
    ]


# --- 7. Better Way options ---------------------------------------------------

def better_way_options(opportunity):
    """
    Wraps ActionPathway (Phase 7). Cost/complexity/risk are only ever
    reported from fields that actually exist on the model
    (capital_required, zero_capital_path, rationale) — never fabricated
    structured numbers this pipeline does not track. Never labels an
    option "best"; only reports its real status.
    """
    pathways = opportunity.action_pathways.select_related('owner').order_by('-created_at')
    return [
        {
            'pathway': p,
            'pathway_type': p.get_pathway_type_display(),
            'expected_benefit': p.rationale or 'Not recorded.',
            'known_cost': p.zero_capital_path if p.capital_required == 'no' else 'Not tracked as a structured figure — see capital_required_usd on the opportunity.',
            'capital_required': p.get_capital_required_display(),
            'evidence_basis': p.rationale or 'Not recorded.',
            'risks': p.blocked_reason or 'None recorded.',
            'decision_state': p.get_status_display(),
            'principle_alignment': [a.agent.name for a in opportunity.agent_activations.all()],
        }
        for p in pathways
    ]


# --- 8. Capability Graph organisation matching -------------------------------

def capability_graph_matches(opportunity):
    """
    Organisation matches via the real Capability Graph (Phase 8) — reads
    the ResponsibleParty rows already resolved by
    responsible_party.suggest_from_capability_graph/suggest_from_signal,
    never re-runs matching here. Explicitly separates DISCOVERED from
    PARTICIPATING and flags controlled-test rows so they can never be
    mistaken for real public participation.
    """
    parties = opportunity.responsible_parties.filter(organisation__isnull=False).select_related('organisation')
    matches = []
    for party in parties:
        organisation = party.organisation
        capability_edges = list(organisation.capabilities.exclude(verification_state__in=('disputed', 'expired')))
        best_route = None
        for edge in capability_edges:
            route = edge.public_routes.filter(is_currently_open=True, superseded_at__isnull=True).order_by('-verified_at').first()
            if route is not None:
                best_route = route
                break
        matches.append({
            'organisation': organisation,
            'responsible_party': party,
            'provenance_label': data_provenance_label(organisation),
            'capability_edges': capability_edges,
            'best_route': best_route,
            'why_relevant': party.notes or 'No rationale recorded.',
            'limitations': '; '.join(e.limitations for e in capability_edges if e.limitations) or 'No limitations recorded.',
            'resolution_status': party.get_resolution_status_display(),
        })
    return matches


# --- 9/11. Contact route + honest outreach state machine --------------------

CONTACT_STATE_LABELS = {
    'not_identified': 'Not identified',
    'public_route_found': 'Public route found',
    'draft_prepared': 'Draft prepared',
    'human_approved': 'Human approved — ready to send',
    'sent': 'Sent',
    'delivery_unknown': 'Sent — delivery unknown',
    'replied': 'Replied',
    'declined': 'Declined',
    'no_response': 'No response',
}


def contact_route_state(opportunity):
    """
    Honest contact/outreach state machine (Phase 11) — computed, not a
    new mutable field, so it can never drift from the real
    ActionContact/OutreachDraft rows it reads. 'READY_TO_SEND' is
    deliberately merged into 'human_approved': OutreachDraft's own
    'approved' status IS the only readiness gate this pipeline has —
    inventing a second, separate gate here would be a fabricated
    distinction, not an honest one (documented in the PR11 report).
    """
    contact = ActionContact.objects.filter(responsible_party__opportunity=opportunity).order_by('-last_verified').first()
    outreach = OutreachDraft.objects.filter(action_pathway__opportunity=opportunity).order_by('-created_at').first()

    if outreach is not None:
        state_map = {
            'draft': 'draft_prepared', 'ready_for_review': 'draft_prepared',
            'approved': 'human_approved', 'sent': 'delivery_unknown',
            'replied': 'replied', 'no_response': 'no_response', 'declined': 'declined',
            'follow_up_required': 'delivery_unknown',
        }
        state = state_map.get(outreach.status, 'draft_prepared')
        detail = f'{outreach.get_status_display()} ({outreach.get_draft_type_display()})'
    elif contact is not None:
        state, detail = 'public_route_found', f'{contact.public_contact_channel or "channel not recorded"} — {contact.get_status_display()}'
    else:
        state, detail = 'not_identified', 'No public contact route recorded yet.'

    return {'state': state, 'label': CONTACT_STATE_LABELS[state], 'detail': detail, 'contact': contact, 'outreach_draft': outreach}


# --- 10. Outreach pack -------------------------------------------------------

DISCLAIMER_NOT_CLAIMING = [
    'EcoIQ is not claiming this organisation has agreed to participate.',
    'This message does not create a partnership, obligation, or funding commitment.',
    'No impact or outcome is being claimed — only a request to explore relevance.',
]


def outreach_pack(opportunity):
    """
    Grounded, deterministic content package (Phase 10) — every field is
    assembled from real, already-persisted data. No AI/model-router call
    is used to draft this pack (a deliberate scope decision — see PR11
    report §25); a human still must review and approve via the existing
    OutreachDraft governance before anything is prepared to send.
    """
    responsible_party = opportunity.responsible_parties.order_by('-confidence').first()
    organisation = responsible_party.organisation if responsible_party and responsible_party.organisation_id else None
    principles = [a.agent.name for a in opportunity.agent_activations.select_related('agent').all()]
    routing_candidate = None
    room = None
    if organisation is not None:
        from partner_participation.models import RoutingCandidate
        routing_candidate = RoutingCandidate.objects.filter(organisation=organisation, opportunity=opportunity).first()
        room = getattr(routing_candidate, 'collaboration_room', None) if routing_candidate else None

    return {
        'mission_summary': opportunity.problem_statement,
        'why_contacting': (
            f'{organisation.name} was identified via EcoIQ\'s Capability Graph as having a real, '
            f'evidence-backed connection to this problem.' if organisation else 'No organisation identified yet.'
        ),
        'evidence_links': opportunity.evidence_refs,
        'why_relevant': responsible_party.notes if responsible_party else '',
        'relevant_principles': principles,
        'specific_ask': (
            opportunity.action_pathways.order_by('-created_at').first().next_step
            if opportunity.action_pathways.exists() else 'No specific ask drafted yet — create an Action Pathway first.'
        ),
        'not_claiming': DISCLAIMER_NOT_CLAIMING,
        'secure_collaboration_link': (_link('Open collaboration room', 'collaboration_rooms:room_detail', room.pk) if room else None),
        'organisation': organisation,
        'provenance_label': data_provenance_label(organisation) if organisation else None,
    }


def render_outreach_message(opportunity):
    """
    Renders outreach_pack() into a ready-to-review subject/body pair
    (Phase 10) — the same "deterministic render, human still approves"
    pattern PR9's render_invitation_message() and PR10's
    render_share_message() already established. Never sent directly;
    only ever used to pre-fill a new OutreachDraft that still goes
    through the existing draft -> ready_for_review -> approved -> sent
    governance ladder.
    """
    pack = outreach_pack(opportunity)
    subject = f'EcoIQ enquiry: {opportunity.title}'
    body_lines = [
        pack['mission_summary'],
        '',
        pack['why_contacting'],
        '',
        f'Relevant EcoIQ stewardship principles: {", ".join(pack["relevant_principles"]) or "none recorded"}.',
        '',
        f'What we are asking: {pack["specific_ask"]}',
        '',
        'What EcoIQ is NOT claiming:',
    ] + [f'- {line}' for line in pack['not_claiming']]
    return {'subject': subject, 'body': '\n'.join(body_lines), 'pack': pack}


# --- 13/14. Next best action + blocker engine --------------------------------

def blockers(opportunity):
    """
    Explicit blocker list (Phase 14) — every entry explains what's
    missing, why it matters, who can resolve it, and the real governed
    action that resolves it (never a dead-end message).
    """
    gate = getattr(opportunity, 'action_gate', None)
    responsible_party = opportunity.responsible_parties.order_by('-confidence').first()
    organisation = responsible_party.organisation if responsible_party and responsible_party.organisation_id else None
    contact = ActionContact.objects.filter(responsible_party__opportunity=opportunity).exists()
    pathway = opportunity.action_pathways.order_by('-created_at').first()
    outreach = OutreachDraft.objects.filter(action_pathway__opportunity=opportunity).order_by('-created_at').first()
    project_candidate = getattr(opportunity, 'project_candidate', None)

    found = []
    if opportunity.insufficient_evidence or not opportunity.evidence_refs:
        found.append({
            'code': 'INSUFFICIENT_EVIDENCE', 'what_missing': 'Real evidence references for this opportunity.',
            'why_it_matters': 'No governed action can proceed on an unsubstantiated claim.',
            'who_can_resolve': 'EcoIQ discovery/review staff', 'resolving_action': None,
        })
    if gate is None or gate.current_state == 'discovered':
        found.append({
            'code': 'HUMAN_REVIEW_PENDING', 'what_missing': 'A human review decision on this opportunity.',
            'why_it_matters': 'Nothing downstream (pathway, outreach, project) may start before human review.',
            'who_can_resolve': 'EcoIQ staff', 'resolving_action': _link('Review', 'good_agents:opportunity_detail', opportunity.pk),
        })
    if organisation is None:
        found.append({
            'code': 'NO_VERIFIED_CONTACT_ROUTE', 'what_missing': 'A resolved responsible organisation.',
            'why_it_matters': 'There is no one to route this opportunity to yet.',
            'who_can_resolve': 'EcoIQ staff (via Capability Graph)',
            'resolving_action': _link('Resolve via signal', 'good_agents:resolve_responsible_party', opportunity.pk),
        })
    elif not contact and not is_controlled_test_organisation(organisation):
        found.append({
            'code': 'NO_VERIFIED_CONTACT_ROUTE', 'what_missing': 'A verified public contact route for the matched organisation.',
            'why_it_matters': 'Outreach cannot be prepared without a real channel to send it to.',
            'who_can_resolve': 'EcoIQ staff', 'resolving_action': _link('Add contact route', 'good_agents:add_contact', responsible_party.pk),
        })
    if pathway is None and gate is not None and gate.current_state not in ('discovered', 'needs_review'):
        found.append({
            'code': 'ACTION_PATHWAY_MISSING', 'what_missing': 'An explicit action pathway.',
            'why_it_matters': 'There is no defined next step for this reviewed opportunity yet.',
            'who_can_resolve': 'EcoIQ staff', 'resolving_action': _link('Create pathway', 'good_agents:opportunity_detail', opportunity.pk),
        })
    if organisation is not None and not is_controlled_test_organisation(organisation):
        from partner_participation.models import RoutingCandidate
        routing_candidate = RoutingCandidate.objects.filter(organisation=organisation, opportunity=opportunity).first()
        if routing_candidate is not None and routing_candidate.status in ('shared', 'no_response'):
            found.append({
                'code': 'NO_PARTNER_RESPONSE', 'what_missing': 'A response from the routed organisation.',
                'why_it_matters': 'EcoIQ cannot decide a next step until the partner responds.',
                'who_can_resolve': 'The partner organisation', 'resolving_action': None,
            })
        room = getattr(routing_candidate, 'collaboration_room', None) if routing_candidate else None
        if room is not None:
            from collaboration_rooms.models import RoomConsent
            pending_consent = RoomConsent.objects.filter(proposal__room=room, status='pending').exists()
            if pending_consent:
                found.append({
                    'code': 'CONSENT_PENDING', 'what_missing': 'Mutual consent on a proposed next step.',
                    'why_it_matters': 'A next step never becomes actionable from silence — every required party must explicitly consent.',
                    'who_can_resolve': 'Required room participants',
                    'resolving_action': _link('Open room', 'collaboration_rooms:room_detail', room.pk),
                })
    if opportunity.capital_required_usd is None and not opportunity.zero_capital_possible:
        found.append({
            'code': 'FUNDING_UNKNOWN', 'what_missing': 'Whether this opportunity is zero-capital or requires funding.',
            'why_it_matters': 'The capital pathway cannot be planned while this is unknown.',
            'who_can_resolve': 'EcoIQ staff', 'resolving_action': None,
        })
    if project_candidate is not None and project_candidate.created_project_id is None and project_candidate.status == 'proposed':
        found.append({
            'code': 'EXECUTION_NOT_STARTED', 'what_missing': 'Approval + creation of the real project.',
            'why_it_matters': 'The project candidate is proposed but not yet approved into a real GoldProject.',
            'who_can_resolve': 'EcoIQ staff',
            'resolving_action': _link('Approve candidate', 'good_agents:project_candidate_approve', project_candidate.pk),
        })
    if project_candidate is not None and project_candidate.created_project_id and not project_candidate.created_project.timeline_milestones.exists():
        found.append({
            'code': 'EXECUTION_NOT_STARTED', 'what_missing': 'Execution milestones for the created project.',
            'why_it_matters': 'The project exists but no execution has been recorded yet.',
            'who_can_resolve': 'EcoIQ / project operations staff', 'resolving_action': None,
        })
    if project_candidate is not None and project_candidate.created_project_id:
        receipt = getattr(opportunity, 'impact_receipt', None)
        if receipt is None:
            found.append({
                'code': 'MRV_NOT_AVAILABLE', 'what_missing': 'A measurement/verification plan or Impact Receipt.',
                'why_it_matters': 'No impact can honestly be claimed until it is measured and verified.',
                'who_can_resolve': 'EcoIQ MRV staff', 'resolving_action': None,
            })
    return found


def next_best_action(opportunity):
    """
    Exactly one PRIMARY next action plus optional secondary actions
    (Phase 13). Priority order mirrors the canonical chain itself — never
    suggests an action whose prerequisites are unmet (e.g. never suggests
    "send outreach" before a draft has been approved).
    """
    gate = getattr(opportunity, 'action_gate', None)
    responsible_party = opportunity.responsible_parties.order_by('-confidence').first()
    organisation = responsible_party.organisation if responsible_party and responsible_party.organisation_id else None
    contact = ActionContact.objects.filter(responsible_party__opportunity=opportunity).order_by('-last_verified').first()
    pathway = opportunity.action_pathways.order_by('-created_at').first()
    outreach = OutreachDraft.objects.filter(action_pathway__opportunity=opportunity).order_by('-created_at').first()
    project_candidate = getattr(opportunity, 'project_candidate', None)
    routing_candidate = None
    if organisation is not None and not is_controlled_test_organisation(organisation):
        from partner_participation.models import RoutingCandidate
        routing_candidate = RoutingCandidate.objects.filter(organisation=organisation, opportunity=opportunity).first()
    room = getattr(routing_candidate, 'collaboration_room', None) if routing_candidate else None

    ladder = []
    if opportunity.insufficient_evidence or not opportunity.evidence_refs:
        ladder.append(('Acquire missing evidence', None))
    elif gate is None or gate.current_state == 'discovered':
        ladder.append(('Human review required', _link('Review', 'good_agents:opportunity_detail', opportunity.pk)))
    elif organisation is None:
        ladder.append(('Find responsible organisation via Capability Graph', _link('Resolve via signal', 'good_agents:resolve_responsible_party', opportunity.pk)))
    elif not is_controlled_test_organisation(organisation) and not organisation.capabilities.exclude(verification_state__in=('unverified', 'disputed', 'expired')).exists():
        ladder.append(('Verify organisation capability', _link('Verify', 'capability_graph:organisation_detail', organisation.pk)))
    elif not contact and not is_controlled_test_organisation(organisation):
        ladder.append(('Find/record public contact route', _link('Add contact route', 'good_agents:add_contact', responsible_party.pk)))
    elif outreach is None and pathway is not None:
        ladder.append(('Prepare outreach draft', _link('Draft outreach', 'good_agents:create_outreach_draft', pathway.pk)))
    elif outreach is None:
        ladder.append(('Create an action pathway before drafting outreach', _link('Create pathway', 'good_agents:opportunity_detail', opportunity.pk)))
    elif outreach.status in ('draft', 'ready_for_review'):
        ladder.append(('Approve outreach draft', _link('Approve', 'good_agents:outreach_approve', outreach.pk)))
    elif outreach.status == 'approved':
        ladder.append(('Send outreach', _link('Send', 'good_agents:outreach_send', outreach.pk)))
    elif outreach.status == 'sent' and routing_candidate is None:
        ladder.append(('Wait for response', None))
    elif routing_candidate is not None and routing_candidate.status in ('shared', 'no_response'):
        ladder.append(('Wait for partner response', None))
    elif room is not None and room.next_step_proposals.filter(status='proposed').exists():
        ladder.append(('Collect consent on proposed next step', _link('Open room', 'collaboration_rooms:room_detail', room.pk)))
    elif routing_candidate is not None and routing_candidate.status == 'interested' and room is None:
        ladder.append(('Open collaboration room', _link('Staff Collaboration Centre', 'collaboration_rooms:staff_centre')))
    elif project_candidate is None and routing_candidate is not None and routing_candidate.status == 'accepted_for_next_step':
        ladder.append(('Create project candidate', _link('Create', 'good_agents:project_candidate_propose', opportunity.pk)))
    elif project_candidate is not None and project_candidate.status == 'proposed':
        ladder.append(('Approve project candidate', _link('Approve', 'good_agents:project_candidate_approve', project_candidate.pk)))
    elif project_candidate is not None and project_candidate.status == 'approved':
        ladder.append(('Create real project', _link('Create', 'good_agents:project_candidate_create_confirm', project_candidate.pk)))
    elif project_candidate is not None and project_candidate.created_project_id and not project_candidate.created_project.timeline_milestones.exists():
        ladder.append(('Start execution (Capital Guardian)', _link('Capital Guardian', 'capital_guardian:directory')))
    elif project_candidate is not None and project_candidate.created_project_id and getattr(opportunity, 'impact_receipt', None) is None:
        ladder.append(('Collect baseline measurement / start MRV', _link('Capital Guardian', 'capital_guardian:directory')))
    else:
        ladder.append(('No further legitimate action currently identified.', None))

    primary_label, primary_link = ladder[0]
    primary = {'label': primary_label, 'link': primary_link}
    secondary = []
    if pathway is None and gate is not None and gate.current_state not in ('discovered',):
        secondary.append({'label': 'Create an action pathway', 'link': _link('Open', 'good_agents:opportunity_detail', opportunity.pk)})
    return {'primary': primary, 'secondary': secondary}


# --- 15/16. Capital snapshot --------------------------------------------------

def capital_snapshot(opportunity):
    """
    Reuses capital_guardian directly — no duplicate capital-decision logic
    (Phase 17). Reports what is genuinely known and marks the rest
    explicitly missing.
    """
    project_candidate = getattr(opportunity, 'project_candidate', None)
    project = project_candidate.created_project if project_candidate and project_candidate.created_project_id else None
    governance = getattr(project, 'governance', None) if project else None

    result = {
        'capital_required_usd': opportunity.capital_required_usd,
        'zero_capital_possible': opportunity.zero_capital_possible,
        'decision_state': 'No project exists yet.',
        'human_gate': 'Project Candidate approval (good_agents.project_bridge)',
        'missing_facts': [],
    }
    if project is not None:
        from capital_guardian.services.execution_monitoring import capital_summary
        result['decision_state'] = project.get_status_display()
        result['capital_summary'] = capital_summary(project)
        result['governance_active'] = governance is not None
        if opportunity.capital_required_usd is None:
            result['missing_facts'].append('capital_required_usd not recorded on the opportunity.')
    return result


# --- 19. MRV plan -------------------------------------------------------------

def mrv_plan(opportunity):
    """
    PLANNED / MEASURED / VERIFIED kept strictly separate (Phase 19) —
    never collapsed into one number. Reuses capital_guardian's real
    expected_vs_actual computation for the measured/verified side.
    """
    project_candidate = getattr(opportunity, 'project_candidate', None)
    project = project_candidate.created_project if project_candidate and project_candidate.created_project_id else None
    receipt = getattr(opportunity, 'impact_receipt', None)

    planned = {
        key: {'value': v.get('value'), 'unit': v.get('unit'), 'stage': v.get('stage', 'estimated')}
        for key, v in (opportunity.potential_benefit or {}).items()
    } if opportunity.potential_benefit else {}

    measured, verified = {}, {}
    if receipt is not None:
        measured = receipt.measured_result or {}
        verified = measured if opportunity.status == 'verified' else {}

    expected_vs_actual_ctx = None
    if project is not None:
        from capital_guardian.services.execution_monitoring import capital_decisions_for_project, expected_vs_actual
        decisions = list(capital_decisions_for_project(project))
        if decisions:
            expected_vs_actual_ctx = expected_vs_actual(decisions[0])

    return {
        'planned_metrics': planned,
        'measured_values': measured or 'No measured values recorded yet.',
        'verified_values': verified or 'IMPACT NOT YET VERIFIED',
        'expected_vs_actual': expected_vs_actual_ctx,
        'measurement_method': opportunity.scalability or 'Not recorded.',
    }


# --- 5. Truth chain provenance ------------------------------------------------

def truth_chain_with_provenance(opportunity):
    """
    Wraps mission_control.truth_chain() with one honest provenance label
    per node (Phase 5) — additive only, never changes an existing node's
    `reached`/`detail` meaning, so mission_control.html's existing usage
    of truth_chain() is unaffected.
    """
    from good_agents.services import mission_control
    nodes = mission_control.truth_chain(opportunity)
    provenance_by_stage = {
        'Signal': PROV_PUBLIC_SOURCE, 'Source': PROV_PUBLIC_SOURCE, 'Evidence': PROV_PUBLIC_SOURCE,
        'Principles activated': PROV_DETERMINISTIC, 'Opportunity': PROV_DETERMINISTIC,
        'Human review': PROV_HUMAN_APPROVED, 'Action pathway': PROV_HUMAN_APPROVED,
        'Responsible party': PROV_PUBLIC_SOURCE, 'Connection / outreach': PROV_HUMAN_APPROVED,
        'Project candidate': PROV_HUMAN_APPROVED, 'Project': PROV_HUMAN_APPROVED,
        'Execution': PROV_MEASURED, 'Outcome': PROV_MEASURED, 'Verification': PROV_VERIFIED,
        'Impact Receipt': PROV_VERIFIED, 'Evidence Memory': PROV_VERIFIED,
    }
    for node in nodes:
        if node['reached']:
            node['provenance'] = provenance_by_stage.get(node['stage'], PROV_DETERMINISTIC)
        else:
            node['provenance'] = PROV_NOT_YET_OCCURRED if node['stage'] in ('Execution', 'Outcome', 'Verification', 'Impact Receipt', 'Evidence Memory') else PROV_MISSING
    return nodes


# --- 25. Dossier --------------------------------------------------------------

def build_dossier(opportunity):
    """
    Assembles every section above into one exportable, deterministic
    dossier (Phase 25). Never generates invented prose for a missing
    field — missing stays literally "Missing".
    """
    responsible_party = opportunity.responsible_parties.order_by('-confidence').first()
    return {
        'opportunity': opportunity,
        'generated_at': timezone.now(),
        'problem': opportunity.problem_statement or 'Missing',
        'location': opportunity.region or (opportunity.geography.name if opportunity.geography_id else 'Missing'),
        'evidence_refs': opportunity.evidence_refs or [],
        'principle_relevance': principle_relevance(opportunity),
        'better_way_options': better_way_options(opportunity),
        'capability_graph_matches': capability_graph_matches(opportunity),
        'contact_route_state': contact_route_state(opportunity),
        'current_state': opportunity.get_status_display(),
        'blockers': blockers(opportunity),
        'next_best_action': next_best_action(opportunity),
        'measurement_plan': mrv_plan(opportunity),
        'readiness_scorecard': readiness_scorecard(opportunity),
        'governance_disclaimer': (
            'This dossier does not constitute a partnership, funding commitment, contract, or verified '
            'impact claim. Every field reflects the real, current state of EcoIQ\'s records — missing '
            'information is shown as Missing, never inferred.'
        ),
    }


# --- 15. Human Command Centre queues -----------------------------------------

def command_centre_queues(opportunities):
    """
    Actionable queues (Phase 15) — every row is a real opportunity in a
    real current state, never a vanity count. Scoped by the caller to a
    bounded, active set (see impact_action_centre view) since this
    recomputes blockers()/next_best_action() per opportunity.
    """
    needs_contact_route, waiting_on_external_party, needs_consent = [], [], []
    ready_for_project, needs_measurement, blocked_queue = [], [], []

    for opportunity in opportunities:
        opp_blockers = blockers(opportunity)
        codes = {b['code'] for b in opp_blockers}
        action = next_best_action(opportunity)

        if 'NO_VERIFIED_CONTACT_ROUTE' in codes:
            needs_contact_route.append(opportunity)
        if action['primary']['label'] in ('Wait for response', 'Wait for partner response'):
            waiting_on_external_party.append(opportunity)
        if 'CONSENT_PENDING' in codes:
            needs_consent.append(opportunity)
        if action['primary']['label'] == 'Create project candidate':
            ready_for_project.append(opportunity)
        if 'MRV_NOT_AVAILABLE' in codes:
            needs_measurement.append(opportunity)
        if opp_blockers:
            blocked_queue.append(opportunity)

    return {
        'needs_contact_route': needs_contact_route,
        'waiting_on_external_party': waiting_on_external_party,
        'needs_consent': needs_consent,
        'ready_for_project': ready_for_project,
        'needs_measurement': needs_measurement,
        'blocked': blocked_queue,
    }
