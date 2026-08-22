"""
core/tests_spa.py — the React SPA is served by Django, and Django still owns
everything it owned before.

The catch-all is the risky part of this architecture. It matches every path
that nothing else matched, which means every mistake it can make is a mistake
about a route somebody else owns. Two of them would be silent in production:

  * an unknown /api/ path answering `200 text/html`, so an integrator sees a
    JSON parse error instead of the 404 that happened;
  * a server-owned prefix (the Stripe webhook, /admin/, /static/) being
    swallowed, so the failure shows up as a payment that never provisioned.

Both are asserted below, per prefix, from the declared list — so adding a
prefix to core/spa.py automatically adds a test for it, and removing one fails
here rather than in production.
"""
from __future__ import annotations

import re
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import get_resolver

from core import spa

#: Every public product route now served by the React app.
#:
#: `/` through `/league/` were Django template routes before the cutover and
#: kept their URL names; `/tours/`, `/labs/` and `/trust/` never existed as
#: server-rendered pages.
SPA_ROUTES = (
    '/', '/intelligence/', '/projects/', '/about/', '/contact/', '/pricing/',
    '/league/', '/tours/', '/labs/', '/trust/',
)


class SpaArtefactTests(TestCase):
    """The committed build artefact is present and well-formed."""

    def test_index_html_exists(self):
        self.assertTrue(
            spa.SPA_INDEX.exists(),
            f'{spa.SPA_INDEX} is missing. The SPA build artefact is committed '
            'to the repository — run `npm --prefix frontend/web ci && npm '
            '--prefix frontend/web run build` and commit static/spa/.')

    def test_head_injection_markers_survive_the_build(self):
        """
        Vite rewrites index.html. If it ever stripped the comment markers,
        every page would silently lose its title, description and canonical —
        the page would still render, so nothing would look broken.
        """
        self.assertIn('<!--ecoiq:head:start-->', spa.SPA_INDEX.read_text())
        self.assertIn('<!--ecoiq:head:end-->', spa.SPA_INDEX.read_text())

    def test_referenced_assets_exist_on_disk(self):
        """
        Every hashed asset the shell names is really there.

        A stale index.html referencing a bundle from a previous build produces
        a blank white page with a 404 in the console and no server-side error
        at all — the single most confusing failure this setup can have.
        """
        html = spa.SPA_INDEX.read_text()
        referenced = re.findall(r'/static/(spa/assets/[^"\']+)', html)
        self.assertTrue(referenced, 'The shell references no assets at all.')
        for asset in referenced:
            with self.subTest(asset=asset):
                self.assertTrue(
                    (spa.SPA_INDEX.parent.parent / asset).exists(),
                    f'{asset} is referenced by index.html but absent from '
                    'static/. The committed artefact is stale.')

    def test_assets_are_content_hashed(self):
        """Immutable caching is only safe because the names change."""
        html = spa.SPA_INDEX.read_text()
        for asset in re.findall(r'/static/spa/assets/([^"\']+)', html):
            with self.subTest(asset=asset):
                self.assertRegex(
                    asset, r'-[A-Za-z0-9_-]{8,}\.(?:js|css)$',
                    'Asset filenames must carry a content hash — '
                    'core/whitenoise.py caches this directory forever.')


class ImmutableAssetCachingTests(TestCase):
    """
    Vite hashes with a dash; WhiteNoise recognises Django's dot convention.

    Without core/whitenoise.py the bundle is served with the default 60-second
    cache, so every returning visitor re-validates ~180 kB on every navigation.
    Tested directly rather than through a request because WhiteNoise only
    serves from STATIC_ROOT, which exists after collectstatic and not during
    the suite.
    """

    def _middleware(self):
        from core.whitenoise import SpaAwareWhiteNoiseMiddleware
        instance = SpaAwareWhiteNoiseMiddleware(lambda request: None)
        return instance

    def test_spa_assets_are_immutable(self):
        middleware = self._middleware()
        self.assertTrue(middleware.immutable_file_test(
            '', '/static/spa/assets/index-DoM4GWeY.js'))
        self.assertTrue(middleware.immutable_file_test(
            '', '/static/spa/assets/index-Bm1aLiXm.css'))

    def test_the_shell_itself_is_never_immutable(self):
        """
        index.html is the one file whose name never changes and whose contents
        must not be stale — it is what names the hashed assets.
        """
        middleware = self._middleware()
        self.assertFalse(middleware.immutable_file_test(
            '', '/static/spa/index.html'))

    def test_unhashed_legacy_static_is_not_marked_immutable(self):
        middleware = self._middleware()
        self.assertFalse(middleware.immutable_file_test(
            '', '/static/dist/ecoiq-islands.js'))


class SpaRouteTests(TestCase):
    """Routes the React app owns."""

    def test_spa_routes_serve_the_shell(self):
        for url in SPA_ROUTES:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertIn('text/html', response['Content-Type'])
                self.assertContains(response, 'id="root"')

    def test_direct_navigation_and_refresh_are_identical(self):
        """
        A refresh is a fresh GET with no client-side router involved. If the
        server did not answer it the same way, deep links would work only when
        reached by clicking.
        """
        for url in SPA_ROUTES:
            with self.subTest(url=url):
                first = self.client.get(url)
                second = self.client.get(url)
                self.assertEqual(first.status_code, 200)
                self.assertEqual(first.content, second.content)

    def test_query_strings_do_not_change_the_shell(self):
        plain = self.client.get('/labs/')
        with_query = self.client.get('/labs/?from=email&utm_source=x')
        self.assertEqual(plain.content, with_query.content)

    def test_shell_is_not_cached(self):
        """
        The shell names hashed assets. A cached shell outlives the bundle it
        points at, and the symptom is a blank page for exactly the users whose
        browser kept it.
        """
        response = self.client.get('/trust/')
        self.assertIn('no-store', response['Cache-Control'])

    def test_unknown_frontend_path_gets_the_shell_with_404(self):
        """
        The React NotFound page for a person; the true status for a crawler.
        Serving 200 for a page that does not exist is the same category of
        untruth as serving a score for a company with no evidence.
        """
        response = self.client.get('/no-such-page-exists/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'id="root"', status_code=404)
        self.assertContains(response, '<meta name="robots" content="noindex',
                            status_code=404)


class ServerOwnedPathTests(TestCase):
    """Django's own surfaces are untouched by the catch-all."""

    def setUp(self):
        # Anonymous API throttling is cache-backed and survives between tests,
        # so a full-suite run can hand this class a 429 that reads exactly like
        # a containment regression.
        cache.clear()

    def test_healthz_is_still_a_plain_health_response(self):
        response = self.client.get('/healthz/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('text/html', response['Content-Type'])
        self.assertNotIn(b'id="root"', response.content)

    def test_admin_is_still_django_admin(self):
        response = self.client.get('/admin/')
        self.assertIn(response.status_code, (302, 200))
        self.assertNotIn(b'id="root"', response.content)

    def test_api_v2_still_returns_json(self):
        response = self.client.get('/api/v2/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/json', response['Content-Type'])

    def test_unknown_api_path_returns_json_404_not_the_shell(self):
        """
        The failure this whole module exists to prevent. An integrator whose
        URL is wrong must see a 404, not a React page that fails to parse.
        """
        for url in ('/api/v2/does-not-exist/', '/api/v1/nope/', '/api/typo'):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)
                self.assertIn('application/json', response['Content-Type'])
                self.assertNotIn(b'id="root"', response.content)

    def test_every_declared_server_owned_prefix_is_refused(self):
        """
        Driven from spa.SERVER_OWNED_PREFIXES, so the list and its coverage
        cannot drift apart.
        """
        for prefix in spa.SERVER_OWNED_PREFIXES:
            with self.subTest(prefix=prefix):
                response = self.client.get(f'/{prefix.rstrip("/")}/x-unmatched')
                self.assertNotEqual(
                    response.status_code, 200,
                    f'/{prefix} fell through to the SPA catch-all.')
                self.assertNotIn(b'id="root"', response.content)

    def test_server_generated_document_suffixes_are_refused(self):
        """A PDF reader must never be handed a web page."""
        for url in ('/nope/report.pdf', '/nope/data.json', '/nope/feed.xml',
                    '/nope/export.csv'):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn(b'id="root"', response.content)

    def test_stripe_webhook_prefix_is_not_swallowed(self):
        """
        /billing/webhook/ is registered by hand in the Stripe dashboard. If the
        catch-all answered it, payments would stop provisioning and the only
        symptom would be silence.
        """
        response = self.client.post('/billing/webhook/')
        self.assertNotIn(b'id="root"', response.content)
        self.assertNotEqual(response.status_code, 200)


class CatchAllOrderingTests(TestCase):
    """The catch-all is last, and stays last."""

    def test_catch_all_is_the_final_url_pattern(self):
        patterns = get_resolver().url_patterns
        self.assertEqual(
            getattr(patterns[-1], 'name', None), 'spa_catch_all',
            'The SPA catch-all must be the LAST entry in the root URLconf — '
            'it matches every path, so anything after it is unreachable.')

    def test_only_one_catch_all_exists(self):
        names = [getattr(p, 'name', None) for p in get_resolver().url_patterns]
        self.assertEqual(names.count('spa_catch_all'), 1)


class HeadMetadataTests(TestCase):
    """Crawlable metadata, injected per route."""

    def _head(self, url: str) -> str:
        html = self.client.get(url).content.decode()
        return html[:html.index('</head>')]

    def test_each_route_has_its_own_title_and_description(self):
        titles = set()
        for url in SPA_ROUTES:
            head = self._head(url)
            title = re.search(r'<title>(.*?)</title>', head)
            self.assertIsNotNone(title, f'{url} has no <title>')
            self.assertNotEqual(title.group(1), 'EcoIQ',
                                f'{url} still has the fallback title')
            titles.add(title.group(1))
            self.assertRegex(head, r'<meta name="description" content=".{40,}"')
        self.assertEqual(len(titles), len(SPA_ROUTES),
                         'Two routes share a title.')

    @override_settings(SITE_URL='https://ecoiq.uk')
    def test_canonical_and_open_graph(self):
        head = self._head('/trust/')
        self.assertIn('<link rel="canonical" href="https://ecoiq.uk/trust/"',
                      head)
        for prop in ('og:title', 'og:description', 'og:url', 'og:site_name'):
            with self.subTest(prop=prop):
                self.assertIn(f'property="{prop}"', head)

    def test_fallback_block_is_replaced_not_duplicated(self):
        html = self.client.get('/labs/').content.decode()
        self.assertEqual(html.count('<title>'), 1)
        self.assertNotIn('<!--ecoiq:head:start-->', html)

    def test_metadata_is_escaped(self):
        """
        Route titles are constants today; company_spa_view builds them from
        database values. An organisation named `Foo " Ltd` must not be able to
        close an attribute.
        """
        rendered = spa.head_tags(
            title='Foo " <script>alert(1)</script>',
            description="It's <b>bold</b>", path='/x/')
        self.assertNotIn('<script>', rendered)
        self.assertIn('&quot;', rendered)

    def test_shell_carries_no_numeric_assessment(self):
        """
        The document Django emits must contain no score, rank or coverage
        figure — the SPA reads those from the API, where one gate decides.
        Anything numeric here would be a second, ungated publication surface.
        """
        for url in SPA_ROUTES + ('/no-such-page/',):
            with self.subTest(url=url):
                head = self._head(url)
                self.assertNotRegex(
                    head, r'\b(?:score|rank|rating)\s*[:=]\s*\d',
                    'The shell must never carry an assessment figure.')


class SessionAuthAfterCatchAllTests(TestCase):
    """The auth boundary is unchanged by the routing change."""

    def setUp(self):
        cache.clear()
        get_user_model().objects.create_user(
            username='spa-tester', password='correct-horse-battery')

    def test_sign_in_still_works(self):
        client = Client(enforce_csrf_checks=True)
        client.get('/api/v2/session/')          # sets the CSRF cookie
        token = client.cookies['csrftoken'].value
        response = client.post(
            '/api/v2/session/sign-in/',
            data={'username': 'spa-tester', 'password': 'correct-horse-battery'},
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200, response.content[:200])
        self.assertTrue(self.client.session is not None)

    def test_sign_in_without_csrf_is_still_rejected(self):
        """
        The login-CSRF fix (api/v2_session.py) must survive the routing change.
        """
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            '/api/v2/session/sign-in/',
            data={'username': 'spa-tester', 'password': 'correct-horse-battery'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)


class CompanyPageIsStillServerRenderedTests(TestCase):
    """
    /companies/<slug>/ is NOT migrated, deliberately. The directory above it
    is.

    The server-rendered company profile carries eleven panels the React page
    does not have. Today every organisation falls through to the
    evidence-pending page so nobody sees them — but routing the URL is a claim
    to own it, and the moment one organisation becomes publishable, owning it
    would silently delete eleven public sections.

    These tests pin that decision so it is a decision, not a thing someone
    forgot. They fail if the route is cut over without the parity work.
    """

    def setUp(self):
        cache.clear()
        from companies.testing import unpopulated
        from league.models import Company

        self.company = Company.objects.create(
            name='Northwind Energy', slug='northwind-energy',
            sector='Energy', country='UK')
        unpopulated(self.company, status='public')

    def test_the_directory_is_react(self):
        """
        The directory migrated; the individual organisation page did not. They
        are separate decisions and this class pins both.
        """
        response = self.client.get('/companies/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="root"')

    def test_the_company_page_is_still_django(self):
        response = self.client.get('/companies/northwind-energy/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="root"')

    def test_an_unpublished_company_page_is_noindexed(self):
        """
        SEO decision B. The page is truthful and reachable; it is simply not
        worth indexing, and with 467 of 467 organisations in this state it
        would mean 467 indexed pages that all say the same thing.
        """
        response = self.client.get('/companies/northwind-energy/')
        self.assertContains(response, '<meta name="robots" content="noindex, follow">')

    def test_the_noindexed_page_still_carries_no_score(self):
        """
        The containment guarantee is unchanged by any of this.
        """
        html = self.client.get('/companies/northwind-energy/').content.decode()
        for forbidden in ('ratingValue', 'aggregateRating', 'ecoiq_score'):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html)


class LeagueRouteTests(TestCase):
    """The league keeps its URL, and its per-company path resolves elsewhere."""

    def setUp(self):
        cache.clear()
        from companies.testing import unpopulated
        from league.models import Company

        company = Company.objects.create(
            name='Northwind Energy', slug='northwind-energy', sector='Energy')
        unpopulated(company, status='public')

    def test_league_index_is_the_react_page(self):
        response = self.client.get('/league/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="root"')

    def test_a_league_company_url_redirects_to_the_company_page(self):
        """
        Both routes rendered league.Company by the same slug. A second React
        implementation would be two surfaces for one organisation, and two
        chances for them to disagree about what is publishable.
        """
        response = self.client.get('/league/northwind-energy/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/companies/northwind-energy/')

    def test_an_unknown_league_slug_404s_rather_than_redirecting(self):
        """
        A 302 followed by a 404 tells a crawler the URL moved before telling it
        the destination does not exist.
        """
        self.assertEqual(
            self.client.get('/league/no-such-company/').status_code, 404)

    def test_the_league_pdf_is_not_shadowed_by_the_redirect(self):
        """
        report.pdf is server-generated output. If the bare-slug redirect
        preceded it, the PDF route would silently become an HTML redirect.
        """
        response = self.client.get('/league/anything/report.pdf')
        self.assertNotEqual(response.status_code, 302)

    def test_no_score_is_embedded_in_the_league_document(self):
        """
        The regression that made all of this necessary: the server-rendered
        league gated its visible table and left fifteen companies' scores, five
        pillar values each and eight sector averages in an inline chart payload
        while the API reported INSUFFICIENT_EVIDENCE for every one of them.
        """
        html = self.client.get('/league/').content.decode()
        self.assertNotIn('ecoiq_score', html)
        self.assertNotRegex(html, r'\[\s*\d+\.\d+\s*,')


class MigratedRouteTests(TestCase):
    """Every migrated route keeps its URL name, so templates still resolve."""

    def setUp(self):
        cache.clear()

    def test_url_names_still_reverse(self):
        """
        ~100 pages are still server-rendered and link to these by name. Losing
        a name would be a NoReverseMatch on every one of them.
        """
        from django.urls import reverse

        for name, expected in (
            ('home', '/'),
            ('about', '/about/'),
            ('contact', '/contact/'),
            ('intelligence', '/intelligence/'),
            ('pricing', '/pricing/'),
            ('projects_site:index', '/projects/'),
            ('league:leaderboard', '/league/'),
        ):
            with self.subTest(name=name):
                self.assertEqual(reverse(name), expected)

    def test_every_migrated_route_serves_the_react_shell(self):
        for url in ('/', '/about/', '/contact/', '/intelligence/', '/pricing/',
                    '/projects/', '/league/'):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="root"')

    def test_no_migrated_route_still_renders_a_django_template(self):
        """
        The specific failure this guards: a route left pointing at its old view
        because the cutover missed it. The Django pages all extend base.html,
        which carries the site header — the shell carries none of it.
        """
        for url in ('/', '/about/', '/contact/', '/intelligence/', '/pricing/',
                    '/projects/', '/league/'):
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                self.assertNotIn('</header>', html)
                self.assertLess(len(html), 4000,
                                'A shell response should be ~1.5 kB. This one '
                                'looks like a rendered Django template.')


class SitemapAgreesWithTheRobotsTagTests(TestCase):
    """
    A sitemap is a request to index. It must agree with what the page says.

    Submitting a URL that carries `noindex` is a direct contradiction: Search
    Console reports it as an error, and every such URL spends crawl budget to
    be told not to index. With 467 unpublished companies, the previous sitemap
    was 467 such URLs.
    """

    def setUp(self):
        cache.clear()
        from companies.testing import unpopulated
        from league.models import Company

        self.company = Company.objects.create(
            name='Northwind Energy', slug='northwind-energy', sector='Energy')
        unpopulated(self.company, status='public')

    def test_an_unpublished_company_is_not_in_the_sitemap(self):
        body = self.client.get('/sitemap.xml').content.decode()
        self.assertNotIn('/companies/northwind-energy/', body)

    def test_the_company_page_that_is_omitted_is_the_one_carrying_noindex(self):
        page = self.client.get('/companies/northwind-energy/').content.decode()
        sitemap = self.client.get('/sitemap.xml').content.decode()

        self.assertIn('<meta name="robots" content="noindex, follow">', page)
        self.assertNotIn('/companies/northwind-energy/', sitemap)

    def test_the_static_pages_are_still_listed(self):
        body = self.client.get('/sitemap.xml').content.decode()
        for path in ('/about/', '/contact/', '/trust/', '/projects/',
                     '/intelligence/'):
            with self.subTest(path=path):
                self.assertIn(path, body)

    def test_no_listed_static_page_carries_noindex(self):
        """
        Every URL this sitemap asks to have indexed must be indexable. Checked
        by fetching them, not by reasoning about them.
        """
        import re

        body = self.client.get('/sitemap.xml').content.decode()
        locs = re.findall(r'<loc>https?://[^/]+([^<]*)</loc>', body)
        self.assertGreater(len(locs), 5)

        for path in locs:
            with self.subTest(path=path):
                response = self.client.get(path)
                if response.status_code != 200:
                    continue        # covered by their own suites
                self.assertNotIn(b'name="robots" content="noindex',
                                 response.content)


class ShellFreshnessTests(TestCase):
    """
    A cached shell that outlives its bundle renders a blank page.

    The shell names content-hashed assets. If it is cached across a rebuild it
    points at a bundle that no longer exists, and the page renders completely
    blank with a single 404 in the console and no server-side error — which
    reads as a routing bug and is not one.
    """

    def test_the_shell_is_reread_under_debug(self):
        """
        Development rebuilds constantly. Caching there guarantees the failure.
        """
        with override_settings(DEBUG=True):
            spa.reload_shell()
            first = spa._shell()
            self.assertIn('id="root"', first)
            # A second call must go back to disk, not to the cache.
            self.assertEqual(spa._cached_shell.cache_info().hits, 0)

    def test_the_shell_is_cached_when_not_debugging(self):
        """
        Production restarts the process on deploy, so the cache is always
        correct there — and a disk read per page view is not.
        """
        with override_settings(DEBUG=False):
            spa.reload_shell()
            spa._shell()
            spa._shell()
            self.assertGreaterEqual(spa._cached_shell.cache_info().hits, 1)

    def test_a_missing_artefact_fails_loudly(self):
        """
        Never a blank page. A missing build is a deploy error and must present
        as one.
        """
        from pathlib import Path

        with override_settings(DEBUG=True):
            original = spa.SPA_INDEX
            spa.SPA_INDEX = Path('/nonexistent/spa/index.html')
            try:
                with self.assertRaises(spa.SpaArtefactMissing):
                    spa._shell()
            finally:
                spa.SPA_INDEX = original
                spa.reload_shell()


class ProjectConceptMetadataTests(TestCase):
    """
    /projects/<slug>/ — a concept page that reads as a concept, even in the
    metadata a crawler sees.
    """

    def setUp(self):
        cache.clear()

    def test_the_title_names_the_concept(self):
        response = self.client.get('/projects/almaty-clean-air/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Almaty Clean Air Pilot — EcoIQ')

    def test_the_description_says_it_is_not_implemented(self):
        """
        A crawler reading only the metadata must not come away thinking EcoIQ
        has delivered this.
        """
        html = self.client.get('/projects/almaty-clean-air/').content.decode()
        head = html[:html.index('</head>')]
        self.assertIn('not implemented', head)
        self.assertIn('indicative', head)

    def test_an_unknown_concept_is_a_404(self):
        """
        Without this, every typo under /projects/ answers 200 with a page
        saying no such concept exists — a page that does not exist, reporting
        that it does.
        """
        self.assertEqual(
            self.client.get('/projects/not-a-concept/').status_code, 404)

    def test_every_concept_in_the_data_module_has_a_page(self):
        from projects.data import PROJECTS

        for concept in PROJECTS:
            with self.subTest(slug=concept['slug']):
                response = self.client.get(f'/projects/{concept["slug"]}/')
                self.assertEqual(response.status_code, 200)


class WithheldScoreIsAbsentEverywhereTests(TestCase):
    """
    The deployment-level restatement of the containment guarantee.

    Asserted here as a PAIR, in one place, for one organisation: the document
    the server sends and the API the page calls must both withhold the same
    number. Each half is covered in its own suite, but the pair is what a
    person actually experiences, and a regression that moved a score from one
    surface to the other would pass both halves separately.
    """

    def setUp(self):
        cache.clear()
        from companies import provenance as prov
        from companies.evidence import PROVENANCE_SEEDED
        from companies.scoring import recalculate_and_save
        from companies.testing import populated
        from league.models import Company

        self.company = Company.objects.create(
            name='Seeded Co', slug='seeded-co', sector='Energy',
            score_pollution_footprint=70, score_reduction_progress=70,
            score_investment=70, score_transparency=70,
            score_community_impact=70)
        profile = populated(self.company, pollution_level='low')
        # Seeded provenance can never satisfy eligibility, however much of it
        # there is — so this company HAS a stored score and must publish none.
        for key in sorted(prov.MATERIAL_METRIC_KEYS):
            prov.record(profile, key, PROVENANCE_SEEDED, written_by='t')
        recalculate_and_save(profile)
        profile.refresh_from_db()
        self.profile = profile
        self.company.refresh_from_db()

    def test_the_score_really_is_stored(self):
        """Otherwise the rest of this class proves nothing."""
        self.assertIsNotNone(self.profile.ecoiq_total_score)

    def test_it_is_absent_from_the_api(self):
        payload = self.client.get('/api/v2/companies/seeded-co/').json()

        self.assertIsNone(payload['ecoiq_score'])
        self.assertEqual(payload['score_status'], 'INSUFFICIENT_EVIDENCE')

    def test_it_is_absent_from_the_initial_html(self):
        stored = f'{self.profile.ecoiq_total_score:.1f}'
        html = self.client.get('/companies/seeded-co/').content.decode()

        self.assertNotIn(stored, html)
        self.assertNotIn('ratingValue', html)

    def test_it_is_absent_from_the_league_document_and_its_api(self):
        self.assertNotIn(
            'Seeded Co', self.client.get('/league/').content.decode())

        payload = self.client.get('/api/v2/leaderboard/').json()
        self.assertEqual(
            [row['name'] for row in payload['leaderboard']], [])

    def test_it_is_absent_from_every_react_shell_route(self):
        """
        The shell is one file. If a score ever reached it, it would reach every
        page at once.
        """
        stored = f'{self.profile.ecoiq_total_score:.1f}'
        for url in SPA_ROUTES:
            with self.subTest(url=url):
                self.assertNotIn(
                    stored, self.client.get(url).content.decode())


class TitleMapsAgreeTests(TestCase):
    """
    core/spa.py's ROUTE_META and the SPA's ROUTE_TITLES must cover the same
    routes, and agree on the text.

    There are two copies because there have to be: Django titles the document
    at request time (what a crawler reads, and what the page carries before any
    JavaScript runs), and the client re-titles on navigation (what the tab
    reads after a click). Django cannot reach into a bundle and a bundle cannot
    import a Python dict.

    Two copies are fine. Two copies that drift are not — a route renamed in one
    would leave the tab saying something the page does not. So the TypeScript
    source is read from disk and compared, which turns a silent divergence into
    a failing test.
    """

    TITLES_TS = (
        Path(__file__).resolve().parent.parent
        / 'frontend' / 'web' / 'src' / 'app' / 'documentTitle.ts'
    )

    def client_titles(self) -> dict:
        source = self.TITLES_TS.read_text(encoding='utf-8')
        block = re.search(
            r'ROUTE_TITLES:\s*Record<string,\s*string>\s*=\s*\{(.*?)\n\};',
            source, re.DOTALL)
        self.assertIsNotNone(
            block, 'ROUTE_TITLES is no longer a literal object in '
                   'documentTitle.ts, so this test can no longer read it.')
        return dict(re.findall(r"'([^']+)':\s*'([^']*)'", block.group(1)))

    def test_the_typescript_map_is_readable(self):
        self.assertGreaterEqual(len(self.client_titles()), 8)

    def test_both_maps_cover_the_same_routes(self):
        server = set(spa.ROUTE_META)
        client = set(self.client_titles())
        self.assertEqual(
            server, client,
            'core/spa.py ROUTE_META and frontend/web/src/app/documentTitle.ts '
            'ROUTE_TITLES cover different routes. Add the route to both.')

    def test_both_maps_agree_on_every_title(self):
        client = self.client_titles()
        for route, meta in spa.ROUTE_META.items():
            with self.subTest(route=route):
                self.assertEqual(
                    meta['title'], client.get(route),
                    f'The title for {route} differs between core/spa.py and '
                    'documentTitle.ts. The tab would say one thing and the '
                    'served document another.')

    def test_the_not_found_title_matches_the_catch_all(self):
        source = self.TITLES_TS.read_text(encoding='utf-8')
        served = self.client.get('/no-such-page-at-all/').content.decode()
        client_not_found = re.search(r"NOT_FOUND\s*=\s*'([^']+)'", source)

        self.assertIsNotNone(client_not_found)
        self.assertIn(f'<title>{client_not_found.group(1)}</title>', served)
