"""
The public-sector page: /public-sector/, and nothing else.

ONE ROUTE
---------
This was three — an overview, a borough demonstration and a procurement
reference page — plus a /procurement/ redirect. The demonstration and the
procurement detail are now sections of the one page, so a buyer never needs a
second URL to understand the proposition and no two URLs hold the same
subject. The tests that existed only to prove the extra routes resolved are
gone; the tests that prove the CONTENT is present moved to the vitest suites
beside the components, which can see what actually renders.

WHAT THESE TESTS ARE ACTUALLY PROTECTING
----------------------------------------
Not the layout. Two things a marketing page cannot be trusted to keep on its
own:

  1. That the routes answer 200 rather than falling to the catch-all's
     shell-with-404, and that the metadata a crawler and a link preview read is
     the metadata the page means.

  2. That the copy does not acquire a credential EcoIQ does not have. A
     procurement page is read by someone whose job is to hold a supplier to
     what it wrote, and "ISO 27001 certified" is one careless commit away on a
     page like this. So the source is scanned, not merely reviewed.

The React rendering itself is asserted in the vitest suites beside each page —
the served document is a shell with an empty <div id="root">, so a Django test
can say nothing about what the page displays and should not pretend to.
"""
from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core import spa

WEB_SRC = Path(settings.BASE_DIR) / 'frontend' / 'web' / 'src'

#: The one route, and the url name it is registered under.
ROUTES = {
    '/public-sector/': 'public_sector',
}

#: URLs this surface used to answer. Each must now be a plain 404 — not a
#: redirect, and certainly not a second copy of the page.
RETIRED = (
    '/public-sector/procurement/',
    '/public-sector/borough-demo/',
    '/procurement/',
)


class RoutingTests(TestCase):
    """Each route is registered, not merely reachable through the catch-all."""

    def setUp(self):
        cache.clear()

    def test_every_route_answers_200(self):
        for path in ROUTES:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_every_route_serves_the_react_shell(self):
        for path in ROUTES:
            with self.subTest(path=path):
                self.assertContains(self.client.get(path), 'id="root"')

    def test_every_url_name_reverses(self):
        for path, name in ROUTES.items():
            with self.subTest(name=name):
                self.assertEqual(reverse(name), path)

    def test_direct_navigation_and_refresh_are_identical(self):
        """
        The demo holds selection state in the client. A refresh must still
        return the same document — if it did not, a buyer who reloaded the page
        they were shown would get something else.
        """
        for path in ROUTES:
            with self.subTest(path=path):
                first = self.client.get(path)
                second = self.client.get(path)
                self.assertEqual(first.content, second.content)

    def test_the_retired_routes_are_gone(self):
        """
        Not redirected — gone. A 301 from /procurement/ would keep a second
        public-sector URL alive in crawlers and inbound links for years, and
        the thing it pointed at no longer exists as a page. These URLs were
        never published, never in a sitemap and never linked, so there is no
        authority to preserve and a 404 is the true answer.
        """
        for path in RETIRED:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_no_retired_route_survives_as_a_redirect(self):
        from core.redirects import PERMANENT

        for path in RETIRED:
            with self.subTest(path=path):
                self.assertNotIn(path, PERMANENT)

    def test_an_unknown_public_sector_path_is_a_404(self):
        """
        The prefix is not a catch-all. Anything under it is an unknown
        frontend path and answers as one.
        """
        response = self.client.get('/public-sector/no-such-page/')

        self.assertEqual(response.status_code, 404)


class MetadataTests(TestCase):
    """What a crawler and a link preview read."""

    def setUp(self):
        cache.clear()

    def test_the_route_has_a_title_and_a_description(self):
        body = self.client.get('/public-sector/').content.decode()

        self.assertIn('<title>Public sector — EcoIQ</title>', body)
        self.assertIsNotNone(
            re.search(r'<meta name="description" content=".+?"', body))

    def test_each_route_is_canonical_to_itself(self):
        for path in ROUTES:
            with self.subTest(path=path):
                self.assertContains(
                    self.client.get(path),
                    f'<link rel="canonical" href="{spa.site_url()}{path}"')

    def test_the_description_claims_only_what_is_supported(self):
        meta = spa.ROUTE_META['/public-sector']

        self.assertIn('public-sector', meta['description'].lower())
        for word in ('client', 'certified', 'framework', 'accredited'):
            self.assertNotIn(word, meta['description'].lower())

    def test_no_description_claims_a_credential(self):
        for path in ROUTES:
            description = spa.meta_for(path.rstrip('/'))['description'].lower()
            with self.subTest(path=path):
                for word in ('certified', 'accredited', 'approved',
                             'framework supplier', 'g-cloud'):
                    self.assertNotIn(word, description)

    def test_the_routes_are_in_the_client_title_map_too(self):
        """
        Belt and braces beside core/tests_spa.py's TitleMapsAgreeTests, which
        asserts the whole set. Named here so a public-sector route dropped from
        one map fails a test that says which surface broke.
        """
        source = (WEB_SRC / 'app' / 'documentTitle.ts').read_text(encoding='utf-8')

        for path in ROUTES:
            with self.subTest(path=path):
                self.assertIn(f"'{path.rstrip('/')}':", source)


class SitemapTests(TestCase):
    """A sitemap is a request to index, so it must agree with what exists."""

    def setUp(self):
        cache.clear()

    def test_the_page_is_listed(self):
        self.assertIn('/public-sector/',
                      self.client.get('/sitemap.xml').content.decode())

    def test_no_retired_url_is_listed(self):
        body = self.client.get('/sitemap.xml').content.decode()

        for path in RETIRED:
            with self.subTest(path=path):
                self.assertNotIn(path, body)

    def test_the_demonstration_cannot_appear_as_its_own_search_result(self):
        """
        Every figure in the demonstration is fictitious. When it had its own
        URL, a result reading "£8.4m annual energy spend" could appear stripped
        of the notice that sits beside it on the page. Embedding it removed
        that failure mode entirely rather than mitigating it — there is no
        separate URL to index.
        """
        from django.urls import NoReverseMatch, reverse

        with self.assertRaises(NoReverseMatch):
            reverse('public_sector_borough_demo')

    def test_the_listed_page_is_indexable(self):
        response = self.client.get('/public-sector/')

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'name="robots" content="noindex', response.content)



class NoRegressionTests(TestCase):
    """The routes that existed before this surface did."""

    def setUp(self):
        cache.clear()

    def test_the_existing_public_pages_still_answer(self):
        for path in ('/', '/intelligence/', '/about/', '/contact/',
                     '/pricing/', '/trust/', '/labs/', '/principles/',
                     '/projects/', '/tours/', '/league/',
                     '/industrial-modernisation/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_the_public_sector_prefix_is_not_gated(self):
        """
        It is a public product page, like /industrial-modernisation/ and
        unlike the preview beside it. An anonymous request reaches it.
        """
        from core.access import SIGN_IN_PREFIXES

        for prefix in SIGN_IN_PREFIXES:
            with self.subTest(prefix=prefix):
                self.assertFalse('/public-sector/'.startswith(prefix))

    def test_the_api_still_answers_json_under_this_prefix_free_url(self):
        """The catch-all's server-owned refusal is untouched by the new
        routes."""
        response = self.client.get('/api/v2/')

        self.assertEqual(response['Content-Type'].split(';')[0],
                         'application/json')


class PublicSectorSourceClaims(SimpleTestCase):
    """
    The copy, scanned.

    THE PATTERNS ARE AFFIRMATIVE-ONLY WHERE THEY HAVE TO BE
    -------------------------------------------------------
    A blanket ban on the word "certification" would reject the page's own
    denial — "holds no independent security certification" — which is the most
    important sentence in the section. So the bans below are on the CLAIM, and
    the denials are asserted to be present as their counterpart.

    WHAT THE PAGE SAYS INSTEAD
    --------------------------
    It once carried a section headed "What is not in place", listing at full
    size that EcoIQ holds no certification, no framework place and no delivered
    contract. Every word was true and it was still wrong for a supplier page: a
    landing page that leads with its gaps is not more honest, it is just worse
    at the job.

    What replaced it is one factual line in the procurement section —
    "does not currently hold third-party security certification" — and
    otherwise silence about credentials. Silence is not an assertion. The scan
    below enforces the half that matters: no positive claim, ever, in any
    phrasing. AbsenceDisclosureBalance further down asserts the other half —
    that the page has not swung into advertising its own weaknesses.
    """

    #: The source files that carry public-sector copy. Tests excluded: they
    #: contain the forbidden strings on purpose, as the patterns being banned.
    FILES = (
        'pages/PublicSector.tsx',
        'features/publicsector/BoroughCommandCentre.tsx',
        'features/publicsector/content.ts',
        'features/publicsector/demoData.ts',
        'features/publicsector/economics.ts',
        'features/publicsector/AssetDetail.tsx',
        'features/publicsector/AssetList.tsx',
        'features/publicsector/ApprovalGate.tsx',
        'features/publicsector/DemonstrationNotice.tsx',
        'features/publicsector/EstateOverview.tsx',
        'features/publicsector/EvidencePanel.tsx',
        'features/publicsector/MrvLoop.tsx',
        'features/publicsector/NarrativeStrip.tsx',
    )

    #: Words that cannot appear at all, in any phrasing, because there is no
    #: honest sentence on these pages that needs them.
    FORBIDDEN_WORDS = (
        'G-Cloud', 'Cyber Essentials', 'ISO 27001', 'ISO27001', 'SOC 2',
        'SOC2', 'CCS framework', 'Digital Outcomes', 'NHS framework',
        'government approved', 'government-approved', 'framework supplier',
        'fully compliant', 'GDPR compliant', 'GDPR certified',
        'certified', 'accredited',
    )

    def _sources(self):
        return {name: (WEB_SRC / name).read_text(encoding='utf-8')
                for name in self.FILES}

    def test_every_scanned_file_exists(self):
        """Guards the guard: a scan over a moved file passes trivially."""
        for name in self.FILES:
            with self.subTest(name=name):
                self.assertTrue((WEB_SRC / name).is_file(),
                                f'{name} is gone; update this scan.')

    def test_no_file_claims_a_credential_or_a_framework_place(self):
        offenders = []
        for name, source in self._sources().items():
            lowered = source.lower()
            for word in self.FORBIDDEN_WORDS:
                if word.lower() in lowered:
                    offenders.append(f'{name}: {word}')

        self.assertEqual(offenders, [],
                         f'unsupported procurement claims: {offenders}')

    def test_the_assurance_position_is_stated_somewhere(self):
        """
        The counterpart of the ban above. Saying nothing at all about
        certification would also pass the scan, and a buyer whose process
        requires one would find out late. One line, in the procurement
        section, is the balance this page settles on.
        """
        content = (WEB_SRC / 'features' / 'publicsector' / 'content.ts') \
            .read_text(encoding='utf-8')

        self.assertIn(
            'does not currently hold third-party security certification',
            content)

    def test_no_file_claims_a_client_or_a_delivered_saving(self):
        """
        Affirmative phrasings only, for the reason in this class's docstring:
        the pages DENY having a client, and "no reference customer and no
        verified client saving" is the sentence doing that work. A substring
        ban on "verified client" rejected exactly that sentence when this test
        was first written, which would have pushed the page toward saying
        nothing rather than toward saying something true.
        """
        offenders = []
        for name, source in self._sources().items():
            lowered = source.lower()
            for phrase in ('our clients', 'our customers', 'trusted by',
                           'delivered savings of', 'savings we have verified',
                           'proven savings', 'client results'):
                if phrase in lowered:
                    offenders.append(f'{name}: {phrase}')

        self.assertEqual(offenders, [])

    def test_the_demonstration_denies_being_a_client_outcome(self):
        """
        The one client-related statement that must survive, because without it
        a reader could take the borough figures for a delivered result. It is a
        label on the DATA, not a statement about the company — which is why it
        belongs in the dataset and not in the sales copy.
        """
        demo = (WEB_SRC / 'features' / 'publicsector' / 'demoData.ts') \
            .read_text(encoding='utf-8')

        self.assertIn('no real organisation, asset, saving or client ', demo)

    def test_the_commercial_ranges_carry_their_basis(self):
        content = (WEB_SRC / 'features' / 'publicsector' / 'content.ts') \
            .read_text(encoding='utf-8')

        self.assertIn('Indicative engagement sizes for budget planning',
                      content)
        # Wrapped across a string concatenation in the source, so matched in
        # halves rather than by reflowing the file.
        self.assertIn('Scope and commercial ', content)
        self.assertIn("+ 'terms are agreed per engagement", content)

    def test_microsoft_integration_is_stated_as_an_option_not_a_feature(self):
        content = (WEB_SRC / 'features' / 'publicsector' / 'content.ts') \
            .read_text(encoding='utf-8')

        self.assertIn('scoped and built as part of the', content)
        self.assertIn("+ 'engagement.'", content)

    def test_data_residency_is_not_claimed_as_uk(self):
        """
        Production runs in a United States region. This is the single easiest
        claim on a UK public-sector page to get wrong and the most damaging.
        """
        for name, source in self._sources().items():
            lowered = source.lower()
            with self.subTest(name=name):
                for phrase in ('uk data residency', 'data held in the uk',
                               'uk-hosted', 'hosted in the uk'):
                    self.assertNotIn(phrase, lowered)

        content = (WEB_SRC / 'features' / 'publicsector' / 'content.ts') \
            .read_text(encoding='utf-8')
        # What it says instead of a residency claim: the architecture is
        # region-agnostic, so residency is a deployment decision. That is
        # verifiable — render.yaml parameterises the region for both the web
        # service and the database, and nothing else is region-pinned.
        self.assertIn('no region-specific dependency', content)


class DemonstrationDataLabelling(SimpleTestCase):
    """
    The demo dataset says what it is, in the data rather than in a template.

    frontend/web/src/features/publicsector/demoData.test.ts walks every
    quantity in the module and fails on any that is not `illustrative`. This
    asserts the Python side of the same contract: that the label exists, that
    it is unambiguous, and that the walking test is still there to enforce it.
    """

    MODULE = WEB_SRC / 'features' / 'publicsector' / 'demoData.ts'
    SUITE = WEB_SRC / 'features' / 'publicsector' / 'demoData.test.ts'

    def test_the_notice_is_unambiguous(self):
        source = self.MODULE.read_text(encoding='utf-8')

        self.assertIn('FICTITIOUS DEMONSTRATION DATASET', source)
        self.assertIn('Fictitious demonstration dataset.', source)
        self.assertIn('client', source)

    def test_no_quantity_is_marked_measured(self):
        source = self.MODULE.read_text(encoding='utf-8')

        self.assertNotIn("basis: 'measured'", source)
        self.assertNotIn("basis: 'derived'", source)
        self.assertIn("basis: 'illustrative'", source)

    def test_the_dataset_names_no_real_organisation(self):
        source = self.MODULE.read_text(encoding='utf-8')

        # Asset labels are roles ("School A"), never invented institution
        # names — an invented school name is indistinguishable from a real one.
        for banned in ('Council of', 'Borough of', 'NHS Trust', 'Academy'):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, source)

    def test_the_walking_guard_still_exists(self):
        """
        The Python assertions above are a substring check. The real guarantee
        is the TypeScript suite that walks the object graph, and this fails
        loudly if it is deleted.
        """
        suite = self.SUITE.read_text(encoding='utf-8')

        self.assertIn('every quantity is marked illustrative', suite)
        self.assertIn("q.basis !== 'illustrative'", suite)


class SupplierInformation(SimpleTestCase):
    """The one block a buyer copies verbatim onto a form."""

    CONTENT = WEB_SRC / 'features' / 'publicsector' / 'content.ts'

    def test_it_states_the_registered_supplier(self):
        content = self.CONTENT.read_text(encoding='utf-8')

        self.assertIn(
            'EcoIQ is a technology product and service delivered by '
            'Stoke Share Ltd.', content)
        self.assertIn("companyNumber: '14347320'", content)
        self.assertIn("jurisdiction: 'England & Wales'", content)

    def test_it_does_not_dress_registration_up_as_a_procurement_status(self):
        content = self.CONTENT.read_text(encoding='utf-8')

        self.assertIn('a buyer can verify it independently', content)


class NarrativeConsistency(SimpleTestCase):
    """
    The seven-step story is the page's spine, and it must stay the same seven
    steps in both places it appears.
    """

    CONTENT = WEB_SRC / 'features' / 'publicsector' / 'content.ts'
    DEMO = WEB_SRC / 'features' / 'publicsector' / 'demoData.ts'

    def test_the_buyer_narrative_has_all_seven_steps(self):
        content = self.CONTENT.read_text(encoding='utf-8')
        block = re.search(r'export const NARRATIVE: NarrativeStep\[\] = \[(.*?)\n\];',
                          content, re.DOTALL)
        self.assertIsNotNone(block)

        names = re.findall(r"name: '([^']+)'", block.group(1))
        self.assertEqual(names, [
            'Find waste', 'Compare interventions', 'Inspect evidence',
            'Human approval', 'Implement', 'Measure', 'Verify savings'])

    def test_the_mrv_loop_ends_at_a_verified_outcome(self):
        demo = self.DEMO.read_text(encoding='utf-8')
        block = re.search(r'export const MRV_STAGES: MrvStage\[\] = \[(.*?)\n\];',
                          demo, re.DOTALL)
        self.assertIsNotNone(block)

        keys = re.findall(r"key: '([^']+)'", block.group(1))
        self.assertEqual(keys, ['baseline', 'intervention', 'measurement',
                                'normalisation', 'actual', 'variance',
                                'verified'])

    def test_the_internal_mrv_workflow_is_not_replaced_by_it(self):
        """
        The buyer-facing seven steps are a reading of the internal eight-step
        workflow, not a replacement for it. If impact_mrv_layer's workflow were
        deleted in favour of this, the simplification would have become a
        removal — which the brief for this work explicitly rules out.
        """
        from impact_mrv_layer.views import MRV_WORKFLOW

        self.assertEqual(len(MRV_WORKFLOW), 8)
        self.assertEqual(MRV_WORKFLOW[0]['title'], 'Measure Baseline')
        self.assertEqual(MRV_WORKFLOW[-1]['title'], 'Generate Report')


class AbsenceDisclosureBalance(SimpleTestCase):
    """
    The counterweight to PublicSectorSourceClaims.

    That class stops the page claiming things EcoIQ does not have. This one
    stops the correction from overshooting into the opposite failure: a
    supplier page that reads as an internal due-diligence report.

    The distinction being enforced is placement and prominence, not honesty.
    Every fact these patterns ban is still true, and several are still stated —
    in ASSURANCE, in the engagement-capabilities list, in the demonstration's
    own notice — worded for a procurement file and sitting where a buyer looks
    for them. What may not happen is a gap being given a heading, a chip, or a
    sentence in the sales copy.
    """

    FILES = PublicSectorSourceClaims.FILES

    #: Phrasings that market an absence. Each was on the page at some point.
    ADVERTISED_ABSENCES = (
        'what is not in place',
        'not claimed as production',
        'built, not currently deployed',
        'not provisioned',
        'no reference customer',
        'has not yet delivered a public-sector contract',
        'delivered no public-sector engagement',
        'no place on any public buying framework',
        'no standard published sla',
        'no published organisation-wide retention schedule',
        'no failover',
        'no staging environment',
        'depends on a person noticing',
        'there is no self-serve',
        'no off-platform copy',
        'has not been rehearsed',
        'united states hosting region',
        'no figure here has been validated',
    )

    def _rendered_copy(self) -> dict:
        """
        Source minus comments.

        Comments carry the REASONING for these decisions and quote the old
        wording verbatim — this file's own docstrings do too. Scanning them
        would fail on the explanation of why the page no longer says a thing,
        which is precisely the note a future reader needs most.
        """
        import re

        out = {}
        for name in self.FILES:
            text = (WEB_SRC / name).read_text(encoding='utf-8')
            text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
            text = re.sub(r'^\s*//.*$', '', text, flags=re.MULTILINE)
            out[name] = text
        return out

    def test_comments_are_actually_stripped(self):
        """Guards the guard: if the stripper failed, every test here passes
        vacuously on a file full of the banned phrases."""
        stripped = self._rendered_copy()['features/publicsector/content.ts']

        self.assertNotIn('WHY THIS IS TWO LISTS', stripped)
        self.assertIn('COMMERCIAL_BANDS', stripped)

    def test_no_absence_is_marketed_in_the_rendered_copy(self):
        offenders = []
        for name, text in self._rendered_copy().items():
            lowered = ' '.join(text.lower().split())
            for phrase in self.ADVERTISED_ABSENCES:
                if phrase in lowered:
                    offenders.append(f'{name}: {phrase}')

        self.assertEqual(
            offenders, [],
            'the public-sector page is advertising a weakness rather than '
            f'disclosing it where a buyer looks for it: {offenders}')

    def test_the_page_has_no_section_headed_with_a_gap(self):
        page = (WEB_SRC / 'pages' / 'PublicSector.tsx').read_text(encoding='utf-8')

        for heading in ('What is not in place', 'Limitations', 'Known gaps',
                        'Caveats'):
            with self.subTest(heading=heading):
                self.assertNotIn(f'>{heading}<', page)

    def test_the_disclosures_that_must_survive_still_do(self):
        """
        The floor under all of the above. Three things are load-bearing for
        truthfulness and are asserted present, not merely permitted:
        the certification position, the residency position, and the
        demonstration's own label.
        """
        content = (WEB_SRC / 'features' / 'publicsector' / 'content.ts') \
            .read_text(encoding='utf-8')
        demo = (WEB_SRC / 'features' / 'publicsector' / 'demoData.ts') \
            .read_text(encoding='utf-8')

        self.assertIn('does not currently hold third-party security '
                      'certification', content)
        self.assertIn('no region-specific dependency', content)
        self.assertIn('Fictitious demonstration dataset.', demo)
