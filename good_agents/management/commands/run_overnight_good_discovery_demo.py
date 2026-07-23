"""
run_overnight_good_discovery_demo — the first Global Good Discovery demo
(PR3 Phase 33): 4 signals, only 1 should survive triage + evidence gate as a
qualifying problem, 1 more registers as a matchable resource, and 1 is
correctly rejected as noise.

This is a SEPARATE demonstration from PR2's `run_almaty_good_agent_demo`
(that command, and the architecture it proves, are untouched — see
good_agents/services/discovery_engine.py's module docstring). This command
proves the NEW front door: a human never submits these 4 signals as a
"problem" — the engine itself normalises, deduplicates, clusters, triages,
evidence-gates, matches resources, and produces a Morning Brief.

All 4 signals are clearly-labelled demo fixtures — no real household
survey, government announcement, or factory disclosure exists behind them.
"""
import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from good_agents.models import GoodMission
from good_agents.services.discovery_engine import run_global_discovery

MISSION_NAME = 'Reduce Regional Energy Poverty (Overnight Demo)'

RAW_SIGNALS = [
    {  # Signal A — a real problem: should qualify.
        'signal_type': 'harm',
        'title': 'Rural households face high winter heating costs from ageing coal boilers',
        'summary': (
            'A regional survey reports rural households spending a large share of income on coal heating, '
            'with visible smoke pollution during winter months.'
        ),
        'region': 'Karaganda region', 'sector': 'heating / energy transition', 'tags': ['energy'],
        'confidence': 55.0, 'severity': 65.0,
        'potential_affected_population': 'Rural households in the Karaganda region (regional survey estimate — demo fixture)',
        'publisher': 'Regional Energy Poverty Survey (demo fixture)',
        'source_url': 'https://example.org/demo/signal-a', 'raw_evidence_ref': 'demo:signal-a-survey',
    },
    {  # Signal B — a matchable funding resource.
        'signal_type': 'funding',
        'title': 'National Energy Efficiency Programme opens rural heating upgrade applications',
        'summary': 'A national government programme has opened applications for rural heating efficiency upgrades in the current cycle.',
        'region': 'Karaganda region', 'sector': 'heating / energy transition',
        'tags': ['resource_type:government_programme'], 'confidence': 70.0, 'severity': 20.0,
        'publisher': 'Ministry announcement (demo fixture)',
        'source_url': 'https://example.org/demo/signal-b', 'raw_evidence_ref': 'demo:signal-b-programme',
    },
    {  # Signal C — a matchable circular-economy resource (waste heat).
        'signal_type': 'resource',
        'title': 'Regional factory reports significant waste heat output near rural district',
        'summary': 'An industrial facility near the affected rural district reports substantial waste heat output from its production process.',
        'region': 'Karaganda region', 'sector': 'industrial',
        'tags': ['resource_type:waste_heat'], 'confidence': 50.0, 'severity': 10.0,
        'publisher': 'Industrial disclosure (demo fixture)',
        'source_url': 'https://example.org/demo/signal-c', 'raw_evidence_ref': 'demo:signal-c-factory',
    },
    {  # Signal D — irrelevant noise: must be rejected, not turned into an opportunity.
        'signal_type': 'price_change',
        'title': 'Global technology stocks rally on strong quarterly earnings',
        'summary': 'Major technology indices rose sharply after several companies reported earnings above analyst expectations.',
        'region': '', 'sector': 'financial markets', 'tags': [],
        'confidence': 80.0, 'severity': 5.0,
        'publisher': 'Market news (demo fixture)', 'source_url': 'https://example.org/demo/signal-d',
    },
]


class Command(BaseCommand):
    help = 'Runs the first Global Good Discovery overnight demo: 4 signals, noise rejection, resource matching, Morning Brief.'

    def handle(self, *args, **options):
        from django.core.management import call_command
        # This demo's signals are hand-tuned to match the 6 curated lenses
        # (coal/heating/pollution/equitable-access keywords) — seeding just
        # those 6 is correct here. A real-world signal stream (PR4's
        # run_good_while_you_sleep) seeds all 114 instead, since real
        # signals rarely match this narrow, Almaty-specific vocabulary.
        call_command('seed_good_agent_definitions')

        mission, _ = GoodMission.objects.update_or_create(
            name=MISSION_NAME,
            defaults=dict(
                description='Demo mission: find evidence-backed energy-poverty opportunities and matchable resources.',
                geographies=['Kazakhstan'], themes=['energy'], run_cost_budget_usd=5.0,
                min_confidence=35.0, max_opportunities=5, enabled=True,
            ),
        )

        now = timezone.now()
        signals_with_timestamps = []
        for offset_days, raw in zip([3, 1, 5, 0], RAW_SIGNALS):
            signals_with_timestamps.append({**raw, 'published_at': now - datetime.timedelta(days=offset_days)})

        run, brief = run_global_discovery(
            mission, signals_with_timestamps, execution_mode='simulated_demo',
            idempotency_key='overnight-good-discovery-demo-v1',
        )

        self.stdout.write(self.style.SUCCESS(
            f'\nGoodDiscoveryRun #{run.pk}: {run.status} (stage={run.current_stage})\n'
            f'  signals reviewed: {run.signals_reviewed}\n'
            f'  duplicates removed: {run.duplicates_removed}\n'
            f'  agents activated: {run.agents_activated}\n'
            f'  opportunities detected: {run.opportunities_detected} (expected 1 — the heating-cost problem)\n'
            f'  rejected: {run.rejected_opportunities}\n'
            f'  insufficient evidence: {run.insufficient_evidence_count}\n'
            f'  zero-capital opportunities: {run.zero_capital_opportunities}\n'
        ))
        self.stdout.write(self.style.SUCCESS(f'Morning Brief — {brief["what_changed_overnight"]}'))
        for action in brief['top_3_actions_today']:
            self.stdout.write(f'  TOP ACTION: {action["action"]} — {action["title"]}')
        if not brief['problems_detected']:
            self.stdout.write(self.style.WARNING('No opportunity was created — check evidence gate thresholds.'))
        else:
            opp = brief['problems_detected'][0]
            self.stdout.write(self.style.SUCCESS(
                f'\nOpportunity: {opp["title"]}\n'
                f'  resources matched: {opp["resources_matched"] or "(none yet)"}\n'
                f'  next safe step: {opp["next_safe_step"]}\n'
            ))
        self.stdout.write(self.style.WARNING(
            'All 4 signals are labelled demo fixtures — no real survey, government announcement, or factory disclosure exists behind them.'
        ))
