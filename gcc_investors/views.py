"""
gcc_investors/views.py — 8 routes (4 pages × EN/AR) for the GCC investor
SEO pages. Every view is a thin wrapper around _render_page(): resolve
content (content_en.py / content_ar.py) + SEO context (seo.py) + an
enquiry-form URL carrying source_page/source_country/UTM attribution, and
render one of two shared templates (page_en.html / page_ar.html).

No business logic lives here — content is data, SEO wiring is pure
functions in seo.py, and the two templates are structurally identical
(only language/direction differ) specifically so nothing about the page
*shape* can drift between countries. Only the *content* is unique per
country, per the GCC investor SEO spec's doorway-page prohibition.
"""
from urllib.parse import urlencode

from django.shortcuts import render
from django.urls import reverse
from django.utils import translation

from . import seo
from .content_ar import PAGES as PAGES_AR
from .content_en import PAGES as PAGES_EN

_UTM_KEYS = ('utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term')

# Factual geographic scope for the Service JSON-LD's areaServed — the
# region/country this page is positioned for, not a claim of operating
# presence (see content_en.py's "capabilities.live" vs "planned" split for
# the actual presence claims).
_AREA_SERVED = {
    'hub': 'GCC',
    'qatar': 'Qatar',
    'saudi': 'Saudi Arabia',
    'kuwait': 'Kuwait',
}


def _enquiry_url(request, page_key: str, lang: str, interest: str | None = None) -> str:
    """
    Builds the /request-access/investors/ URL a CTA on this page should
    point to, carrying source_page/source_country + any UTM params present
    on the CURRENT request (preserved, not invented) + lang, so the
    enquiry form renders in the same language the visitor is already
    reading and InvestorEnquiry records where they came from.
    """
    params = {
        'source_page': seo.page_url(page_key, lang, absolute=False),
        'source_country': page_key,
    }
    if interest:
        params['interest'] = interest
    if lang == 'ar':
        params['lang'] = 'ar'
    for key in _UTM_KEYS:
        value = request.GET.get(key, '').strip()
        if value:
            params[key] = value
    return f"{reverse('leads:investor_enquiry')}?{urlencode(params)}"


def _render_page(request, page_key: str, lang: str):
    content = (PAGES_EN if lang == 'en' else PAGES_AR)[page_key]

    context = {
        'content': content,
        'page_key': page_key,
        'is_arabic': lang == 'ar',
        'area_served': _AREA_SERVED[page_key],
        'breadcrumbs': seo.build_breadcrumbs(page_key, lang),
        'enquiry_url': _enquiry_url(request, page_key, lang),
        'founding_partner_enquiry_url': _enquiry_url(request, page_key, lang, interest='founding_partner'),
        **seo.build_seo_context(page_key, lang),
    }

    template = f'gcc_investors/page_{lang}.html'

    if lang == 'ar':
        # Scoped to this render only (translation.override is a context
        # manager, not a global setting change) -- see docs/adr note in
        # seo.py for why this doesn't touch ecoiq/settings.py's LANGUAGES.
        with translation.override('ar'):
            return render(request, template, context)
    return render(request, template, context)


def gcc_hub_en(request):
    """GET /gcc-investors/"""
    return _render_page(request, 'hub', 'en')


def gcc_hub_ar(request):
    """GET /ar/gcc-investors/"""
    return _render_page(request, 'hub', 'ar')


def qatar_investors_en(request):
    """GET /qatar/investors/"""
    return _render_page(request, 'qatar', 'en')


def qatar_investors_ar(request):
    """GET /ar/qa/investors/"""
    return _render_page(request, 'qatar', 'ar')


def saudi_investors_en(request):
    """GET /saudi-arabia/investors/"""
    return _render_page(request, 'saudi', 'en')


def saudi_investors_ar(request):
    """GET /ar/sa/investors/"""
    return _render_page(request, 'saudi', 'ar')


def kuwait_investors_en(request):
    """GET /kuwait/investors/"""
    return _render_page(request, 'kuwait', 'en')


def kuwait_investors_ar(request):
    """GET /ar/kw/investors/"""
    return _render_page(request, 'kuwait', 'ar')
