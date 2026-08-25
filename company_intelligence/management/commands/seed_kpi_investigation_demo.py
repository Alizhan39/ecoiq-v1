"""
Seed one worked KPI investigation: Apple against principle #114.

WHY A SEED COMMAND AND NOT FIXTURES IN THE TEMPLATE
---------------------------------------------------
The investigation view reads structured records and nothing else. If the
evidence lived in JSX it would be unreviewable, untestable, impossible to
supersede, and it would silently become "content" rather than evidence — which
is the exact failure the review-state machinery exists to prevent.

EVERY ROW IS is_demo=True
-------------------------
These are real, citable public sources, but this corpus was assembled to
demonstrate the architecture rather than produced by EcoIQ's ingestion and
review pipeline. `is_demo` is what stops it being presented as independently
verified intelligence, and the API passes the flag through so the UI can say so.

WHY APPLE, AND WHY BOTH DIRECTIONS
----------------------------------
Principle #114 asks whether an organisation protects people from manipulation
"even where legally permitted". Apple is the clearest available case where the
honest answer is BOTH: it operates platform controls that materially reduce
third-party manipulation, and a regulator has separately established that its
own rules constrained consumer choice. A demonstration that only showed one
direction would misrepresent both the company and the principle.

Idempotent: re-running updates in place rather than accumulating duplicates.
"""
from __future__ import annotations

import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

KPI_ID = 114

#: Authoritative, publicly citable sources only. Each entry states what the
#: source IS in evidentiary terms — see EvidenceMemory.LEGAL_STATUS_CHOICES.
EVIDENCE = [
    {
        'ref': 'Apple — App Tracking Transparency (developer documentation)',
        'url': 'https://developer.apple.com/documentation/apptrackingtransparency',
        'authority': 'Apple Inc.',
        'legal_status': 'company_policy',
        'relation': 'supports',
        'tier': 'human_reviewed',
        'collected': datetime.date(2026, 8, 25),
        'text': (
            'Apple requires apps to obtain a user\'s explicit permission through the '
            'App Tracking Transparency framework before tracking that user across apps '
            'and websites owned by other companies. Where permission is refused, the '
            'device identifier used for cross-party tracking is withheld from the app.'
        ),
    },
    {
        'ref': 'Apple — App Review Guidelines, sections on data, design and deception',
        'url': 'https://developer.apple.com/app-store/review/guidelines/',
        'authority': 'Apple Inc.',
        'legal_status': 'company_policy',
        'relation': 'supports',
        'tier': 'human_reviewed',
        'collected': datetime.date(2026, 8, 25),
        'text': (
            'Apple\'s App Review Guidelines prohibit applications that mislead users, '
            'including deceptive interface design, hidden or undisclosed functionality, '
            'and manipulation of users into purchases or permissions they did not intend.'
        ),
    },
    {
        'ref': 'European Commission — non-compliance decision, App Store anti-steering (DMA)',
        'url': 'https://ec.europa.eu/commission/presscorner/detail/en/ip_25_1085',
        'authority': 'European Commission',
        'legal_status': 'final_regulatory_finding',
        'relation': 'conflicts',
        'tier': 'independently_verified',
        'collected': datetime.date(2026, 8, 25),
        'text': (
            'The European Commission found that Apple\'s App Store rules restricted app '
            'developers from informing users about alternative, potentially cheaper '
            'purchasing options outside the App Store. A fine of EUR 500 million was '
            'imposed under the Digital Markets Act, and Apple was required to remove the '
            'restrictions.'
        ),
    },
    {
        'ref': 'European Commission — browser and default choice screens in the EU',
        'url': 'https://ec.europa.eu/commission/presscorner/detail/en/ip_24_1161',
        'authority': 'European Commission',
        'legal_status': 'remediation_record',
        'relation': 'context',
        'tier': 'human_reviewed',
        'collected': datetime.date(2026, 8, 25),
        'text': (
            'Following Digital Markets Act obligations, Apple introduced a browser choice '
            'screen for EU users and changes permitting default application selection. '
            'The Commission continued to assess whether the implemented changes were '
            'sufficient.'
        ),
    },
]

#: finding -> response -> change -> regulatory response -> residual concern.
#: `residual_concern` is present deliberately: a remediation chain that ends at
#: "we changed it" documents a claim, not an outcome.
REMEDIATION = [
    {'position': 1, 'kind': 'finding', 'verification': 'independently_confirmed',
     'summary': 'Anti-steering rules found to restrict developer communication with users.',
     'detail': 'European Commission non-compliance decision under the Digital Markets Act.',
     'on': datetime.date(2025, 4, 23)},
    {'position': 2, 'kind': 'company_response', 'verification': 'claimed',
     'summary': 'Apple stated it disagreed with the decision and would appeal.',
     'detail': 'A stated position, recorded as such. It does not change the finding.',
     'on': datetime.date(2025, 4, 23)},
    {'position': 3, 'kind': 'product_or_policy_change', 'verification': 'evidenced',
     'summary': 'App Store terms updated to permit external purchase links in the EU.',
     'detail': 'Link entitlements and revised business terms introduced for EU developers.',
     'on': datetime.date(2025, 6, 26)},
    {'position': 4, 'kind': 'regulatory_response', 'verification': 'contested',
     'summary': 'Commission continued assessing whether the changes achieved compliance.',
     'detail': 'A change made is not the same as a change accepted.',
     'on': datetime.date(2025, 7, 1)},
    {'position': 5, 'kind': 'residual_concern', 'verification': 'claimed',
     'summary': 'Fee structure and presentation of external options remain under scrutiny.',
     'detail': ('Remediation addresses the restriction found. It does not retire the '
                'historical finding, and does not by itself evidence neutral choice '
                'architecture.'),
     'on': None},
]


class Command(BaseCommand):
    help = 'Seed the Apple x principle #114 investigation demo (idempotent, is_demo=True).'

    def add_arguments(self, parser):
        parser.add_argument('--slug', default='apple')
        parser.add_argument('--kpi', type=int, default=KPI_ID)

    @transaction.atomic
    def handle(self, *args, **options):
        from companies.models import CompanyProfile
        from company_intelligence.models import (
            CompanyKPIAssessment, CompanyKPIEvidenceLink, KPIRemediationStep,
        )
        from evidence_memory.models import EvidenceMemory
        from league.models import Company

        slug, kpi_id = options['slug'], options['kpi']

        company = Company.objects.filter(slug=slug).first()
        if company is None:
            self.stderr.write(self.style.ERROR(
                f'No company "{slug}". Run seed_global_companies first.'))
            return
        profile, _ = CompanyProfile.objects.get_or_create(company=company)

        assessment, _ = CompanyKPIAssessment.objects.update_or_create(
            company=profile, kpi_id=kpi_id,
            defaults={
                'rationale': (
                    'Apple operates platform-level controls that materially reduce '
                    'manipulation of users by third parties. A final regulatory finding '
                    'separately establishes that Apple\'s own App Store rules restricted '
                    'users\' visibility of alternative purchasing options. Both hold.'
                ),
                'confidence': 'high',
                'is_demo': True,
            },
        )

        created = 0
        for item in EVIDENCE:
            evidence, made = EvidenceMemory.objects.update_or_create(
                source_reference=item['ref'],
                defaults={
                    'text_chunk': item['text'],
                    'source_url': item['url'],
                    'source_type': 'manual',
                    'source_authority': item['authority'],
                    'legal_status': item['legal_status'],
                    'company': profile,
                    'agent_name': 'seed_kpi_investigation_demo',
                    'confidence': 0.9,
                    'date_collected': item['collected'],
                    'verification_status': 'verified',
                    'review_tier': item['tier'],
                    'is_demo': True,
                    'visibility': 'platform_learning_demo',
                },
            )
            created += int(made)
            CompanyKPIEvidenceLink.objects.update_or_create(
                assessment=assessment, evidence=evidence,
                defaults={
                    'relationship': item['relation'],
                    'review_state': 'confirmed',
                    'match_basis': 'Seeded demonstration corpus (deterministic, not inferred).',
                },
            )

        for step in REMEDIATION:
            KPIRemediationStep.objects.update_or_create(
                assessment=assessment, position=step['position'],
                defaults={
                    'kind': step['kind'], 'summary': step['summary'],
                    'detail': step['detail'], 'occurred_on': step['on'],
                    'verification': step['verification'], 'is_demo': True,
                },
            )

        # The engine decides the verdict from the links. It is never asserted here.
        from company_intelligence.services.kpi_engine import recompute_assessment_status
        recompute_assessment_status(assessment)
        assessment.refresh_from_db()

        self.stdout.write(self.style.SUCCESS(
            f'{company.name} x KPI {kpi_id}: {len(EVIDENCE)} evidence ({created} new), '
            f'{len(REMEDIATION)} remediation steps, engine verdict = {assessment.status}'))
