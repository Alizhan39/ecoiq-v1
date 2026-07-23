"""
seed_global_monitoring_mission — creates the one real, enabled GoodMission
`run_good_while_you_sleep` runs by default (PR4 Phase 19's first real
demo). Idempotent: update_or_create on name.
"""
from django.core.management.base import BaseCommand

from good_agents.models import GoodMission

MISSION_NAME = 'Global Real-Time Signal Monitoring (Live Public Sources)'


class Command(BaseCommand):
    help = 'Seeds the real, enabled GoodMission that monitors live public signal providers.'

    def handle(self, *args, **options):
        mission, created = GoodMission.objects.update_or_create(
            name=MISSION_NAME,
            defaults=dict(
                description=(
                    'Continuously monitor real public signal providers (USGS significant earthquakes, '
                    'GOV.UK grant/funding search, UK Environment Agency flood warnings) for evidence-backed '
                    'opportunities to reduce harm, connect an unmet need to an existing resource, or surface '
                    'a genuine funding match — with no owned capital required to act on most findings.'
                ),
                geographies=['global'], themes=['energy', 'environment', 'infrastructure', 'community_resilience'],
                run_cost_budget_usd=5.0, min_confidence=35.0, max_opportunities=10,
                risk_tolerance='medium', enabled=True,
                schedule='Intended daily — see render.yaml for the disabled-by-default cron config.',
            ),
        )
        state = 'created' if created else 'updated (already existed)'
        self.stdout.write(self.style.SUCCESS(f'Global monitoring mission {state}: "{mission.name}" (enabled={mission.enabled}).'))
