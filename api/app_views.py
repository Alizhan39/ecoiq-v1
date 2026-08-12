"""
api/app_views.py — /api/v1/me/ and /api/v1/app-config/ for the EcoIQ
mobile/desktop app. Kept separate from api/commercial_views.py (B2B data
API) and api/views.py (public web-facing API) since these two exist purely
to serve the first-party app shell.
"""
from django.conf import settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ecoiq_commerce.models import Plan, Product
from ecoiq_commerce.services.entitlements import has_entitlement

# The subset of PART 3 feature keys the app shell actually needs to know
# about to decide what to show/hide -- kept as an explicit list (not "all
# features") so this endpoint doesn't leak the full internal catalogue.
APP_RELEVANT_FEATURE_KEYS = [
    'company_profiles_basic',
    'company_profiles_advanced',
    'portfolio_intelligence',
    'ethical_screening',
    'islamic_screening',
    'evidence_access',
    'report_download',
    'dataset_export',
]


class MeView(APIView):
    """
    GET /api/v1/me/ — the authenticated user + an entitlement summary the
    app can use to decide what to render. The app must NOT infer access
    from its own cached copy of this response beyond a single session --
    every gated read still goes through the server-side check on the
    endpoint that serves the data itself (see PART 1 of the app spec: "Do
    not rely only on client-side feature gates").
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        entitlements = {
            key: bool(has_entitlement(user, key))
            for key in APP_RELEVANT_FEATURE_KEYS
        }

        from ecoiq_commerce.models import Subscription
        active_sub = (Subscription.objects
                      .filter(user=user, status__in=('trialing', 'active'))
                      .select_related('plan', 'plan__product')
                      .order_by('-started_at').first())

        return Response({
            'id': user.pk,
            'username': user.get_username(),
            'email': user.email,
            'is_staff': user.is_staff,
            'plan': {
                'product': active_sub.plan.product.key,
                'plan': active_sub.plan.key,
                'name': active_sub.plan.name,
                'status': active_sub.status,
            } if active_sub else None,
            'entitlements': entitlements,
        })


class AppConfigView(APIView):
    """
    GET /api/v1/app-config/ — backend-driven remote configuration (PART 22
    of the app spec). Public: the app needs this before a user has logged
    in (e.g. to show a maintenance banner or force-update screen).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        catalogue = (Product.objects.filter(status='active')
                     .prefetch_related('plans'))
        return Response({
            'min_supported_version': settings.ECOIQ_APP_MIN_SUPPORTED_VERSION,
            'latest_version': settings.ECOIQ_APP_LATEST_VERSION,
            'maintenance_mode': settings.ECOIQ_APP_MAINTENANCE_MODE,
            'force_update': settings.ECOIQ_APP_FORCE_UPDATE,
            'enabled_products': [
                {
                    'key': p.key,
                    'name': p.name,
                    'plans': [
                        {'key': pl.key, 'name': pl.name, 'price_display': pl.price_display}
                        for pl in p.plans.all() if pl.is_public
                    ],
                }
                for p in catalogue
            ],
            # No standalone /privacy/ or /terms/ page exists on ecoiq.uk yet
            # (verified by inspection -- see the final report's "known risks"
            # section). URLs are null rather than pointing at pages that
            # don't exist; the app must treat null as "not yet published".
            'legal_documents': {
                'privacy_policy_url': None,
                'terms_url': None,
                'privacy_policy_version': None,
                'terms_version': None,
            },
            'support_contact': 'support@ecoiq.uk',
            'store_urls': {
                # Populated once each listing is live -- see the final
                # report's "store prerequisites" / "known risks" sections.
                'ios': None,
                'android': None,
                'windows': None,
            },
        })
