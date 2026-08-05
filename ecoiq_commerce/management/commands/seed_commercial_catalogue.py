"""
seed_commercial_catalogue — idempotent seed of the Feature/Product/Plan/
PlanFeature catalogue described in PARTs 1-2 of the commercial architecture
spec. Safe to re-run (uses get_or_create / update throughout).

Usage:
    python manage.py seed_commercial_catalogue
"""
from django.core.management.base import BaseCommand

from ecoiq_commerce.models import Feature, Plan, PlanFeature, Product

FEATURES = [
    # key, name, category
    ('company_profiles_basic', 'Basic Company Profiles', 'company_data'),
    ('company_profiles_advanced', 'Advanced Company Analytics', 'company_data'),
    ('portfolio_intelligence', 'Portfolio Exposure Intelligence', 'portfolio'),
    ('ethical_screening', 'Ethical Screening', 'screening'),
    ('islamic_screening', 'Islamic Screening', 'screening'),
    ('evidence_access', 'Evidence Trail Access', 'company_data'),
    ('report_download', 'Report Download', 'reports'),
    ('dataset_export', 'Dataset Export (CSV)', 'reports'),
    ('api_access', 'API Access', 'api'),
    ('api_evidence_access', 'API Evidence Access', 'api'),
    ('marketplace_project_submit', 'Marketplace: Submit a Project', 'marketplace'),
    ('marketplace_investor_access', 'Marketplace: Investor Discovery', 'marketplace'),
    ('academy_courses', 'Academy Course Access', 'academy'),
    ('professional_certification', 'Academy Certification', 'academy'),
]

# (product_key, product_type, name, tagline, status, sort_order)
PRODUCTS = [
    ('data-api', 'data_api', 'EcoIQ Data API',
     'EcoIQ intelligence, inside the apps your customers already use.', 'active', 10),
    ('lite', 'lite', 'EcoIQ Lite',
     'Follow companies, build a watchlist, understand your exposure.', 'active', 20),
    ('professional', 'professional', 'EcoIQ Professional',
     'Full evidence trails, exports, and portfolio intelligence for analysts.', 'active', 30),
    ('marketplace', 'marketplace', 'EcoIQ Project Marketplace',
     'Verified climate-project intelligence for developers and investors.', 'coming_soon', 40),
    ('research', 'research', 'EcoIQ Research',
     'Paid sector, company, country and thematic reports.', 'coming_soon', 50),
    ('academy', 'academy', 'EcoIQ Academy',
     'Applied training in AI-assisted climate-risk and ethical-investment analysis.', 'coming_soon', 60),
]

# (product_key, plan_key, name, billing_period, price, currency, api_tier, is_public, feature_keys[])
PLANS = [
    ('data-api', 'explorer', 'API Explorer', 'monthly', 0, 'USD', 'explorer', True,
     ['company_profiles_basic', 'api_access']),
    ('data-api', 'api-professional', 'API Professional', 'monthly', 499, 'USD', 'professional', True,
     ['company_profiles_basic', 'company_profiles_advanced', 'api_access', 'api_evidence_access',
      'ethical_screening', 'islamic_screening']),
    ('data-api', 'api-enterprise', 'API Enterprise', 'custom', None, 'USD', 'enterprise', True,
     ['company_profiles_basic', 'company_profiles_advanced', 'api_access', 'api_evidence_access',
      'ethical_screening', 'islamic_screening', 'evidence_access']),

    ('lite', 'free', 'Free', 'monthly', 0, 'USD', '', True,
     ['company_profiles_basic', 'portfolio_intelligence']),
    ('lite', 'lite', 'EcoIQ Lite', 'monthly', 15, 'USD', '', True,
     ['company_profiles_basic', 'portfolio_intelligence', 'ethical_screening', 'islamic_screening',
      'report_download']),

    ('professional', 'professional', 'EcoIQ Professional', 'monthly', 79, 'USD', '', True,
     ['company_profiles_basic', 'company_profiles_advanced', 'portfolio_intelligence', 'evidence_access',
      'ethical_screening', 'islamic_screening', 'report_download', 'dataset_export', 'api_access']),
]

# Free-tier and Lite quantity limits, applied on top of the inclusion rows above.
# (plan_key_within_product, feature_key, quantity_limit, limit_period)
PLAN_LIMITS = [
    ('lite', 'free', 'company_profiles_basic', 20, 'monthly'),
    ('lite', 'free', 'dataset_export', 1, 'monthly'),
    ('lite', 'lite', 'dataset_export', 10, 'monthly'),
    ('professional', 'professional', 'dataset_export', 200, 'monthly'),
    ('data-api', 'explorer', 'api_access', 100, 'monthly'),  # mirrors api.APIKey explorer tier (100/day handled by throttle; this is a coarse plan-level allowance)
]


class Command(BaseCommand):
    help = 'Seed the EcoIQ commercial catalogue (Products, Plans, Features, PlanFeatures)'

    def handle(self, *args, **options):
        feature_by_key = {}
        for key, name, category in FEATURES:
            feature, created = Feature.objects.update_or_create(
                key=key, defaults={'name': name, 'category': category},
            )
            feature_by_key[key] = feature
            self.stdout.write(f'{"  + " if created else "    "}Feature: {key}')

        product_by_key = {}
        for key, product_type, name, tagline, status, sort_order in PRODUCTS:
            product, created = Product.objects.update_or_create(
                key=key, defaults={
                    'product_type': product_type, 'name': name, 'tagline': tagline,
                    'status': status, 'sort_order': sort_order,
                },
            )
            product_by_key[key] = product
            self.stdout.write(f'{"  + " if created else "    "}Product: {key} ({status})')

        plan_by_product_and_key = {}
        for product_key, plan_key, name, period, price, currency, api_tier, is_public, feature_keys in PLANS:
            plan, created = Plan.objects.update_or_create(
                product=product_by_key[product_key], key=plan_key,
                defaults={
                    'name': name, 'billing_period': period, 'price_amount': price,
                    'currency': currency, 'api_tier': api_tier, 'is_public': is_public,
                },
            )
            plan_by_product_and_key[(product_key, plan_key)] = plan
            self.stdout.write(f'{"  + " if created else "    "}Plan: {product_key}/{plan_key}')
            for feature_key in feature_keys:
                PlanFeature.objects.update_or_create(
                    plan=plan, feature=feature_by_key[feature_key],
                    defaults={'is_included': True, 'limit_period': 'unlimited', 'quantity_limit': None},
                )

        for product_key, plan_key, feature_key, limit, period in PLAN_LIMITS:
            plan = plan_by_product_and_key[(product_key, plan_key)]
            PlanFeature.objects.update_or_create(
                plan=plan, feature=feature_by_key[feature_key],
                defaults={'is_included': True, 'quantity_limit': limit, 'limit_period': period},
            )

        self.stdout.write(self.style.SUCCESS(
            f'\nSeeded {len(FEATURES)} features, {len(PRODUCTS)} products, {len(PLANS)} plans.'
        ))
