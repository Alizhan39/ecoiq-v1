"""
companies/tests_embed.py — PART 5 public embeddable badges/widgets
(companies/embed_views.py, mounted at /embed/).
"""
from django.test import TestCase

from companies.models import CompanyProfile
from league.models import Company


class EmbedBadgeTest(TestCase):
    def setUp(self):
        self.public_co = Company.objects.create(name='Public Embed Co', slug='public-embed-co')
        CompanyProfile.objects.create(company=self.public_co, status='public')

        self.draft_co = Company.objects.create(name='Draft Embed Co', slug='draft-embed-co')
        CompanyProfile.objects.create(company=self.draft_co, status='draft')

    def test_ecoiq_badge_svg_for_public_company(self):
        resp = self.client.get('/embed/public-embed-co/badge.svg')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'image/svg+xml')
        self.assertIn(b'EcoIQ Score', resp.content)

    def test_ethical_badge_svg(self):
        resp = self.client.get('/embed/public-embed-co/ethical-badge.svg')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Insufficient', resp.content)  # no evidence -> insufficient_evidence

    def test_islamic_badge_svg_labels_itself_indicative(self):
        resp = self.client.get('/embed/public-embed-co/islamic-badge.svg')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Indicative', resp.content)

    def test_risk_card_is_frame_embeddable(self):
        resp = self.client.get('/embed/public-embed-co/risk-card/')
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('X-Frame-Options', resp)
        self.assertIn(b'Powered by EcoIQ', resp.content)

    def test_risk_card_noindex(self):
        resp = self.client.get('/embed/public-embed-co/risk-card/')
        self.assertEqual(resp['X-Robots-Tag'], 'noindex')

    def test_risk_card_carries_not_a_fatwa_disclaimer(self):
        resp = self.client.get('/embed/public-embed-co/risk-card/')
        self.assertIn(b'not a fatwa', resp.content.lower())

    def test_dark_theme_query_param(self):
        resp = self.client.get('/embed/public-embed-co/risk-card/?theme=dark')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'#0d1117', resp.content)

    def test_draft_company_not_reachable_via_any_embed_endpoint(self):
        for path in ('badge.svg', 'ethical-badge.svg', 'islamic-badge.svg', 'risk-card/'):
            resp = self.client.get(f'/embed/draft-embed-co/{path}')
            self.assertEqual(resp.status_code, 404, path)

    def test_unknown_company_404s(self):
        resp = self.client.get('/embed/does-not-exist/badge.svg')
        self.assertEqual(resp.status_code, 404)

    def test_snippets_page_renders_and_noindexes(self):
        resp = self.client.get('/embed/public-embed-co/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'noindex')
        self.assertContains(resp, '/embed/public-embed-co/badge.svg')

    def test_snippets_page_404s_for_draft_company(self):
        resp = self.client.get('/embed/draft-embed-co/')
        self.assertEqual(resp.status_code, 404)
