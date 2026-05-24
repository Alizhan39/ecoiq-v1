"""
EcoIQ CMS — test suite.
Run with: python manage.py test cms --verbosity=2
"""
from django.test import TestCase, Client
from django.urls import reverse

from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTestCase

from .models import HomePage, CompanyIndexPage, CompanyPage, ArticlePage, MethodologyPage


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_home():
    """
    Return (root_page, home_page) — creates them if missing.
    Site hostname = 'localhost' to match Django test client SERVER_NAME.
    Pages at /pages/ (root) and /pages/<child-slug>/ (children).
    """
    root = Page.objects.filter(depth=1).first()
    home_qs = HomePage.objects.all()
    if not home_qs.exists():
        # Wagtail may have created a default page with slug='home' — rename it.
        from wagtail.models import Page as WP
        conflict = WP.objects.filter(depth=2, slug='home').first()
        if conflict and not isinstance(conflict.specific, HomePage):
            conflict.slug = 'wagtail-default'
            conflict.save(update_fields=['slug'])

        home = HomePage(
            title='Test EcoIQ Home',
            slug='test-ecoiq-home',
            intro='<p>Test intro.</p>',
        )
        root.add_child(instance=home)
        home.save_revision().publish()
    else:
        home = home_qs.first()

    # Site must use 'localhost' (Django test client default SERVER_NAME)
    Site.objects.update_or_create(
        is_default_site=True,
        defaults={'hostname': 'localhost', 'port': 80, 'root_page': home, 'site_name': 'Test'}
    )
    return root, home


def _make_company_page(parent):
    page = CompanyPage(
        title='QazaqGaz Profile',
        slug='qazaqgaz-profile',
        company_slug='qazaqgaz',
        hero_intro='<p>National gas operator.</p>',
    )
    parent.add_child(instance=page)
    page.save_revision().publish()
    return page


# ── Block import tests ────────────────────────────────────────────────────────

class BlockImportTests(TestCase):

    def test_all_blocks_importable(self):
        from cms.blocks import (
            KPICardBlock, CO2MetricsBlock, ScoreBreakdownBlock,
            ComparisonTableBlock, ProjectShowcaseBlock, TimelineBlock,
            EvidenceCarouselBlock, RecommendationBlock, RichTextSectionBlock,
            ImageBlock, CallToActionBlock,
            CompanyPageBody, ArticlePageBody, HomePageBody,
        )
        self.assertIsNotNone(CompanyPageBody)

    def test_score_breakdown_block_no_company(self):
        """ScoreBreakdownBlock.get_context() handles missing company gracefully."""
        from cms.blocks import ScoreBreakdownBlock
        block = ScoreBreakdownBlock()
        ctx = block.get_context({'company_slug': 'does-not-exist-xyz', 'title': 'Test', 'show_trend_chart': False, 'show_pillar_bars': True})
        self.assertIsNone(ctx.get('company'))

    def test_comparison_block_no_companies(self):
        """ComparisonTableBlock.get_context() with empty slugs returns empty list."""
        from cms.blocks import ComparisonTableBlock
        block = ComparisonTableBlock()
        ctx = block.get_context({'title': 'Test', 'company_slugs': 'nope\nalso-nope'})
        self.assertEqual(ctx.get('companies'), [])


# ── AI prep tests ─────────────────────────────────────────────────────────────

class AIPrepTests(TestCase):

    def test_pdf_extractor_is_stub(self):
        from cms.ai_prep import PDFExtractor
        ext = PDFExtractor()
        with self.assertRaises(NotImplementedError):
            ext.extract_kpis('dummy.pdf', 'qazaqgaz')

    def test_recommendation_engine_is_stub(self):
        from cms.ai_prep import RecommendationEngine
        eng = RecommendationEngine()
        with self.assertRaises(NotImplementedError):
            eng.generate('qazaqgaz')

    def test_anomaly_detector_is_stub(self):
        from cms.ai_prep import AnomalyDetector
        det = AnomalyDetector()
        with self.assertRaises(NotImplementedError):
            det.detect('qazaqgaz')

    def test_registry_has_all_features(self):
        from cms.ai_prep import AI_FEATURES
        expected = {'pdf_extraction', 'recommendations', 'anomaly_detection',
                    'narrative_generation', 'risk_scoring'}
        self.assertEqual(set(AI_FEATURES.keys()), expected)


# ── Page model tests ──────────────────────────────────────────────────────────

class CMSPageModelTests(TestCase):

    def setUp(self):
        self.root, self.home = _make_home()

    def test_home_page_can_be_created(self):
        self.assertIsNotNone(self.home)
        self.assertIsInstance(self.home, HomePage)

    def test_company_index_page_can_be_created(self):
        cip = CompanyIndexPage(title='Companies', slug='test-companies')
        self.home.add_child(instance=cip)
        self.assertTrue(CompanyIndexPage.objects.filter(slug='test-companies').exists())

    def test_company_page_can_be_created(self):
        cip = CompanyIndexPage(title='Cos', slug='test-cos-idx')
        self.home.add_child(instance=cip)
        cp = CompanyPage(title='ACME Corp', slug='acme', company_slug='acme-slug')
        cip.add_child(instance=cp)
        self.assertEqual(cp.company_slug, 'acme-slug')

    def test_methodology_page_can_be_created(self):
        mp = MethodologyPage(title='Method', slug='test-method')
        self.home.add_child(instance=mp)
        self.assertTrue(MethodologyPage.objects.exists())

    def test_article_page_can_be_created(self):
        import datetime
        ap = ArticlePage(
            title='Test Article', slug='test-article',
            published_date=datetime.date.today(),
            author='Test Author',
            intro='Short intro.',
        )
        self.home.add_child(instance=ap)
        self.assertTrue(ArticlePage.objects.filter(slug='test-article').exists())


# ── View / URL tests ──────────────────────────────────────────────────────────

class CMSPageViewTests(TestCase):
    """
    Wagtail URL routing:
      /pages/            → site root page (HomePage)
      /pages/<slug>/     → child of root
      /pages/<s1>/<s2>/  → grandchild

    Site hostname = 'localhost'; test client uses SERVER_NAME='localhost'.
    """

    def setUp(self):
        # SERVER_NAME='localhost' must match Site.hostname in _make_home()
        self.client = Client(SERVER_NAME='localhost')
        self.root, self.home = _make_home()

    def test_wagtail_home_page_200(self):
        """Root of /pages/ serves the HomePage."""
        r = self.client.get('/pages/')
        self.assertEqual(r.status_code, 200)

    def test_cms_admin_redirects_to_login(self):
        r = self.client.get('/cms-admin/')
        self.assertIn(r.status_code, [200, 302])

    def test_company_index_page_200(self):
        cip = CompanyIndexPage(title='Companies', slug='test-companies-view')
        self.home.add_child(instance=cip)
        cip.save_revision().publish()
        # child of root → /pages/test-companies-view/
        r = self.client.get('/pages/test-companies-view/')
        self.assertEqual(r.status_code, 200)

    def test_company_page_no_linked_company_200(self):
        """CompanyPage without a valid company_slug renders gracefully (no crash)."""
        cip = CompanyIndexPage(title='Cos', slug='test-cos-view')
        self.home.add_child(instance=cip)
        cp = CompanyPage(title='Unknown Corp', slug='unknown-corp', company_slug='no-such-company')
        cip.add_child(instance=cp)
        cp.save_revision().publish()
        # grandchild → /pages/test-cos-view/unknown-corp/
        r = self.client.get('/pages/test-cos-view/unknown-corp/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Unknown Corp')

    def test_existing_routes_untouched(self):
        """All pre-Wagtail routes still work — league, audit, login."""
        c = Client(SERVER_NAME='localhost')
        for url, expected in [
            ('/league/', 200),
            ('/login/', 200),
            ('/', 200),
        ]:
            r = c.get(url)
            self.assertEqual(r.status_code, expected, msg=f'{url} returned {r.status_code}')

    def test_methodology_page_renders(self):
        mp = MethodologyPage(title='How We Score', slug='test-method-view')
        self.home.add_child(instance=mp)
        mp.save_revision().publish()
        r = self.client.get('/pages/test-method-view/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'How We Score')
