"""
seed_capability_graph_from_real_providers — seeds a small number of real,
conservatively-scoped OrganisationCapability rows for the organisations
behind PR4's already-verified real SignalProvider adapters
(good_agents/services/provider_adapters.py). Evidence URLs here are the
EXACT endpoints those adapters already call — not new/unverified URLs —
so nothing in this seed is a fabricated citation.

Deliberately narrow: only two real, well-documented statutory/scientific
roles are seeded, both at verification_state='documented' (a real public
source states this) rather than 'independently_verified' (which requires
a human — see capability_graph.services.capabilities.verify_capability).
Idempotent: safe to re-run.
"""
from django.core.management.base import BaseCommand

from capability_graph.services.capabilities import record_capability
from capability_graph.services.organisations import get_or_create_organisation
from capability_graph.services.routes import add_public_route
from good_agents.services.provider_adapters import EA_FLOODS_URL, USGS_URL


class Command(BaseCommand):
    help = 'Seeds real, evidence-backed capability data for the organisations behind PR4\'s real signal providers.'

    def handle(self, *args, **options):
        usgs = get_or_create_organisation(
            'USGS (US Geological Survey)', org_type='research_institution', jurisdiction='Global',
            website='https://www.usgs.gov/',
        )
        usgs_capability = record_capability(
            usgs, 'measure', jurisdiction='Global', topic_domain='seismic activity',
            evidence_url=USGS_URL,
            limitations=(
                'Publishes real-time seismic measurement data (magnitude, location, depth). Does not itself '
                'coordinate emergency response, fund disaster relief, or authorise any regulatory action — '
                'those require a different, separately-evidenced organisation.'
            ),
        )
        record_capability(
            usgs, 'research', jurisdiction='Global', topic_domain='seismic activity',
            evidence_url=USGS_URL,
            limitations='Publishes hazard research and monitoring data; not a funding or regulatory body.',
        )
        add_public_route(usgs_capability, 'online_application', USGS_URL, notes='Public GeoJSON feed, not a human-facing application form.')

        ea = get_or_create_organisation(
            'UK Environment Agency', org_type='regulator', jurisdiction='England',
            website='https://www.gov.uk/government/organisations/environment-agency',
        )
        ea_capability = record_capability(
            ea, 'regulate', jurisdiction='England', topic_domain='flood risk',
            evidence_url=EA_FLOODS_URL,
            limitations=(
                'Statutory flood-risk regulator for England only — has no equivalent authority in Scotland, '
                'Wales, or Northern Ireland (each has its own separate body). Publishes flood warnings; does '
                'not itself fund flood-defence works for individual households.'
            ),
        )
        record_capability(
            ea, 'respond_to_emergency', jurisdiction='England', topic_domain='flood risk',
            evidence_url=EA_FLOODS_URL,
            limitations='Issues public flood warnings/alerts for England; on-the-ground emergency response is coordinated with local authorities and emergency services, not solely the Environment Agency.',
        )
        add_public_route(ea_capability, 'public_contact_form', EA_FLOODS_URL, notes='Public real-time flood monitoring API/feed.')

        self.stdout.write(self.style.SUCCESS(
            f'Seeded capability data for {usgs.name} and {ea.name} '
            f'({usgs.capabilities.count() + ea.capabilities.count()} capability edges).'
        ))
