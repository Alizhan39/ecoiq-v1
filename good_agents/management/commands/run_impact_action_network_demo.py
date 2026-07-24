"""
run_impact_action_network_demo — PR5's "first real action demo" (Phase 29).

Two clearly-separated parts, printed with distinct banners:

PART A — REAL. Fetches live signals from the same real, bounded public
providers PR4 wired up (USGS, GOV.UK, UK Environment Agency), runs them
through the real GlobalGoodDiscoveryEngine, and — if anything qualifies —
shows the real ActionGate this repo now creates automatically for every
discovered opportunity (see discovery_engine.run_global_discovery), plus a
real, provenance-backed ResponsibleParty suggestion where a signal
publisher exists. This command NEVER calls action_gate.transition() on a
Part A opportunity: approving/rejecting a real discovered opportunity is a
human decision, not something a demo command may simulate. Part A stops
there and says so explicitly — "governed real-world follow-through, not
autonomous action" (PR5 brief) applies to real opportunities most of all.
Live signals rarely match this demo's few hand-tuned lenses (see PR4's own
report on this), so Part A commonly — and honestly — reports zero
qualifying opportunities today; that is not a failure of this command.

PART B — SIMULATED WALKTHROUGH. To actually demonstrate every downstream
governed step (approve -> pathway -> responsible party -> outreach draft
-> project candidate), this section runs the same walkthrough against a
clearly labelled demo opportunity ("[DEMO] ..." title throughout), with
every approval explicitly printed as "[SIMULATED APPROVAL] (demo command,
not a real human)". This mirrors the same convention
run_almaty_good_agent_demo.py already uses for its own auto-approved
CapitalAllocationDecision — nothing here claims a real human reviewed
anything in Part B, and it stops one step short of outreach send / project
creation, which stay behind a real approval even in this demo.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

from good_agents.models import ActionContact, ActionGate, GoodMission, GoodOpportunity, ResponsibleParty, WorldSignal
from good_agents.services import action_gate as action_gate_service
from good_agents.services import action_pathway as action_pathway_service
from good_agents.services import outreach as outreach_service
from good_agents.services import project_bridge
from good_agents.services import responsible_party as responsible_party_service
from good_agents.services.discovery_engine import run_global_discovery
from good_agents.services.ingestion import fetch_due_signals


class Command(BaseCommand):
    help = "PR5 Phase 29 — real action demo: real signals through the governed Action Gate, plus a labelled simulated walkthrough of the rest of the pipeline."

    def handle(self, *args, **options):
        call_command('seed_signal_providers')
        call_command('seed_all_good_agent_definitions')

        self._run_part_a_real()
        self._run_part_b_simulated_walkthrough()

    def _run_part_a_real(self):
        self.stdout.write(self.style.WARNING('\n=== PART A — REAL: live public signals, real Action Gate, no simulated approval ===\n'))
        raw_signals, provider_reports = fetch_due_signals()
        for report in provider_reports:
            status = 'OK' if report['success'] else f"FAILED ({report['error']})"
            self.stdout.write(f"  - {report['name']}: {status} — {report['items_after_validation']} real signal(s) after validation")
        self.stdout.write(f'Fetched {len(raw_signals)} real raw signal(s) total.\n')

        mission, _ = GoodMission.objects.get_or_create(
            name='Global Real-Time Signal Monitoring (Live Public Sources)',
            defaults=dict(run_cost_budget_usd=5.0, min_confidence=30.0, max_opportunities=5, enabled=True),
        )
        run, brief = run_global_discovery(mission, raw_signals, idempotency_key='impact-action-network-demo')

        if not brief['problems_detected']:
            self.stdout.write(self.style.WARNING(
                "No real opportunity qualified from today's live signals — reported honestly, not padded. "
                "(Live earthquake/grant/flood feeds rarely match this repo's hand-tuned lenses; this is the "
                'expected common case, not an error — see PR4\'s own report.)'
            ))
            return

        for opp_summary in brief['problems_detected']:
            opportunity = GoodOpportunity.objects.get(pk=opp_summary['id'])
            gate = ActionGate.objects.get(opportunity=opportunity)
            self.stdout.write(f'REAL opportunity #{opportunity.pk}: "{opportunity.title}"')
            self.stdout.write(f'  ActionGate state: {gate.current_state} (created automatically on discovery — see ActionGateTransition history)')

            suggested = 0
            for signal in WorldSignal.objects.filter(title__in=opportunity.detected_signals):
                party = responsible_party_service.suggest_from_signal(opportunity, signal)
                if party:
                    suggested += 1
                    self.stdout.write(f'  Suggested responsible party: {party.name} ({party.get_resolution_status_display()}) — {party.evidence_ref}')
            if not suggested:
                self.stdout.write('  No responsible party could be suggested (no signal publisher on record) — reported honestly.')

            self.stdout.write(self.style.WARNING(
                '  STOPPING HERE for this real opportunity: approving it into an action pathway, drafting outreach, '
                'or proposing a project requires a real human decision via the Impact Action Centre / opportunity '
                'detail page. This command will not simulate that decision for a real opportunity.\n'
            ))

    def _run_part_b_simulated_walkthrough(self):
        self.stdout.write(self.style.WARNING('=== PART B — SIMULATED WALKTHROUGH (demo data, every approval labelled) ===\n'))

        demo_opportunity, _ = GoodOpportunity.objects.get_or_create(
            title='[DEMO] Rural households need help paying for winter heating upgrades',
            defaults=dict(
                problem_statement='Demo fixture problem statement — not a real household survey.',
                theme='energy', sector='heating', region='Demo Region', confidence=65.0, urgency=70.0,
                zero_capital_possible=True,
            ),
        )

        gate = action_gate_service.get_or_create_gate(demo_opportunity)
        if gate.current_state == 'discovered':
            gate = action_gate_service.transition(demo_opportunity, 'needs_review', reason='[SIMULATED APPROVAL] Demo command triage.')
        if gate.current_state == 'needs_review':
            gate = action_gate_service.transition(demo_opportunity, 'approved_for_contact', reason='[SIMULATED APPROVAL] Demo command — not a real human.')
        self.stdout.write(f'DEMO opportunity #{demo_opportunity.pk} gate: {gate.current_state} [SIMULATED APPROVAL]')

        pathway = demo_opportunity.action_pathways.filter(pathway_type='introduction').first() or action_pathway_service.create_pathway(
            demo_opportunity, 'introduction', rationale='[DEMO] Connect to a local energy-efficiency NGO.',
        )
        self.stdout.write(f'  Action pathway: {pathway.get_pathway_type_display()} (capital_required={pathway.capital_required})')

        party, _ = ResponsibleParty.objects.get_or_create(
            opportunity=demo_opportunity, name='[DEMO] Local Energy Efficiency NGO', party_type='ngo',
        )
        self.stdout.write(f'  Responsible party (demo): {party.name} — {party.get_resolution_status_display()}')

        contact, _ = ActionContact.objects.get_or_create(
            responsible_party=party, contact_role='General enquiries',
            defaults=dict(public_contact_channel='demo-contact@example-ngo.org', source_of_contact_info='[DEMO] Published NGO contact page.'),
        )
        draft = pathway.outreach_drafts.first() or outreach_service.create_draft(
            pathway, 'introduction_request', contact=contact,
            subject='[DEMO] Introduction request', body='[DEMO] This is demo outreach body text, never actually sent to a real recipient.',
        )
        if draft.status == 'draft':
            draft = outreach_service.mark_ready_for_review(draft)
        self.stdout.write(f'  Outreach draft: {draft.get_draft_type_display()} [{draft.status}] — awaiting approval (not auto-approved, even in this demo)')

        project_candidate = project_bridge.propose_candidate(demo_opportunity, rationale='[DEMO] Warrants a pilot.')
        self.stdout.write(f'  Project candidate: {project_candidate.get_status_display()} [SIMULATED — not approved by this command]')

        self.stdout.write(self.style.WARNING(
            '\nPART B STOPPING HERE: the outreach draft is intentionally left at "ready_for_review" and the project '
            'candidate at "proposed" — this command does not simulate the human approval that would move either one '
            'further, even for demo data. Real approval flows only through the Impact Action Centre UI.'
        ))
