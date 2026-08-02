from django.conf import settings


def analytics(request):
    """
    Exposes analytics/search-console config to every template (both those
    that extend base.html and the standalone leads/investor_enquiry*.html
    pages, since render() always applies context processors regardless of
    template inheritance). Values are blank unless the corresponding env var
    is set — see ecoiq/settings.py.
    """
    return {
        'analytics': {
            'ga4_id': settings.GA4_MEASUREMENT_ID,
            'gtm_id': settings.GTM_CONTAINER_ID,
            'google_site_verification': settings.GOOGLE_SITE_VERIFICATION,
            'bing_site_verification': settings.BING_SITE_VERIFICATION,
        }
    }
