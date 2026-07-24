"""
run_partner_participation_demo — PR8 Phase 32's real/controlled demo.

The real organisations in the Capability Graph today (USGS, UK
Environment Agency — seeded in PR7 from externally-verified public
evidence) have NO real authenticated representative available in this
session. Per the brief's own instruction ("If no real organisation
representative is available: do NOT fake organisation participation...
keep the real organisation record separate"), this command:

1. Leaves USGS/UK Environment Agency completely untouched — prints their
   real, PR7-only state (discovered/verified capability, zero
   participation) as a contrast.
2. Creates ONE clearly-labelled "[CONTROLLED TEST]" organisation and a
   real Django user to walk the full participation workflow end to end,
   using this repo's own real, governed service calls at every step —
   never a shortcut, never a fabricated status.

Stops at "shared" (human sharing approval) — the furthest EcoIQ-side
action this command can honestly execute. It never simulates the
organisation itself expressing interest, since that is the other party's
real-world response, not EcoIQ's to fabricate (Phase 32: "stop before
external acceptance unless real").
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
from partner_participation.services import capability_declarations, membership, opportunity_preferences, routing


class Command(BaseCommand):
    help = 'Runs the real/controlled Partner Participation Protocol demo (PR8 Phase 32).'

    def handle(self, *args, **options):
        User = get_user_model()

        self.stdout.write('=== PART A — REAL organisations from PR7, left untouched ===')
        for name, jurisdiction in [('USGS (US Geological Survey)', 'Global'), ('UK Environment Agency', 'England')]:
            org = Organisation.objects.filter(name=name, jurisdiction=jurisdiction).first()
            if org is None:
                self.stdout.write(f'  {name}: not seeded in this database (run seed_capability_graph_from_real_providers first).')
                continue
            member_count = org.memberships.count()
            verified_caps = org.capabilities.filter(verification_state='independently_verified').count()
            self.stdout.write(
                f'  {name}: {org.capabilities.count()} capabilit(y/ies) recorded, {verified_caps} independently verified, '
                f'{member_count} membership row(s) — REAL, externally-discovered only, no participation claimed on its behalf.'
            )

        self.stdout.write('\n=== PART B — CONTROLLED TEST organisation, full participation workflow ===')
        controlled_org = get_or_create_organisation(
            '[CONTROLLED TEST] Community Energy Poverty Trust', org_type='charity', jurisdiction='England',
            notes='Created solely to exercise the Partner Participation Protocol end to end (PR8 Phase 32). '
                  'Not a real charity — never to be treated as a real routing target.',
        )
        self.stdout.write(f'Organisation: "{controlled_org.name}" (pk={controlled_org.pk})')

        staff, _ = User.objects.get_or_create(
            username='pr8-demo-staff', defaults={'is_staff': True, 'last_login': timezone.now()},
        )
        member_user, _ = User.objects.get_or_create(
            username='pr8-demo-member', defaults={'last_login': timezone.now()},
        )

        from partner_participation.models import OrganisationMembership
        m = OrganisationMembership.objects.filter(organisation=controlled_org, user=member_user).first()
        if m is None:
            m = membership.request_membership(controlled_org, member_user, role='editor', justification='PR8 demo — controlled test member.')
            self.stdout.write(f'Membership requested: status={m.status}')
            m = membership.review_membership(m, decision='verified_member', actor=staff, notes='PR8 demo — approved for controlled testing only.')
            self.stdout.write(f'Membership reviewed by real staff actor: status={m.status}')
        else:
            self.stdout.write(f'Reusing existing membership: status={m.status}')

        # 'coordinate' is required by the 'poverty' theme's real deterministic
        # mapping (see capability_graph.services.needs.REQUIRED_CAPABILITIES_BY_THEME)
        # — chosen to match, not invented, so the routing engine below has a
        # genuine capability/theme fit to find rather than a contrived one.
        edge = capability_declarations.declare_capability(
            controlled_org, 'coordinate', m, jurisdiction='England', topic_domain='energy poverty',
            limitations='Coordinates referrals to real energy-poverty support schemes; does not itself provide funding.',
        )
        self.stdout.write(f'Capability declared: {edge.get_capability_display()} — {edge.get_verification_state_display()} ({edge.get_provenance_display()})')

        edge = capability_declarations.attach_evidence(edge, evidence_url='https://example.org/controlled-test-evidence', actor=member_user)
        self.stdout.write(f'Evidence attached: {edge.get_verification_state_display()}')

        edge = capability_declarations.human_review(edge, actor=staff, notes='PR8 demo — reviewed for controlled testing only.')
        self.stdout.write(f'EcoIQ human review: {edge.get_verification_state_display()} (never auto-promoted to independently_verified)')

        pref = opportunity_preferences.set_preference(
            controlled_org, 'poverty', m, acceptance_mode='open_to_relevant_opportunities',
            notes='PR8 demo preference — controlled test only.',
        )
        self.stdout.write(f'Opportunity preference set: {pref.get_theme_display()} — {pref.get_acceptance_mode_display()}')

        route = add_public_route(edge, 'email', 'controlled-test@example.org', notes='PR8 demo route — not a real contact.')
        self.stdout.write(f'Public route added: {route.get_route_type_display()} — {route.route_value}')

        opportunity, created = GoodOpportunity.objects.get_or_create(
            title='[CONTROLLED TEST] Rural household energy poverty referral need',
            defaults=dict(
                problem_statement='Controlled test opportunity for PR8\'s routing engine demo — not a real discovered need.',
                theme='poverty', confidence=60.0, region='England', status='qualified',
            ),
        )
        action_gate_service.get_or_create_gate(opportunity)
        self.stdout.write(f'{"Created" if created else "Reusing"} controlled test opportunity #{opportunity.pk}.')

        result = routing.generate_routing_candidates(opportunity)
        self.stdout.write(
            f'Routing candidates created: {len(result["created"])} '
            f'({[c.organisation.name for c in result["created"]]}), skipped: {len(result["skipped"])}'
        )
        candidate = next((c for c in result['created'] if c.organisation_id == controlled_org.pk), None)
        if candidate is None:
            # May already exist from an earlier run of this same idempotent command.
            from partner_participation.models import RoutingCandidate
            candidate = RoutingCandidate.objects.filter(organisation=controlled_org, opportunity=opportunity).first()
        if candidate is None:
            self.stdout.write(self.style.WARNING('No routing candidate created for the controlled test org — stopping here honestly.'))
            return
        self.stdout.write(f'Routing candidate (controlled test org): {candidate.get_confidence_label_display()} — reasons: {candidate.match_reasons}')

        candidate = routing.transition(candidate, 'ready_for_ecoiq_review', actor=member_user)
        self.stdout.write(f'Routing candidate -> {candidate.get_status_display()}')
        candidate = routing.transition(candidate, 'approved_to_share', actor=staff)
        self.stdout.write(f'Routing candidate -> {candidate.get_status_display()} (real EcoIQ staff actor)')
        candidate = routing.transition(candidate, 'shared', actor=staff)
        self.stdout.write(f'Routing candidate -> {candidate.get_status_display()} (real EcoIQ staff actor)')

        self.stdout.write(self.style.SUCCESS(
            '\nSTOPPING HERE: this is the furthest EcoIQ-side action this command can honestly execute. '
            'It does not simulate the organisation itself expressing interest ("viewed"/"interested"/'
            '"accepted_for_next_step") — that is the other party\'s real-world response, never EcoIQ\'s to fabricate.'
        ))
