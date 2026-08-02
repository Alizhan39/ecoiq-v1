"""
gcc_investors/seo.py — canonical/hreflang/breadcrumb wiring shared by every
GCC investor page. Kept as pure functions (no template logic) so the
hreflang graph is defined in exactly one place and can be unit-tested for
reciprocity directly (see gcc_investors/tests.py).

Site is EN-primary with COUNTRY-SPECIFIC language variants (en-QA/ar-QA,
en-SA/ar-SA, en-KW/ar-KW) for the three country pages, and a plain en/ar
pair for the hub — the hub isn't country-specific, so it doesn't carry a
region subtag. x-default always points at the hub's English URL, per the
GCC investor SEO spec ("x-default pointing to /gcc-investors/").
"""
SITE = 'https://ecoiq.uk'

# path, keyed by page -> lang
PAGE_PATHS = {
    'hub': {
        'en': '/gcc-investors/',
        'ar': '/ar/gcc-investors/',
    },
    'qatar': {
        'en': '/qatar/investors/',
        'ar': '/ar/qa/investors/',
    },
    'saudi': {
        'en': '/saudi-arabia/investors/',
        'ar': '/ar/sa/investors/',
    },
    'kuwait': {
        'en': '/kuwait/investors/',
        'ar': '/ar/kw/investors/',
    },
}

# hreflang code, keyed by page -> lang
HREFLANG_CODES = {
    'hub': {'en': 'en', 'ar': 'ar'},
    'qatar': {'en': 'en-QA', 'ar': 'ar-QA'},
    'saudi': {'en': 'en-SA', 'ar': 'ar-SA'},
    'kuwait': {'en': 'en-KW', 'ar': 'ar-KW'},
}

X_DEFAULT_URL = SITE + PAGE_PATHS['hub']['en']


def page_url(page_key: str, lang: str, absolute: bool = True) -> str:
    path = PAGE_PATHS[page_key][lang]
    return (SITE + path) if absolute else path


def build_seo_context(page_key: str, lang: str) -> dict:
    """
    Returns the context every gcc_investors template needs for canonical +
    hreflang: {canonical_url, hreflang_alternates, lang_switch_url,
    lang_switch_code}. hreflang_alternates is reciprocal by construction —
    every page in PAGE_PATHS[page_key] appears, plus x-default -> hub.
    """
    other_lang = 'ar' if lang == 'en' else 'en'
    alternates = [
        (HREFLANG_CODES[page_key][code_lang], page_url(page_key, code_lang))
        for code_lang in ('en', 'ar')
    ]
    alternates.append(('x-default', X_DEFAULT_URL))

    return {
        'canonical_url': page_url(page_key, lang),
        'hreflang_alternates': alternates,
        'lang_switch_url': page_url(page_key, other_lang, absolute=False),
        'lang_switch_code': HREFLANG_CODES[page_key][other_lang],
    }


# Breadcrumb label pairs (en, ar) shared across pages that reference the hub.
_HUB_BREADCRUMB_LABEL = {'en': 'GCC Investors', 'ar': 'مستثمرو الخليج'}
_HOME_BREADCRUMB_LABEL = {'en': 'Home', 'ar': 'الرئيسية'}

_COUNTRY_BREADCRUMB_LABEL = {
    'qatar':  {'en': 'Qatar', 'ar': 'قطر'},
    'saudi':  {'en': 'Saudi Arabia', 'ar': 'السعودية'},
    'kuwait': {'en': 'Kuwait', 'ar': 'الكويت'},
}


def build_breadcrumbs(page_key: str, lang: str) -> list[dict]:
    """
    [{'label': ..., 'url': ... or None (current page, no link)}, ...] —
    also the exact structure fed to the BreadcrumbList JSON-LD builder.
    """
    home_url = '/' if lang == 'en' else '/ar/gcc-investors/'  # no Arabic homepage exists yet
    crumbs = [
        {'label': _HOME_BREADCRUMB_LABEL[lang], 'url': home_url},
    ]
    if page_key == 'hub':
        crumbs.append({'label': _HUB_BREADCRUMB_LABEL[lang], 'url': None})
    else:
        crumbs.append({'label': _HUB_BREADCRUMB_LABEL[lang], 'url': page_url(page_key='hub', lang=lang, absolute=False)})
        crumbs.append({'label': _COUNTRY_BREADCRUMB_LABEL[page_key][lang], 'url': None})
    return crumbs
