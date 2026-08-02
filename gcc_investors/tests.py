"""
gcc_investors/tests.py — the 8 GCC investor pages: routes, EN/AR rendering,
canonical/hreflang, unique metadata, sitemap inclusion, JSON-LD, internal
linking. Form-submission/CSRF/UTM/consent tests for the shared enquiry form
live in leads/tests.py (InvestorEnquiryFormTests etc.) since InvestorEnquiry
is a leads-app model — see that file for those.

Mobile-horizontal-overflow and visual RTL rendering are NOT covered here
(server-rendered HTML assertions can't meaningfully test CSS layout) — see
the final report's browser-verification section for that check.
"""
import json

from django.test import TestCase, override_settings
from django.urls import reverse

from . import seo

ALL_PAGES = ['hub', 'qatar', 'saudi', 'kuwait']
ALL_LANGS = ['en', 'ar']

URL_BY_PAGE_LANG = {
    ('hub', 'en'): '/gcc-investors/',
    ('hub', 'ar'): '/ar/gcc-investors/',
    ('qatar', 'en'): '/qatar/investors/',
    ('qatar', 'ar'): '/ar/qa/investors/',
    ('saudi', 'en'): '/saudi-arabia/investors/',
    ('saudi', 'ar'): '/ar/sa/investors/',
    ('kuwait', 'en'): '/kuwait/investors/',
    ('kuwait', 'ar'): '/ar/kw/investors/',
}


class SeoHelperTests(TestCase):
    """Pure unit tests on gcc_investors/seo.py — no HTTP involved."""

    def test_page_url_matches_url_map(self):
        for (page, lang), path in URL_BY_PAGE_LANG.items():
            self.assertEqual(seo.page_url(page, lang, absolute=False), path)

    def test_hreflang_alternates_are_reciprocal(self):
        """
        Reciprocity: the EN page's alternate list must include the AR page
        (and vice versa) with matching hreflang codes on both sides.
        """
        for page in ALL_PAGES:
            en_ctx = seo.build_seo_context(page, 'en')
            ar_ctx = seo.build_seo_context(page, 'ar')

            en_alternates = dict(en_ctx['hreflang_alternates'])
            ar_alternates = dict(ar_ctx['hreflang_alternates'])

            # Every non-x-default code present on the EN page's alternate
            # list must resolve to a URL that itself lists the EN page back.
            for code, url in en_alternates.items():
                if code == 'x-default':
                    continue
                self.assertIn(url, [en_ctx['canonical_url'], ar_ctx['canonical_url']])

            self.assertEqual(en_alternates, ar_alternates, f"{page}: EN/AR alternate sets must be identical")

    def test_x_default_points_at_hub(self):
        for page in ALL_PAGES:
            for lang in ALL_LANGS:
                ctx = seo.build_seo_context(page, lang)
                alternates = dict(ctx['hreflang_alternates'])
                self.assertEqual(alternates['x-default'], seo.page_url('hub', 'en'))

    def test_country_hreflang_codes_match_spec(self):
        self.assertEqual(seo.HREFLANG_CODES['qatar'], {'en': 'en-QA', 'ar': 'ar-QA'})
        self.assertEqual(seo.HREFLANG_CODES['saudi'], {'en': 'en-SA', 'ar': 'ar-SA'})
        self.assertEqual(seo.HREFLANG_CODES['kuwait'], {'en': 'en-KW', 'ar': 'ar-KW'})

    def test_breadcrumbs_last_item_has_no_url(self):
        for page in ALL_PAGES:
            for lang in ALL_LANGS:
                crumbs = seo.build_breadcrumbs(page, lang)
                self.assertIsNone(crumbs[-1]['url'], f"{page}/{lang}: current page must not self-link")


class GccPageRouteTests(TestCase):
    """All 8 routes resolve and return 200."""

    def test_all_pages_return_200(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            with self.subTest(page=page, lang=lang):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200, f"{url} -> {r.status_code}")

    def test_url_names_resolve(self):
        names = [
            'gcc_investors:hub_en', 'gcc_investors:hub_ar',
            'gcc_investors:qatar_en', 'gcc_investors:qatar_ar',
            'gcc_investors:saudi_en', 'gcc_investors:saudi_ar',
            'gcc_investors:kuwait_en', 'gcc_investors:kuwait_ar',
        ]
        for name in names:
            self.assertTrue(reverse(name).startswith('/'))


class LangAndDirAttributeTests(TestCase):

    def test_english_pages_are_ltr(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            if lang != 'en':
                continue
            content = self.client.get(url).content.decode()
            self.assertIn('lang="en"', content, url)
            self.assertNotIn('<html lang="en" dir="rtl"', content, url)

    def test_arabic_pages_are_rtl(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            if lang != 'ar':
                continue
            content = self.client.get(url).content.decode()
            self.assertIn('lang="ar"', content, url)
            self.assertIn('dir="rtl"', content, url)

    def test_arabic_pages_render_arabic_script(self):
        r = self.client.get('/ar/qa/investors/')
        content = r.content.decode()
        # A few Arabic strings specific to the Qatar page's own content —
        # confirms real per-country Arabic copy, not a stub.
        self.assertIn('قطر', content)
        self.assertIn('الدوحة', content)


class CanonicalAndHreflangTests(TestCase):

    def test_self_referencing_canonical(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode()
            self.assertIn(f'<link rel="canonical" href="https://ecoiq.uk{url}">', content, url)

    def test_hreflang_alternate_tags_present_and_reciprocal_in_html(self):
        for page in ALL_PAGES:
            en_url = URL_BY_PAGE_LANG[(page, 'en')]
            ar_url = URL_BY_PAGE_LANG[(page, 'ar')]
            en_content = self.client.get(en_url).content.decode()
            ar_content = self.client.get(ar_url).content.decode()

            en_code = seo.HREFLANG_CODES[page]['en']
            ar_code = seo.HREFLANG_CODES[page]['ar']

            self.assertIn(f'hreflang="{en_code}" href="https://ecoiq.uk{en_url}"', en_content)
            self.assertIn(f'hreflang="{ar_code}" href="https://ecoiq.uk{ar_url}"', en_content)
            self.assertIn(f'hreflang="{en_code}" href="https://ecoiq.uk{en_url}"', ar_content)
            self.assertIn(f'hreflang="{ar_code}" href="https://ecoiq.uk{ar_url}"', ar_content)

    def test_x_default_tag_present_on_every_page(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode()
            self.assertIn('hreflang="x-default" href="https://ecoiq.uk/gcc-investors/"', content, url)

    def test_no_ip_based_redirect_hints(self):
        """
        PART D: 'no IP-based automatic redirection'. Loose smoke check --
        the English hub must never 302 based on request metadata alone.
        """
        r = self.client.get('/gcc-investors/', HTTP_ACCEPT_LANGUAGE='ar')
        self.assertEqual(r.status_code, 200)


class UniqueMetadataTests(TestCase):

    def test_all_titles_are_unique(self):
        titles = []
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode()
            start = content.find('<title>') + len('<title>')
            end = content.find('</title>')
            titles.append(content[start:end])
        self.assertEqual(len(titles), len(set(titles)), f"Duplicate <title> found: {titles}")

    def test_all_meta_descriptions_are_unique(self):
        descriptions = []
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode()
            marker = 'name="description" content="'
            start = content.find(marker) + len(marker)
            end = content.find('"', start)
            descriptions.append(content[start:end])
        self.assertEqual(len(descriptions), len(set(descriptions)), 'Duplicate meta description found')

    def test_required_titles_match_spec_exactly(self):
        """PART C gives exact required titles for 3 of the 4 English pages."""
        cases = {
            '/qatar/investors/': 'AI Startup Investment in Qatar | EcoIQ',
            '/saudi-arabia/investors/': 'Saudi AI and Vision 2030 Investment | EcoIQ',
            '/kuwait/investors/': 'Kuwait AI and FinTech Investment Opportunity | EcoIQ',
            '/gcc-investors/': 'EcoIQ GCC Investors | AI Decision Intelligence Platform',
        }
        for url, expected_title in cases.items():
            content = self.client.get(url).content.decode()
            self.assertIn(f'<title>{expected_title}</title>', content, url)

    def test_required_h1s_match_spec_exactly(self):
        cases = {
            '/qatar/investors/': 'AI decision intelligence for Qatar’s investors and institutions',
            '/saudi-arabia/investors/': 'AI decision intelligence for Saudi investment and transformation',
            '/kuwait/investors/': 'AI investment intelligence for Kuwait’s investors and institutions',
            '/gcc-investors/': 'AI decision intelligence for GCC investors and institutions',
        }
        for url, expected_h1 in cases.items():
            content = self.client.get(url).content.decode()
            self.assertIn(f'<h1>{expected_h1}</h1>', content, url)


class SitemapInclusionTests(TestCase):

    def test_all_eight_pages_in_sitemap(self):
        content = self.client.get('/sitemap.xml').content.decode()
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            self.assertIn(url, content, f"{url} missing from sitemap.xml")


class JsonLdTests(TestCase):

    def _extract_json_ld(self, content: str) -> dict:
        marker = '<script type="application/ld+json">'
        start = content.find(marker) + len(marker)
        end = content.find('</script>', start)
        return json.loads(content[start:end])

    def test_json_ld_is_valid_json_on_every_page(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode()
            data = self._extract_json_ld(content)  # raises if invalid JSON
            self.assertIn('@graph', data, url)

    def test_json_ld_graph_has_required_types(self):
        content = self.client.get('/qatar/investors/').content.decode()
        data = self._extract_json_ld(content)
        types = {node['@type'] for node in data['@graph']}
        self.assertEqual(types, {'Organization', 'WebPage', 'Service', 'BreadcrumbList'})

    def test_json_ld_breadcrumb_matches_visible_breadcrumbs(self):
        content = self.client.get('/kuwait/investors/').content.decode()
        data = self._extract_json_ld(content)
        breadcrumb_node = next(n for n in data['@graph'] if n['@type'] == 'BreadcrumbList')
        names = [item['name'] for item in breadcrumb_node['itemListElement']]
        self.assertEqual(names, ['Home', 'GCC Investors', 'Kuwait'])

    def test_json_ld_area_served_is_factual_not_invented(self):
        content = self.client.get('/saudi-arabia/investors/').content.decode()
        data = self._extract_json_ld(content)
        service_node = next(n for n in data['@graph'] if n['@type'] == 'Service')
        self.assertEqual(service_node['areaServed'], 'Saudi Arabia')

    def test_organization_json_ld_has_no_invented_sameas(self):
        """PART: 'Only include verified information in structured data.'"""
        content = self.client.get('/gcc-investors/').content.decode()
        data = self._extract_json_ld(content)
        org_node = next(n for n in data['@graph'] if n['@type'] == 'Organization')
        self.assertEqual(org_node['sameAs'], [])


class ContentDisciplineTests(TestCase):
    """
    Factual-safety checks: the spec repeatedly prohibits specific claims.
    These assert the prohibited language is genuinely absent, not just that
    the page happens to render.
    """

    def test_no_page_claims_government_endorsement(self):
        prohibited = ['endorsed by the government', 'approved by the government', 'official government partner']
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode().lower()
            for phrase in prohibited:
                self.assertNotIn(phrase, content, f"{url} contains prohibited phrase: {phrase}")

    def test_no_page_shows_buy_now_or_invest_now(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode()
            self.assertNotIn('Buy now', content, url)
            self.assertNotIn('Invest now', content, url)

    def test_every_page_has_investment_notice(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode()
            marker_en = 'does not constitute an offer of securities'
            marker_ar = 'لا تشكل عرضاً'
            self.assertTrue(marker_en in content or marker_ar in content, url)

    def test_every_page_has_independence_disclaimer(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode()
            marker_en = 'independent company'
            marker_ar = 'شركة مستقلة'
            self.assertTrue(marker_en in content or marker_ar in content, url)

    def test_islamic_screening_never_asserted_as_a_fatwa(self):
        """
        'formal fatwa' may appear ONLY inside a negation ('not a formal
        fatwa') -- never as a bare claim. See content_en.py's governance
        section for the required phrasing.
        """
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode()
            self.assertNotIn('is a fatwa', content, url)
            idx = content.find('formal fatwa')
            if idx != -1:
                preceding = content[max(0, idx - 40):idx]
                self.assertTrue(
                    'not' in preceding or 'never' in preceding or 'لا ت' in preceding,
                    f"{url}: 'formal fatwa' appears without a preceding negation: ...{preceding}",
                )


class InternalLinkingTests(TestCase):

    def test_hub_links_to_all_three_country_pages_en(self):
        content = self.client.get('/gcc-investors/').content.decode()
        self.assertIn('/qatar/investors/', content)
        self.assertIn('/saudi-arabia/investors/', content)
        self.assertIn('/kuwait/investors/', content)

    def test_hub_links_to_all_three_country_pages_ar(self):
        content = self.client.get('/ar/gcc-investors/').content.decode()
        self.assertIn('/ar/qa/investors/', content)
        self.assertIn('/ar/sa/investors/', content)
        self.assertIn('/ar/kw/investors/', content)

    def test_country_pages_link_back_to_hub(self):
        for page in ('qatar', 'saudi', 'kuwait'):
            content = self.client.get(URL_BY_PAGE_LANG[(page, 'en')]).content.decode()
            self.assertIn('/gcc-investors/', content, page)

    def test_pricing_page_and_amanah_page_link_to_gcc_hub(self):
        for url in ('/pricing/', '/amanah-autopilot/'):
            content = self.client.get(url).content.decode()
            self.assertIn('/gcc-investors/', content, url)

    def test_every_page_links_to_enquiry_form(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode()
            self.assertIn('/request-access/investors/', content, url)

    def test_every_page_links_to_pricing(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode()
            self.assertIn('/pricing/', content, url)


# ── Analytics: loader (no duplicates) ───────────────────────────────────────

@override_settings(GA4_MEASUREMENT_ID='', GTM_CONTAINER_ID='', GOOGLE_SITE_VERIFICATION='', BING_SITE_VERIFICATION='')
class AnalyticsLoaderUnconfiguredTests(TestCase):
    """Nothing loads unless the corresponding env var is set — verified per the
    task's "verify whether the site already has GA4/GTM/verification" step:
    at the time this was written it has none of them."""

    def test_no_gtm_or_gtag_script_when_unconfigured(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode()
            self.assertNotIn('googletagmanager.com/gtm.js', content, url)
            self.assertNotIn('googletagmanager.com/gtag/js', content, url)
            self.assertNotIn('google-site-verification', content, url)
            self.assertNotIn('msvalidate.01', content, url)

    def test_ecoiq_track_helper_still_defined_exactly_once(self):
        """Instrumentation code (page_view, click handlers) must never error
        even with no analytics backend configured — the core helper script
        always renders, exactly once."""
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode()
            self.assertEqual(content.count('id="ecoiq-analytics-core"'), 1, url)
            self.assertEqual(content.count('id="ecoiq-analytics-loader"'), 0, url)


@override_settings(GTM_CONTAINER_ID='GTM-TESTCODE', GA4_MEASUREMENT_ID='G-SHOULDNOTLOAD')
class AnalyticsLoaderGtmTests(TestCase):
    """When GTM is configured it owns tag firing — the raw gtag.js loader must
    never also load, even if a GA4 ID happens to be set at the same time."""

    def test_gtm_loads_gtag_does_not(self):
        content = self.client.get('/gcc-investors/').content.decode()
        # GTM's snippet builds the URL via runtime JS concatenation
        # ('.../gtm.js?id='+i+dl), so the container ID appears as the IIFE's
        # last literal argument rather than inline in the URL string.
        self.assertIn('googletagmanager.com/gtm.js?id=', content)
        self.assertIn("'GTM-TESTCODE'", content)
        self.assertNotIn('googletagmanager.com/gtag/js', content)
        self.assertNotIn('G-SHOULDNOTLOAD', content)
        self.assertEqual(content.count('id="ecoiq-analytics-loader"'), 1)

    def test_noscript_iframe_present_once(self):
        content = self.client.get('/gcc-investors/').content.decode()
        self.assertEqual(content.count('ns.html?id=GTM-TESTCODE'), 1)


@override_settings(GA4_MEASUREMENT_ID='G-TESTCODE123', GTM_CONTAINER_ID='')
class AnalyticsLoaderGtagTests(TestCase):

    def test_gtag_loads_once_gtm_absent(self):
        content = self.client.get('/gcc-investors/').content.decode()
        self.assertIn('googletagmanager.com/gtag/js?id=G-TESTCODE123', content)
        self.assertNotIn('googletagmanager.com/gtm.js', content)
        self.assertEqual(content.count('id="ecoiq-analytics-loader"'), 1)
        self.assertEqual(content.count('id="ecoiq-analytics-loader-config"'), 1)


@override_settings(GOOGLE_SITE_VERIFICATION='gsc-token-abc', BING_SITE_VERIFICATION='bing-token-def')
class SearchConsoleVerificationTests(TestCase):

    def test_verification_meta_tags_present_once(self):
        content = self.client.get('/gcc-investors/').content.decode()
        self.assertEqual(content.count('name="google-site-verification" content="gsc-token-abc"'), 1)
        self.assertEqual(content.count('name="msvalidate.01" content="bing-token-def"'), 1)


# ── Analytics: gcc_investor_page_view ───────────────────────────────────────

class PageViewEventTests(TestCase):

    def test_page_view_event_fires_once_with_correct_country_and_language(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode()
            self.assertEqual(content.count('gcc_investor_page_view'), 1, url)
            self.assertIn(f"source_country_page: '{page}'", content, url)
            self.assertIn(f"language: '{lang}'", content, url)

    def test_utm_params_preserved_into_page_view_event(self):
        content = self.client.get(
            '/qatar/investors/?utm_source=linkedin&utm_medium=social&utm_campaign=gcc-launch'
        ).content.decode()
        self.assertIn("utm_source: 'linkedin'", content)
        self.assertIn("utm_medium: 'social'", content)
        # Hyphens are escapejs-encoded (-) for safe embedding in the <script> —
        # still valid, semantically identical JS.
        self.assertIn('utm_campaign', content)
        self.assertIn('gcc', content)

    def test_no_utm_keys_emitted_when_absent_from_query_string(self):
        content = self.client.get('/kuwait/investors/').content.decode()
        self.assertNotIn('utm_source:', content)
        self.assertNotIn('utm_campaign:', content)


# ── Analytics: click-tracking data attributes ───────────────────────────────

class ClickEventMarkerTests(TestCase):

    def test_four_investor_briefing_click_markers_per_page(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode()
            self.assertEqual(content.count('data-eq-event="investor_briefing_click"'), 4, url)
            self.assertEqual(content.count(f'data-eq-country="{page}"'), 6, url)  # 4 briefing + 1 pricing + 1 langswitch

    def test_one_enterprise_pricing_click_marker_per_page(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode()
            self.assertEqual(content.count('data-eq-event="enterprise_pricing_click"'), 1, url)

    def test_one_language_switch_marker_with_correct_direction(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            content = self.client.get(url).content.decode()
            self.assertEqual(content.count('data-eq-event="investor_language_switch"'), 1, url)
            other_lang = 'ar' if lang == 'en' else 'en'
            self.assertIn(f'data-eq-from="{lang}"', content, url)
            self.assertIn(f'data-eq-to="{other_lang}"', content, url)

# ── Meta description: count, placement and length ───────────────────────────
#
# Regression cover for a Bing Webmaster Tools "Live URL" finding of
# "Meta Description too long or too short" on /gcc-investors/. The root cause
# was length (the hub description rendered at 270 characters), NOT a missing
# or duplicated tag. These tests parse the RENDERED <head> — the same thing a
# crawler sees — rather than asserting on the content_*.py dicts, so a
# template-level regression (e.g. overriding both meta_description_content and
# meta_description in base.html, which would emit two tags) is caught too.

import html as _html
import re as _re

# Bing's SEO analyser flags meta descriptions outside this range. Google
# truncates display around ~155-160 chars, so the same ceiling serves both.
META_DESC_MIN_CHARS = 25
META_DESC_MAX_CHARS = 160

_HEAD_RE = _re.compile(r'<head[^>]*>(.*?)</head>', _re.S | _re.I)
_DESC_TAG_RE = _re.compile(r'<meta[^>]+name=["\']description["\'][^>]*>', _re.I)
_DESC_CONTENT_RE = _re.compile(r'content=["\'](.*?)["\']\s*/?>', _re.S)


class MetaDescriptionTagCountTests(TestCase):

    def _fetch(self, url):
        body = self.client.get(url).content.decode()
        head_match = _HEAD_RE.search(body)
        self.assertIsNotNone(head_match, f'{url}: no parseable <head>')
        return body, head_match.group(1)

    def test_exactly_one_meta_description_in_head(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            _, head = self._fetch(url)
            tags = _DESC_TAG_RE.findall(head)
            self.assertEqual(
                len(tags), 1,
                f'{url}: expected exactly 1 <meta name="description"> in <head>, found {len(tags)}: {tags}',
            )

    def test_exactly_one_meta_description_in_whole_document(self):
        """Catches a stray duplicate emitted outside <head> (e.g. from a body
        include), which crawlers still parse and report on."""
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            body, _ = self._fetch(url)
            tags = _DESC_TAG_RE.findall(body)
            self.assertEqual(
                len(tags), 1,
                f'{url}: expected exactly 1 <meta name="description"> in the document, found {len(tags)}',
            )

    def test_meta_description_is_non_empty_and_well_formed(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            _, head = self._fetch(url)
            tag = _DESC_TAG_RE.findall(head)[0]
            content_match = _DESC_CONTENT_RE.search(tag)
            self.assertIsNotNone(content_match, f'{url}: description tag has no parseable content attribute')
            self.assertTrue(content_match.group(1).strip(), f'{url}: description content is empty')


class MetaDescriptionLengthTests(TestCase):

    def _description(self, url):
        body = self.client.get(url).content.decode()
        head = _HEAD_RE.search(body).group(1)
        tag = _DESC_TAG_RE.findall(head)[0]
        return _html.unescape(_DESC_CONTENT_RE.search(tag).group(1))

    def test_every_description_within_bing_length_range(self):
        for (page, lang), url in URL_BY_PAGE_LANG.items():
            desc = self._description(url)
            self.assertGreaterEqual(
                len(desc), META_DESC_MIN_CHARS,
                f'{url}: meta description is {len(desc)} chars, below the {META_DESC_MIN_CHARS}-char minimum',
            )
            self.assertLessEqual(
                len(desc), META_DESC_MAX_CHARS,
                f'{url}: meta description is {len(desc)} chars, above the {META_DESC_MAX_CHARS}-char maximum '
                f'(Bing reports "Meta Description too long or too short"): {desc!r}',
            )

    def test_all_eight_descriptions_unique_as_rendered(self):
        descs = {url: self._description(url) for url in URL_BY_PAGE_LANG.values()}
        self.assertEqual(len(descs), 8)
        self.assertEqual(
            len(set(descs.values())), 8,
            f'Duplicate rendered meta description across GCC investor pages: {descs}',
        )

    def test_arabic_and_english_descriptions_differ_per_country(self):
        """A page's AR description must not be a copy of its EN one — each
        language variant needs its own indexable summary."""
        for page in ALL_PAGES:
            en = self._description(URL_BY_PAGE_LANG[(page, 'en')])
            ar = self._description(URL_BY_PAGE_LANG[(page, 'ar')])
            self.assertNotEqual(en, ar, page)
