"""
seed_good_agent_definitions — seeds the first 6 Good Agent lenses from
core.esg_principles_data.PRINCIPLES (the canonical 114-principle source —
see docs/114_GOOD_AGENTS.md for why). Idempotent: update_or_create on
principle_id, safe to re-run.

This does NOT seed all 114 — Phase 1/2 explicitly says to build the
reusable framework for all 114 and prove it with a small, real subset.
Chosen for relevance to the first vertical-slice demo (energy poverty /
coal-to-clean-heating): vulnerable-groups protection, ecological
stewardship, accountability, energy transition, equitable access, and
energy as a shared resource.
"""
from django.core.management.base import BaseCommand

from good_agents.models import GoodAgentDefinition
from good_agents.services.principles import get_principle

SEED_LENSES = [
    {
        'principle_id': 4,
        'domains': ['social', 'housing', 'health'],
        'signal_types': ['vulnerable', 'elderly', 'children', 'fuel poverty', 'cold homes', 'health risk'],
        'search_questions': [
            'Who is most exposed to harm in this situation, and how is that measured?',
            'What safeguards already exist, and are they actually reaching the people at risk?',
        ],
        'evidence_requirements': ['household/beneficiary count', 'vulnerability criteria used', 'health or safety data if claimed'],
        'risk_flags': ['claims about vulnerable groups without a named, checkable data source'],
    },
    {
        'principle_id': 9,
        'domains': ['environment', 'earth', 'land'],
        'signal_types': ['pollution', 'emissions', 'air quality', 'ecosystem', 'land use'],
        'search_questions': [
            'What is the measured environmental baseline, and from which source?',
            'Does the proposed intervention reduce or merely relocate the harm?',
        ],
        'evidence_requirements': ['emissions or air-quality measurement', 'source and date of measurement'],
        'risk_flags': ['environmental benefit asserted with no measurement source'],
    },
    {
        'principle_id': 19,
        'domains': ['justice', 'governance'],
        'signal_types': ['accountability', 'harm', 'consequences', 'responsibility'],
        'search_questions': [
            'If this intervention fails or harms someone, who is accountable, and how?',
            'Is there a visible, checkable trail from decision to outcome?',
        ],
        'evidence_requirements': ['named accountable party', 'decision/audit trail'],
        'risk_flags': ['no identifiable accountable party for a consequential action'],
    },
    {
        'principle_id': 34,
        'domains': ['energy', 'earth', 'climate'],
        'signal_types': ['coal', 'clean energy', 'energy transition', 'heating', 'renewable'],
        'search_questions': [
            'What is the current energy source, and what would replace it?',
            'What is the credible pace of transition given real technical/financial constraints?',
        ],
        'evidence_requirements': ['current fuel/energy source', 'proposed replacement technology and cost basis'],
        'risk_flags': ['transition timeline asserted with no technical or financial basis'],
    },
    {
        'principle_id': 45,
        'domains': ['social', 'housing', 'energy'],
        'signal_types': ['equitable access', 'affordability', 'underserved', 'equal access'],
        'search_questions': [
            'Who currently cannot access this resource/service, and why?',
            'Does the proposed intervention close the access gap or only serve those already served?',
        ],
        'evidence_requirements': ['access/affordability baseline for the affected population'],
        'risk_flags': ['intervention that only benefits an already-advantaged subset'],
    },
    {
        'principle_id': 91,
        'domains': ['energy', 'earth'],
        'signal_types': ['shared resource', 'energy poverty', 'community energy', 'commons'],
        'search_questions': [
            'Is this energy resource being treated as a shared/community asset or a private extraction opportunity?',
            'Could a genuinely shared-resource model (e.g. district heating, community ownership) do better than a private one?',
        ],
        'evidence_requirements': ['ownership/governance model of the energy resource in question'],
        'risk_flags': ['a "community" framing with no real shared governance or benefit-sharing mechanism'],
    },
]


class Command(BaseCommand):
    help = 'Seeds the first 6 Good Agent principle lenses from core.esg_principles_data.PRINCIPLES.'

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0
        for lens in SEED_LENSES:
            principle = get_principle(lens['principle_id'])
            if principle is None:
                self.stdout.write(self.style.WARNING(
                    f"principle_id {lens['principle_id']} not found in core.esg_principles_data.PRINCIPLES — skipped."
                ))
                continue

            _, created = GoodAgentDefinition.objects.update_or_create(
                principle_id=lens['principle_id'],
                defaults=dict(
                    name=principle['title'],
                    category=principle['category'],
                    mission=principle['question'],
                    domains=lens['domains'],
                    signal_types=lens['signal_types'],
                    search_questions=lens['search_questions'],
                    evidence_requirements=lens['evidence_requirements'],
                    risk_flags=lens['risk_flags'],
                    is_active=True,
                ),
            )
            created_count += int(created)
            updated_count += int(not created)

        self.stdout.write(self.style.SUCCESS(
            f'Good Agent lenses seeded: {created_count} created, {updated_count} updated '
            f'(of {len(SEED_LENSES)} configured; {GoodAgentDefinition.objects.count()} total rows now).'
        ))
