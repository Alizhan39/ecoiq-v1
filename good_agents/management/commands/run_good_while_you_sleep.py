"""
run_good_while_you_sleep — the real, scheduled-ready overnight discovery
loop (PR4 Phase 14, and Phase 19's "first real Good While You Sleep demo").

    SignalProvider (real, live) -> fetch_due_signals -> GlobalGoodDiscoveryEngine
    -> qualified opportunities / matched resources / zero-capital actions
    -> notifications -> Morning Brief

Idempotent per (mission, run-date): re-running the same day returns the
already-completed run for each mission rather than reprocessing. Bounded:
each mission has its own cost_budget_usd/max_opportunities. Failure-isolated
per provider (see services/ingestion.py) — one provider failing (timeout,
malformed response, blocked by the SSRF allowlist) never stops the others
or the missions from running.

This is SCHEDULER READY, not SCHEDULER ACTIVE — see render.yaml for the
disabled-by-default cron block and docs/GOOD_WHILE_YOU_SLEEP.md for what
that distinction means. Running this command manually (or via your own
external scheduler) is fully supported today; nothing claims a production
cron is actually ticking unless that render.yaml block is uncommented.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from good_agents.models import GoodMission
from good_agents.services import notify
from good_agents.services.discovery_engine import run_global_discovery
from good_agents.services.ingestion import fetch_due_signals


class Command(BaseCommand):
    help = 'Real overnight discovery: fetches live public signals, runs every enabled GoodMission, prints the Morning Brief.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mission', action='append', dest='mission_names', default=None,
            help='Run only this GoodMission name (repeatable). Defaults to every enabled mission.',
        )
        parser.add_argument(
            '--include-dogfood', action='store_true',
            help='Also run the (disabled-by-default) EcoIQ Dogfood mission against this same real signal batch.',
        )

    def handle(self, *args, **options):
        call_command('seed_signal_providers')
        # Real-world signals (earthquakes, UK grants, flood warnings) rarely
        # match the 6 lenses hand-tuned for the Almaty heating fixture — seed
        # all 114 so a genuinely relevant principle has a chance to activate.
        call_command('seed_all_good_agent_definitions')

        mission_names = options.get('mission_names')
        missions = GoodMission.objects.filter(enabled=True)
        if mission_names:
            missions = GoodMission.objects.filter(name__in=mission_names)
        elif options.get('include_dogfood'):
            missions = GoodMission.objects.filter(enabled=True) | GoodMission.objects.filter(
                name='EcoIQ Dogfood — 30 Days, Minimal Capital',
            )
        missions = list(missions.distinct())

        if not missions:
            self.stdout.write(self.style.WARNING(
                'No enabled GoodMission found — nothing to run. '
                'Seed one, e.g.: GoodMission.objects.create(name=..., enabled=True).'
            ))
            return

        raw_signals, provider_reports = fetch_due_signals()
        self.stdout.write(f'Fetched {len(raw_signals)} raw signal(s) from {len(provider_reports)} provider(s):')
        for report in provider_reports:
            status = 'OK' if report['success'] else f'FAILED ({report["error"]})'
            self.stdout.write(f'  - {report["name"]}: {status} — {report["items_after_validation"]} signal(s) after validation')
        if not any(r['success'] for r in provider_reports):
            self.stdout.write(self.style.WARNING('All providers failed this run — continuing with 0 signals (failure-isolated, not fatal).'))

        run_date = timezone.now().date().isoformat()
        for mission in missions:
            idempotency_key = f'good-while-you-sleep:{mission.pk}:{run_date}'
            run, brief = run_global_discovery(mission, list(raw_signals), idempotency_key=idempotency_key)

            self.stdout.write(self.style.SUCCESS(f'\n=== {mission.name} — GoodDiscoveryRun #{run.pk} ({run.status}) ==='))
            self.stdout.write(
                f'  signals_reviewed={run.signals_reviewed} duplicates_removed={run.duplicates_removed} '
                f'agents_activated={run.agents_activated} opportunities_detected={run.opportunities_detected} '
                f'qualified={run.qualified_opportunities} rejected={run.rejected_opportunities} '
                f'insufficient_evidence={run.insufficient_evidence_count} zero_capital={run.zero_capital_opportunities}'
            )
            if not brief['problems_detected']:
                self.stdout.write('  No sufficiently evidenced opportunity found.')
                continue
            for opp in brief['problems_detected']:
                self.stdout.write(
                    f'  - {opp["title"]} — confidence {opp["confidence"]:.0f}%, '
                    f'principles: {", ".join(p["name"] for p in opp["relevant_principles"]) or "(none)"}, '
                    f'resources matched: {", ".join(opp["resources_matched"]) or "(none)"}, '
                    f'next: {opp["next_safe_step"]}'
                )
            for action in brief['top_3_actions_today']:
                self.stdout.write(f'  TOP ACTION: {action["action"]} — {action["title"]}')

        # PR5 Phase 26 — funding deadlines are time-based, not event-based
        # (an existing FundingAction's deadline gets closer every night this
        # runs), so this sweep belongs in the overnight loop rather than at
        # any single mutation call site.
        deadline_notifications = notify.sweep_funding_deadlines()
        if deadline_notifications:
            self.stdout.write(f'\n{len(deadline_notifications)} funding deadline notification(s) raised.')

        self.stdout.write(self.style.WARNING(
            '\nSCHEDULER READY, not SCHEDULER ACTIVE — this command runs on demand only; '
            'see render.yaml for the disabled-by-default cron config.'
        ))
