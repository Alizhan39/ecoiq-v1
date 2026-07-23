"""
seed_signal_providers — registers the 3 real SignalProvider rows PR4
implements adapters for. See good_agents/services/provider_adapters.py for
the actual fetch logic; this command only creates/updates the registry
rows describing them (Phase 1). Idempotent: update_or_create on slug.
"""
from django.core.management.base import BaseCommand

from good_agents.models import SignalProvider

PROVIDERS = [
    {
        'slug': 'usgs-significant-earthquakes',
        'name': 'USGS Significant Earthquakes (past 30 days)',
        'provider_type': 'climate_environmental_dataset',
        'geographies': ['global'],
        'domains': ['environment', 'climate_adaptation', 'infrastructure'],
        'trust_tier': 'high',
        'fetch_method': (
            'HTTPS GET https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson '
            '— public GeoJSON feed, no authentication, US Geological Survey.'
        ),
        'refresh_cadence': 'On demand (every run_good_while_you_sleep invocation).',
        'cost_usd_per_refresh': 0.0,
    },
    {
        'slug': 'govuk-search',
        'name': 'GOV.UK Search API (grant / funding / policy queries)',
        'provider_type': 'government_publication',
        'geographies': ['United Kingdom'],
        'domains': ['energy', 'housing', 'infrastructure', 'financial_inclusion'],
        'trust_tier': 'high',
        'fetch_method': (
            'HTTPS GET https://www.gov.uk/api/search.json?q=... for a small fixed set of grant/funding/policy '
            'queries — public search API, no authentication, UK Government Digital Service.'
        ),
        'refresh_cadence': 'On demand (every run_good_while_you_sleep invocation).',
        'cost_usd_per_refresh': 0.0,
    },
    {
        'slug': 'uk-ea-flood-monitoring',
        'name': 'UK Environment Agency Real-Time Flood Monitoring',
        'provider_type': 'regulatory_announcement',
        'geographies': ['United Kingdom'],
        'domains': ['environment', 'infrastructure', 'community_resilience'],
        'trust_tier': 'high',
        'fetch_method': (
            'HTTPS GET https://environment.data.gov.uk/flood-monitoring/id/floods?min-severity=3 — public '
            'real-time flood warnings API, no authentication, UK Environment Agency. Open Government Licence v3.'
        ),
        'refresh_cadence': 'On demand (every run_good_while_you_sleep invocation).',
        'cost_usd_per_refresh': 0.0,
    },
]


class Command(BaseCommand):
    help = 'Registers the 3 real SignalProvider rows PR4 implements adapters for.'

    def handle(self, *args, **options):
        created, updated = 0, 0
        for spec in PROVIDERS:
            # These 3 (and only these 3) have a real, tested adapter in
            # provider_adapters.PROVIDER_ADAPTERS — safe to mark 'active'
            # immediately rather than the model's honest 'inactive' default
            # for providers nobody has wired an adapter for yet.
            _, was_created = SignalProvider.objects.update_or_create(
                slug=spec['slug'],
                defaults={**{k: v for k, v in spec.items() if k != 'slug'}, 'status': 'active'},
            )
            created += int(was_created)
            updated += int(not was_created)
        self.stdout.write(self.style.SUCCESS(f'Signal providers: {created} created, {updated} updated (of {len(PROVIDERS)} configured).'))
