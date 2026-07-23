"""
seed_dogfood_mission — creates the Dogfood GoodMission (PR3 Phase 34):
"How can EcoIQ create measurable good in the next 30 days with minimal
owned capital?"

This command creates the MISSION CONFIG ROW only — it deliberately does
NOT run a discovery pass against fabricated "EcoIQ opportunity" signals.
Inventing pilot/grant/introduction signals that purport to be about EcoIQ's
own real-world opportunities would misrepresent fiction as discovered
fact, which is exactly what this whole system's evidence-honesty discipline
forbids. When real candidate signals about EcoIQ's own position exist (a
real grant EcoIQ could apply to, a real introduction opportunity), run
`good_agents.services.discovery_engine.run_global_discovery` against this
mission with those real signals — see docs/GLOBAL_GOOD_DISCOVERY.md.
"""
from django.core.management.base import BaseCommand

from good_agents.models import GoodMission

MISSION_NAME = 'EcoIQ Dogfood — 30 Days, Minimal Capital'


class Command(BaseCommand):
    help = 'Seeds the Dogfood GoodMission config row (no fabricated signals are run against it).'

    def handle(self, *args, **options):
        mission, created = GoodMission.objects.update_or_create(
            name=MISSION_NAME,
            defaults=dict(
                description=(
                    'How can EcoIQ create measurable good in the next 30 days with minimal owned capital? '
                    'Candidates: zero-capital introductions, public-interest research, grant discovery, '
                    'pilot opportunities, energy-transition opportunities, responsible-capital introductions. '
                    'Self-promotional activity must never outrank genuine impact merely because it benefits EcoIQ.'
                ),
                geographies=[], themes=[], run_cost_budget_usd=5.0, min_confidence=40.0,
                max_opportunities=10, risk_tolerance='medium', enabled=False,
                schedule='Manual trigger only — no real signals exist yet to run this against honestly.',
            ),
        )
        state = 'created' if created else 'updated (already existed)'
        self.stdout.write(self.style.SUCCESS(
            f'Dogfood mission {state}: "{mission.name}" (enabled={mission.enabled}). '
            f'Not run against any signal — see command docstring.'
        ))
