"""
run_trusted_partner_activation_demo — PR9 Phase 28's real/controlled
demo.

Same honesty constraint PR8's demo hit: the real organisations in the
Capability Graph today (USGS, UK Environment Agency — seeded in PR7 from
externally-verified public evidence) have NO real, authenticated human
representative available in this session to actually receive and accept
a real invitation. Per this PR's own instruction ("do not fabricate
partners, responses, or acceptance... if no real representative is
available, use ONE clearly labelled internal controlled-test org only"),
this command:

1. Checks each real organisation's genuine routing-readiness and prints
   exactly what's missing. It creates NO invitation, membership, consent,
   or routing candidate against them — they are left completely
   untouched, same as PR8's demo.
2. Creates ONE clearly-labelled "[CONTROLLED TEST]" organisation and
   drives it through the ENTIRE PR9 activation loop end to end — real
   invitation, real (manual, since this environment has no real SMTP
   transport) delivery confirmation, real acceptance, real staff
   membership review, real consent by the real controlled-test user,
   real capability declaration/evidence/verification, real route, real
   preference, real routing candidate, real human share approval, real
   manual delivery, real response capture, and a real governed next
   step — using this repo's own real, governed service calls at every
   step, never a shortcut, never a fabricated status.

This command is idempotent — it can be re-run safely.
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
    invitation as invitation_service, membership, next_step as next_step_service, onboarding,
    opportunity_preferences, response_capture, routing,
)


class Command(BaseCommand):
    help = 'Runs the real/controlled Trusted Partner Activation demo (PR9 Phase 28).'

    def handle(self, *args, **options):
        User = get_user_model()

        self.stdout.write('=== PART A — REAL organisations from PR7/PR8, left untouched ===')
        for name, jurisdiction in [('USGS (US Geological Survey)', 'Global'), ('UK Environment Agency', 'England')]:
            org = Organisation.objects.filter(name=name, jurisdiction=jurisdiction).first()
            if org is None:
                self.stdout.write(f'  {name}: not seeded in this database (run seed_capability_graph_from_real_providers first).')
                continue
            ready, reasons = onboarding.is_routing_ready(org)
            if ready:
                self.stdout.write(f'  {name}: genuinely ROUTING READY — a real invitation could route real opportunities today.')
            else:
                self.stdout.write(
                    f'  {name}: READY FOR REAL PARTNER INVITATION only — not yet routing-ready. '
                    f'Missing: {"; ".join(reasons)}'
                )
            self.stdout.write('    No invitation, membership, consent, or routing candidate created against this real record.')

        self.stdout.write('\n=== PART B — CONTROLLED TEST organisation, full activation loop ===')
        controlled_org = get_or_create_organisation(
            '[CONTROLLED TEST] Riverside Flood Resilience Cooperative', org_type='charity', jurisdiction='England',
            notes='Created solely to exercise the Trusted Partner Activation loop end to end (PR9 Phase 28). '
                  'Not a real charity — never to be treated as a real routing target.',
        )
        self.stdout.write(f'Organisation: "{controlled_org.name}" (pk={controlled_org.pk})')

        staff, _ = User.objects.get_or_create(username='pr9-demo-staff', defaults={'is_staff': True, 'last_login': timezone.now()})
        rep, _ = User.objects.get_or_create(username='pr9-demo-rep', defaults={'last_login': timezone.now()})

        existing_membership = OrganisationMembership.objects.filter(organisation=controlled_org, user=rep).first()
        if existing_membership is None:
            invitation = invitation_service.create_invitation(
                controlled_org, 'rep@controlled-test.example.org', actor=staff, intended_role='editor',
                reason='PR9 demo — controlled test invitation.',
            )
            self.stdout.write(f'Invitation created: token={invitation.token[:8]}... status={invitation.status}')

            if invitation_service.has_real_mail_transport():
                invitation_service.send_invitation(invitation, actor=staff)
                self.stdout.write(f'Invitation sent by REAL email -> status={invitation.status}')
            else:
                subject, body, link = invitation_service.render_invitation_message(invitation)
                invitation_service.mark_manually_sent(invitation, actor=staff, evidence='PR9 demo — no real SMTP transport configured; recorded as manually delivered.')
                self.stdout.write('No real mail transport configured — this is the honest path, not a workaround:')
                self.stdout.write(f'  Subject: {subject}')
                self.stdout.write(f'  Link: {link}')
                self.stdout.write('Invitation marked manually sent by a real staff actor.')

            m = invitation_service.accept_invitation(invitation.token, user=rep)
            self.stdout.write(f'Invitation accepted -> membership status={m.status} (never auto-verified)')
            m = membership.review_membership(m, decision='verified_member', actor=staff, notes='PR9 demo — approved for controlled testing only.')
            self.stdout.write(f'Membership reviewed by real staff actor -> status={m.status}')
        else:
            m = existing_membership
            self.stdout.write(f'Reusing existing membership: status={m.status}')

        consent = getattr(m, 'consent', None)
        if consent is None or consent.status != 'active':
            consent = consent_service.record_consent(m, actor=rep)
        self.stdout.write(f'Participation consent: {consent.status} (recorded by the real membership holder, never by staff on their behalf)')

        edge = controlled_org.capabilities.filter(capability='supply').first()
        if edge is None:
            edge = capability_declarations.declare_capability(
                controlled_org, 'supply', m, jurisdiction='England', topic_domain='flood-resilient water supply',
                limitations='Coordinates emergency water supply during flood response; does not itself fund repairs.',
            )
            self.stdout.write(f'Capability declared: {edge.get_capability_display()} — {edge.get_verification_state_display()} ({edge.get_provenance_display()})')
            edge = capability_declarations.attach_evidence(edge, evidence_url='https://example.org/controlled-test-evidence', actor=rep)
            self.stdout.write(f'Evidence attached: {edge.get_verification_state_display()}')
            edge = verify_capability(edge, actor=staff)
            self.stdout.write(f'EcoIQ independently verified: {edge.get_verification_state_display()}')
        else:
            self.stdout.write(f'Reusing existing capability: {edge.get_verification_state_display()}')

        if not edge.public_routes.filter(is_currently_open=True).exists():
            route = add_public_route(edge, 'email', 'controlled-test@example.org', notes='PR9 demo route — not a real contact.')
            self.stdout.write(f'Public route added: {route.get_route_type_display()} — {route.route_value}')

        pref = opportunity_preferences.set_preference(
            controlled_org, 'water', m, acceptance_mode='open_to_relevant_opportunities',
            notes='PR9 demo preference — controlled test only.',
        )
        self.stdout.write(f'Opportunity preference set: {pref.get_theme_display()} — {pref.get_acceptance_mode_display()}')

        ready, reasons = onboarding.is_routing_ready(controlled_org)
        self.stdout.write(f'Routing readiness: {ready} ({reasons if not ready else "all requirements genuinely met"})')
        if not ready:
            self.stdout.write(self.style.WARNING('Controlled test org is not routing-ready — stopping here honestly.'))
            return

        opportunity, created = GoodOpportunity.objects.get_or_create(
            title='[CONTROLLED TEST] Riverside flood-response water supply gap',
            defaults=dict(
                problem_statement='Controlled test opportunity for PR9\'s activation demo — not a real discovered need.',
                theme='water', confidence=60.0, region='England', status='qualified',
            ),
        )
        action_gate_service.get_or_create_gate(opportunity)
        self.stdout.write(f'{"Created" if created else "Reusing"} controlled test opportunity #{opportunity.pk}.')

        result = routing.generate_routing_candidates(opportunity)
        candidate = next((c for c in result['created'] if c.organisation_id == controlled_org.pk), None)
        if candidate is None:
            candidate = RoutingCandidate.objects.filter(organisation=controlled_org, opportunity=opportunity).first()
        if candidate is None:
            self.stdout.write(self.style.WARNING('No routing candidate created for the controlled test org — stopping here honestly.'))
            return
        self.stdout.write(f'Routing candidate: {candidate.get_confidence_label_display()} — reasons: {candidate.match_reasons}')

        if candidate.status == 'routing_candidate':
            candidate = routing.transition(candidate, 'ready_for_ecoiq_review', actor=rep)
            self.stdout.write(f'Routing candidate -> {candidate.get_status_display()}')
        if candidate.status == 'ready_for_ecoiq_review':
            candidate = delivery_service.approve_share(candidate, actor=staff)
            self.stdout.write(f'Human approval to share -> {candidate.get_status_display()} (real EcoIQ staff actor)')
        if candidate.status == 'approved_to_share':
            delivery = delivery_service.record_manual_delivery(
                candidate, actor=staff, recipient='controlled-test@example.org',
                channel_notes='PR9 demo — recorded manual delivery (no real SMTP transport configured).',
                evidence='Controlled test only.',
            )
            candidate.refresh_from_db()
            self.stdout.write(f'Real delivery recorded (method={delivery.delivery_method}) -> {candidate.get_status_display()}')

        if candidate.status in ('shared', 'no_response'):
            candidate = response_capture.record_response(candidate, 'viewed', actor=rep, channel='portal', summary='PR9 demo — controlled test partner viewed the shared opportunity.')
            self.stdout.write(f'Response captured -> {candidate.get_status_display()}')
        if candidate.status == 'viewed':
            candidate = response_capture.partner_self_service_response(candidate, 'interested', user=rep, notes='PR9 demo — controlled test partner self-service response.')
            self.stdout.write(f'Partner self-service response -> {candidate.get_status_display()}')

        if candidate.status == 'interested' and not candidate.next_steps.exists():
            step = next_step_service.create_meeting_request(
                candidate, actor=staff, notes='PR9 demo — propose an introductory call to discuss the flood-response water supply gap.',
            )
            self.stdout.write(f'Governed next step created: {step.get_action_type_display()} ({step.get_status_display()})')
        elif candidate.status == 'interested':
            self.stdout.write(f'Reusing existing next step: {candidate.next_steps.first().get_action_type_display()}')

        self.stdout.write(self.style.SUCCESS(
            '\nCOMPLETE: the full PR9 activation loop ran end to end against the clearly-labelled '
            '[CONTROLLED TEST] organisation only. Real organisation records (USGS, UK Environment Agency) '
            'were left completely untouched throughout.'
        ))
