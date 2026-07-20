"""
seed_company_intelligence_demo — feat/company-halal-intelligence (PR 9):
seeds exactly 3 clearly-labelled DEMO companies with deliberately
different profiles, so the Shariah screen and 114-KPI engine both
demonstrate real nuance in browser verification:

- Nur Renewables Holdings — passes the reference Shariah screen in full
  (business activity + financial ratios), strong positive KPI evidence,
  with a few KPIs still honestly missing evidence.
- Silk Route Industrials — Shariah financial-ratio screen incomplete
  (partial financial facts recorded), mixed KPI evidence (some support,
  some conflict on the same company).
- Meridian Capital Group — business-activity screen fails (conventional
  banking language in its own description), with a real controversy
  record and KPI conflicts.

Every row this command creates carries is_demo=True. This is a
management command, not a public "run analysis" web action — see
company_intelligence/views.py's module docstring for why that matches
every other company-scoring pipeline already in this repo. The whole
batch is wrapped in one real ai_observatory.AnalysisSession (kind=
'company_intelligence') so the Observatory has real telemetry for this
pipeline to show, exactly as Part 8 of the PR9 brief asks.
"""
import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from ai_observatory.services import recorder
from companies.models import CompanyProfile
from company_intelligence.models import (
    CompanyControversy, CompanyFinancialFacts, CompanyKPIAssessment, CompanyKPIEvidenceLink,
    CompanyListing, ShariahMethodology,
)
from company_intelligence.services.kpi_engine import recompute_assessment_status
from company_intelligence.services.shariah_screening import run_shariah_screen
from evidence_memory.models import EvidenceMemory
from league.models import Company

User = get_user_model()


def _reference_methodology():
    methodology, _ = ShariahMethodology.objects.update_or_create(
        name='EcoIQ Reference Shariah Screen', version='1.0',
        defaults=dict(
            description=(
                'A reference business-activity and financial-ratio screening methodology, structured after '
                'commonly-referenced Islamic index conventions (e.g. a 33% debt/market-cap ceiling and a 5% '
                'non-permissible-income/revenue ceiling). This is a documented screening methodology, not a '
                'religious ruling, fatwa, or scholarly certification — results should be confirmed with a '
                'qualified Shariah advisory board before being relied upon.'
            ),
            source_reference='Structured with reference to commonly-published Islamic equity index screening conventions.',
            business_activity_rules=[
                {'category': 'conventional_banking', 'label': 'Conventional (interest-based) banking', 'status': 'blocked',
                 'keywords': ['conventional bank', 'interest-based lending', 'credit card issuer'],
                 'notes': 'Core revenue from interest-based lending is not screened as eligible under this methodology.'},
                {'category': 'alcohol', 'label': 'Alcohol production or distribution', 'status': 'blocked',
                 'keywords': ['alcohol production', 'brewery', 'distillery'], 'notes': ''},
                {'category': 'gambling', 'label': 'Gambling and gaming', 'status': 'blocked',
                 'keywords': ['gambling', 'casino operator', 'sports betting'], 'notes': ''},
                {'category': 'tobacco', 'label': 'Tobacco', 'status': 'blocked',
                 'keywords': ['tobacco manufacturing', 'cigarette production'], 'notes': ''},
                {'category': 'pork', 'label': 'Pork-related products', 'status': 'blocked',
                 'keywords': ['pork processing', 'pork products'], 'notes': ''},
                {'category': 'adult_entertainment', 'label': 'Adult entertainment', 'status': 'blocked',
                 'keywords': ['adult entertainment'], 'notes': ''},
                {'category': 'defence_controversial', 'label': 'Controversial weapons manufacturing', 'status': 'restricted',
                 'keywords': ['controversial weapons', 'cluster munitions'], 'tolerance_pct': 5.0,
                 'notes': 'Requires revenue-share review before being treated as eligible.'},
            ],
            financial_ratio_rules={
                'debt_to_market_cap_max': 0.33,
                'interest_bearing_securities_to_market_cap_max': 0.33,
                'non_permissible_income_to_revenue_max': 0.05,
            },
            effective_date=datetime.date(2026, 1, 1),
            is_active=True,
        ),
    )
    return methodology


def _company(name, slug, sector, country, description):
    company, _ = Company.objects.update_or_create(
        slug=slug, defaults=dict(name=name, sector=sector, country=country, description=description, is_public=True),
    )
    profile, _ = CompanyProfile.objects.update_or_create(
        company=company, defaults=dict(status='public'),
    )
    return company, profile


def _evidence(company_profile, text, *, verification_status, review_tier, document_category='other'):
    return EvidenceMemory.objects.create(
        text_chunk=text, company=company_profile, source_type='company_report',
        verification_status=verification_status, review_tier=review_tier,
        document_category=document_category, is_demo=True, visibility='project_private',
        date_collected=timezone.now().date(),
    )


def _assess(company_profile, kpi_id, links):
    """links: list of (evidence, relationship). Creates the assessment and
    its evidence links, then derives the status from them — never sets
    status directly."""
    assessment, _ = CompanyKPIAssessment.objects.update_or_create(
        company=company_profile, kpi_id=kpi_id, defaults={'is_demo': True},
    )
    assessment.evidence_links.all().delete()
    for evidence, relationship in links:
        CompanyKPIEvidenceLink.objects.create(assessment=assessment, evidence=evidence, relationship=relationship)
    recompute_assessment_status(assessment)
    return assessment


class Command(BaseCommand):
    help = 'Seeds 3 clearly-labelled DEMO companies for the Shariah screen + 114-KPI engine (PR 9).'

    def handle(self, *args, **options):
        methodology = _reference_methodology()
        self.stdout.write(f'Methodology ready: {methodology}')

        # ── Company A: Nur Renewables Holdings — passes in full ──────────
        nur, nur_profile = _company(
            'Nur Renewables Holdings', 'nur-renewables-holdings', 'energy', 'Kazakhstan',
            'Nur Renewables Holdings develops and operates solar and wind power generation assets, '
            'selling clean electricity under long-term power purchase agreements.',
        )
        CompanyListing.objects.update_or_create(
            company=nur, ticker='NURR', defaults=dict(exchange='AIX', currency='USD', is_primary=True, is_demo=True),
        )
        nur_facts = CompanyFinancialFacts.objects.create(
            company=nur_profile, as_of_date=datetime.date(2026, 3, 31),
            market_cap_usd=850_000_000, total_debt_usd=180_000_000, cash_and_equivalents_usd=60_000_000,
            interest_bearing_securities_usd=15_000_000, non_permissible_income_usd=2_000_000,
            revenue_usd=210_000_000, source='DEMO fixture — illustrative financials', is_demo=True,
        )
        session = recorder.start_session(company=nur_profile, kind='company_intelligence')
        with recorder.record_stage(session, 'business_activity_screen', 'Business Activity Screen'):
            pass
        with recorder.record_stage(session, 'financial_ratio_screen', 'Financial Ratio Screen') as info:
            screen = run_shariah_screen(nur_profile, methodology, financial_facts=nur_facts, is_demo=True)
            info['metadata'] = {'overall_result': screen.overall_result}
        ev1 = _evidence(nur_profile, 'Sustainability report confirms 100% renewable generation portfolio, third-party audited.',
                         verification_status='verified', review_tier='independently_verified', document_category='technical_report')
        ev2 = _evidence(nur_profile, 'Annual report discloses full emissions inventory and decarbonisation roadmap.',
                         verification_status='verified', review_tier='human_reviewed')
        ev3 = _evidence(nur_profile, 'Community investment disclosure: local hiring and supplier development programme.',
                         verification_status='pending', review_tier='uploaded')
        with recorder.record_stage(session, 'kpi_mapping', 'KPI Evidence Mapping', category='deterministic') as info:
            _assess(nur_profile, 4, [(ev1, 'supports')])
            _assess(nur_profile, 21, [(ev2, 'supports')])
            _assess(nur_profile, 3, [(ev3, 'supports')])
            _assess(nur_profile, 67, [])
            info['items_processed'] = 4
        recorder.finish_session(session, evidence_retrieved=3, evidence_reused=0, final_recommendation_status='recorded')
        self.stdout.write(f'Nur Renewables Holdings: Shariah {screen.overall_result}')

        # ── Company B: Silk Route Industrials — incomplete + mixed ───────
        silk, silk_profile = _company(
            'Silk Route Industrials', 'silk-route-industrials', 'metallurgy', 'Kazakhstan',
            'Silk Route Industrials operates metals processing facilities supplying regional construction '
            'and manufacturing markets.',
        )
        silk_facts = CompanyFinancialFacts.objects.create(
            company=silk_profile, as_of_date=datetime.date(2026, 3, 31),
            market_cap_usd=420_000_000, total_debt_usd=95_000_000,
            # cash_and_equivalents_usd / interest_bearing_securities_usd / non_permissible_income_usd /
            # revenue_usd deliberately left unrecorded — the point of this fixture is an honest
            # INSUFFICIENT_DATA / CONDITIONAL screen, never a value silently defaulted to zero.
            source='DEMO fixture — partial financials only', is_demo=True,
        )
        session = recorder.start_session(company=silk_profile, kind='company_intelligence')
        with recorder.record_stage(session, 'business_activity_screen', 'Business Activity Screen'):
            pass
        with recorder.record_stage(session, 'financial_ratio_screen', 'Financial Ratio Screen') as info:
            screen_b = run_shariah_screen(silk_profile, methodology, financial_facts=silk_facts, is_demo=True)
            info['metadata'] = {'missing_inputs': screen_b.financial_ratio_detail.get('missing_inputs', [])}
        ev4 = _evidence(silk_profile, 'Modernisation report describes a real furnace efficiency upgrade reducing energy intensity 12%.',
                         verification_status='verified', review_tier='human_reviewed')
        ev5 = _evidence(silk_profile, 'Regulatory filing records an unresolved emissions-permit exceedance in the prior reporting year.',
                         verification_status='verified', review_tier='system_checked')
        with recorder.record_stage(session, 'kpi_mapping', 'KPI Evidence Mapping', category='deterministic') as info:
            _assess(silk_profile, 21, [(ev4, 'supports'), (ev5, 'conflicts')])
            _assess(silk_profile, 4, [(ev5, 'conflicts')])
            info['items_processed'] = 2
        recorder.finish_session(
            session, evidence_retrieved=2, evidence_reused=0,
            warnings=['Financial facts incomplete — Shariah financial-ratio screen could not fully evaluate.'],
            final_recommendation_status='recorded',
        )
        self.stdout.write(f'Silk Route Industrials: Shariah {screen_b.overall_result}')

        # ── Company C: Meridian Capital Group — business activity fails ──
        meridian, meridian_profile = _company(
            'Meridian Capital Group', 'meridian-capital-group', 'other', 'Kazakhstan',
            'Meridian Capital Group is a conventional bank offering interest-based lending, deposit and '
            'credit card issuer services to retail and corporate customers.',
        )
        session = recorder.start_session(company=meridian_profile, kind='company_intelligence')
        with recorder.record_stage(session, 'business_activity_screen', 'Business Activity Screen') as info:
            screen_c = run_shariah_screen(meridian_profile, methodology, financial_facts=None, is_demo=True)
            info['metadata'] = {'overall_result': screen_c.overall_result}
        controversy_evidence = _evidence(
            meridian_profile, 'Regulatory enforcement action for undisclosed fee practices affecting retail customers.',
            verification_status='verified', review_tier='independently_verified',
        )
        CompanyControversy.objects.create(
            company=meridian_profile, title='Regulatory enforcement — undisclosed retail fee practices',
            category='governance', severity='high', status='unresolved', evidence=controversy_evidence,
            reported_date=datetime.date(2025, 11, 12), is_demo=True,
            notes='DEMO fixture — illustrative controversy record.',
        )
        with recorder.record_stage(session, 'kpi_mapping', 'KPI Evidence Mapping', category='deterministic') as info:
            _assess(meridian_profile, 2, [(controversy_evidence, 'conflicts')])
            _assess(meridian_profile, 44, [(controversy_evidence, 'conflicts')])
            info['items_processed'] = 2
        recorder.finish_session(
            session, evidence_retrieved=1, evidence_reused=0, blocked_recommendations=1,
            final_recommendation_status='blocked',
        )
        self.stdout.write(f'Meridian Capital Group: Shariah {screen_c.overall_result}')

        self.stdout.write(self.style.SUCCESS(
            'Company intelligence DEMO fixtures ready: Nur Renewables Holdings (pass), '
            'Silk Route Industrials (incomplete/mixed), Meridian Capital Group (fail/controversy).'
        ))
