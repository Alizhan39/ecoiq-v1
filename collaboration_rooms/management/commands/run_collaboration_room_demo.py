"""
run_collaboration_room_demo — PR10 Phase 36's real/controlled demo.

Same honesty constraint every PR in this lineage has hit: no real,
independent external organisation representative was available in this
session to exercise a genuine two-organisation collaboration. Per this
PR's own instruction ("use controlled organisations for technical
verification unless real external representatives are genuinely
available... stop before pretending any external real-world
commitment"), this command drives the FULL PR10 loop using TWO clearly-
labelled "[CONTROLLED TEST]" organisations (so the mutual-consent matrix
is genuinely exercised across two real party rows, not faked as one),
while leaving any real Capability Graph organisation completely untouched.

Idempotent — safe to re-run.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from capability_graph.models import Organisation
from capability_graph.services.capabilities import verify_capability
from capability_graph.services.organisations import get_or_create_organisation
from capability_graph.services.routes import add_public_route
from good_agents.models import GoodOpportunity
from good_agents.services import action_gate as action_gate_service
from partner_participation.models import OrganisationMembership, RoutingCandidate
from partner_participation.services import (
    capability_declarations, consent as consent_service, delivery as delivery_service,
    onboarding, opportunity_preferences, response_capture, routing,
)

from collaboration_rooms.services import (
    evidence as evidence_service, promotion, proposals as proposals_service, questions, rooms as rooms_service,
)


class Command(BaseCommand):
    help = 'Runs the real/controlled Governed Collaboration Room demo (PR10 Phase 36).'

    def _make_ready_org(self, name, staff, rep):
        org = get_or_create_organisation(
            name, org_type='charity', jurisdiction='England',
            notes='Created solely to exercise the Governed Collaboration Room loop end to end (PR10 Phase 36). Not real.',
        )
        m = OrganisationMembership.objects.filter(organisation=org, user=rep).first()
        if m is None:
            from partner_participation.services import membership as membership_service
            m = membership_service.request_membership(org, rep, role='editor', justification='PR10 demo.')
            m = membership_service.review_membership(m, decision='verified_member', actor=staff)
        consent = getattr(m, 'consent', None)
        if consent is None or consent.status != 'active':
            consent_service.record_consent(m, actor=rep)
        edge = org.capabilities.filter(capability='supply').first()
        if edge is None:
            edge = capability_declarations.declare_capability(org, 'supply', m, jurisdiction='England', topic_domain='flood-resilient water supply')
            edge = capability_declarations.attach_evidence(edge, evidence_url='https://example.org/x', actor=rep)
            edge = verify_capability(edge, actor=staff)
        if not edge.public_routes.filter(is_currently_open=True).exists():
            add_public_route(edge, 'email', f'{org.pk}-controlled-test@example.org')
        opportunity_preferences.set_preference(org, 'water', m, acceptance_mode='open_to_relevant_opportunities')
        return org, m

    def handle(self, *args, **options):
        User = get_user_model()

        self.stdout.write('=== PART A — REAL organisations from Capability Graph, left untouched ===')
        for name, jurisdiction in [('USGS (US Geological Survey)', 'Global'), ('UK Environment Agency', 'England')]:
            org = Organisation.objects.filter(name=name, jurisdiction=jurisdiction).first()
            if org is None:
                self.stdout.write(f'  {name}: not seeded in this database.')
                continue
            has_room = RoutingCandidate.objects.filter(organisation=org, collaboration_room__isnull=False).exists()
            self.stdout.write(f'  {name}: collaboration room exists = {has_room}. No room created against this real record by this command.')

        self.stdout.write('\n=== PART B — TWO controlled organisations, full collaboration loop ===')
        staff, _ = User.objects.get_or_create(username='pr10-demo-staff', defaults={'is_staff': True, 'last_login': timezone.now()})
        rep_a, _ = User.objects.get_or_create(username='pr10-demo-rep-a', defaults={'last_login': timezone.now()})
        rep_b, _ = User.objects.get_or_create(username='pr10-demo-rep-b', defaults={'last_login': timezone.now()})

        org_a, m_a = self._make_ready_org('[CONTROLLED TEST] Riverside Flood Cooperative A', staff, rep_a)
        org_b, m_b = self._make_ready_org('[CONTROLLED TEST] Riverside Flood Cooperative B', staff, rep_b)
        self.stdout.write(f'Organisation A: "{org_a.name}" (pk={org_a.pk}) — routing ready: {onboarding.is_routing_ready(org_a)[0]}')
        self.stdout.write(f'Organisation B: "{org_b.name}" (pk={org_b.pk}) — routing ready: {onboarding.is_routing_ready(org_b)[0]}')

        opportunity, created = GoodOpportunity.objects.get_or_create(
            title='[CONTROLLED TEST] PR10 flood-response coordination need',
            defaults=dict(problem_statement='Controlled test opportunity for PR10\'s collaboration room demo.', theme='water', confidence=60.0, region='England', status='qualified'),
        )
        action_gate_service.get_or_create_gate(opportunity)
        self.stdout.write(f'{"Created" if created else "Reusing"} controlled test opportunity #{opportunity.pk}.')

        result = routing.generate_routing_candidates(opportunity)
        candidate_a = next((c for c in result['created'] if c.organisation_id == org_a.pk), None) or RoutingCandidate.objects.filter(organisation=org_a, opportunity=opportunity).first()
        if candidate_a is None:
            self.stdout.write(self.style.WARNING('No routing candidate for Organisation A — stopping honestly.'))
            return
        self.stdout.write(f'Routing candidate (Org A): {candidate_a.get_confidence_label_display()}')

        if candidate_a.status == 'routing_candidate':
            routing.transition(candidate_a, 'ready_for_ecoiq_review', actor=rep_a)
        if candidate_a.status == 'ready_for_ecoiq_review':
            delivery_service.approve_share(candidate_a, actor=staff)
        candidate_a.refresh_from_db()
        if candidate_a.status == 'approved_to_share':
            delivery_service.record_manual_delivery(candidate_a, actor=staff, recipient='controlled-test@example.org', channel_notes='PR10 demo manual delivery.')
        candidate_a.refresh_from_db()
        if candidate_a.status in ('shared', 'no_response'):
            response_capture.record_response(candidate_a, 'viewed', actor=staff)
        candidate_a.refresh_from_db()
        if candidate_a.status == 'viewed':
            response_capture.record_response(candidate_a, 'interested', actor=rep_a, channel='portal', summary='PR10 demo — Organisation A interested.')
        candidate_a.refresh_from_db()
        self.stdout.write(f'Organisation A routing candidate status: {candidate_a.get_status_display()}')

        room = rooms_service.create_room(candidate_a, actor=staff, title='[CONTROLLED TEST] Flood-response coordination room')
        self.stdout.write(f'Collaboration room #{room.pk}: {room.get_status_display()} (participants: {room.participants.filter(revoked_at__isnull=True).count()})')

        # Bring in Organisation B as a second real party — staff explicitly adds it, with a stated reason.
        if not room.participants.filter(user=rep_b, revoked_at__isnull=True).exists():
            rooms_service.add_participant(
                room, user=rep_b, organisation=org_b, role='organisation_representative',
                reason='PR10 demo — Organisation B is the proposed introduction counterpart.', actor=staff,
            )
        self.stdout.write('Organisation B added to room as a real second party.')

        item = room.evidence_items.filter(title='Emergency water supply capacity').first()
        if item is None:
            item = evidence_service.share_evidence(
                room, shared_by=rep_a, title='Emergency water supply capacity', description='We can supply up to 200 units/week during flood response.',
                evidence_type='resource_information',
            )
        self.stdout.write(f'Evidence shared by Org A: "{item.title}" — {item.get_verification_state_display()} (a declared claim, not yet verified)')

        req = room.information_requests.filter(request_type='technical_specification').first()
        if req is None:
            req = questions.create_request(room, requested_by=staff, question_text='Can Organisation B confirm technical compatibility with Organisation A\'s supply format?', request_type='technical_specification')
            response = questions.record_response(req, responded_by=rep_b, answer_text='Yes, compatible with our standard fittings.')
            self.stdout.write(f'Response recorded by Org B (claim only: {response.is_claim_only})')
            questions.set_status(req, 'answered', actor=staff)
        self.stdout.write(f'Information request: "{req.question_text}" — {req.get_status_display()}')

        proposal = None
        for p in room.next_step_proposals.filter(proposal_type='introduction'):
            proposal = p
        if proposal is None:
            proposal = proposals_service.create_proposal(
                room, proposed_by=staff, proposal_type='introduction',
                description='Introduce Organisation A and Organisation B for a direct flood-response supply arrangement.',
                required_organisations=[org_a, org_b], requires_ecoiq_consent=True,
            )
            proposals_service.propose(proposal, actor=staff)
        self.stdout.write(f'Next-step proposal: {proposal.get_proposal_type_display()} — {proposal.get_status_display()}')

        if proposal.status == 'proposed':
            proposals_service.give_consent(proposal, actor=staff, organisation=None, notes='EcoIQ coordinator consents.')
            proposals_service.give_consent(proposal, actor=rep_a, organisation=org_a, notes='Organisation A consents.')
            proposals_service.give_consent(proposal, actor=rep_b, organisation=org_b, notes='Organisation B consents.')
        proposal.refresh_from_db()
        self.stdout.write(f'Consent matrix: {[(c.organisation.name if c.organisation_id else "EcoIQ", c.get_status_display()) for c in proposal.consents.all()]}')
        self.stdout.write(f'Proposal status after all required consents: {proposal.get_status_display()}')

        if proposal.status == 'accepted':
            result = promotion.promote_proposal(proposal, actor=staff)
            room.refresh_from_db()
            self.stdout.write(self.style.SUCCESS(
                f'Promoted to a real governed record: {result} (room status now: {room.get_status_display()}).'
            ))
        elif proposal.status == 'completed':
            self.stdout.write(f'Already promoted on an earlier run: {proposal.promoted_reference}')
        else:
            self.stdout.write(self.style.WARNING('Consensus not yet reached — stopping honestly before promotion.'))
            return

        self.stdout.write(self.style.SUCCESS(
            '\nCOMPLETE: the full PR10 governed collaboration loop ran end to end against two clearly-labelled '
            '[CONTROLLED TEST] organisations only. Real Capability Graph organisation records were left completely untouched.'
        ))
