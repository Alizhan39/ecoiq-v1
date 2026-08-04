"""
Tests for the stock-market integration: the compact header stock strip on
companies/detail.html, the /companies/<slug>/stock/ profile page, and the
EcoIQ Investment Relevance Report (model, generation, publish workflow,
prohibited-language safety).

Mirrors the existing codebase convention (see
agent_runtime_model_router/services/model_adapters.py's own docstring):
automated tests never make a live network/LLM call. generate_investment_
relevance_report() is exercised with companies.investment_report._get_client
patched to a fake Anthropic client returning canned JSON.
"""
import datetime
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from companies.investment_report import (
    check_prohibited_language, generate_investment_relevance_report,
)
from companies.models import CompanyProfile, InvestmentRelevanceReport
from league.models import Company


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_public_company(slug='acme-energy', **kwargs):
    defaults = {
        'name': 'Acme Energy',
        'sector': 'energy',
        'country': 'United States',
        'ticker': 'ACME',
        'exchange': 'NASDAQ',
        'stock_price': Decimal('42.00'),
        'stock_price_currency': 'USD',
        'is_public': True,
        'stock_price_updated_at': datetime.datetime.now(datetime.timezone.utc),
    }
    defaults.update(kwargs)
    return Company.objects.create(slug=slug, **defaults)


def _make_profile(company, **kwargs):
    defaults = {'status': 'public', 'ecoiq_total_score': 65.0}
    defaults.update(kwargs)
    return CompanyProfile.objects.create(company=company, **defaults)


_CANNED_REPORT_JSON = {
    'classification': 'moderate_exposure',
    'executive_assessment': 'Acme Energy shows a moderate sustainability-risk profile grounded in EcoIQ data.',
    'key_risks': [
        {
            'title': 'Transparency gap', 'detail': 'Limited disclosure recorded.',
            'evidence_type': 'company_reported', 'evidence_detail': 'ai_risk_notes field',
            'confidence': 'medium',
        },
    ],
    'positive_signals': [
        {
            'title': 'Modernization progress', 'detail': 'Some transition investment noted.',
            'evidence_type': 'ai_interpretation', 'evidence_detail': 'modernization_score above average',
            'confidence': 'low',
        },
    ],
    'transition_regulatory_exposure': 'Moderate exposure to transition regulation.',
    'controversies_evidence_concerns': 'No controversies recorded in EcoIQ.',
    'sector_relative_context': 'Not enough sector peers for comparison.',
    'data_confidence': 'Profile is unverified with limited cited evidence.',
    'due_diligence_questions': ['What are the company\'s Scope 3 emissions?'],
}


def _fake_client(response_dict=None):
    """A stand-in for anthropic.Anthropic() — .messages.create(...) returns canned JSON text."""
    payload = response_dict if response_dict is not None else _CANNED_REPORT_JSON
    fake_response = SimpleNamespace(content=[SimpleNamespace(text=json.dumps(payload))])
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: fake_response))
    return client


# ── Header stock strip on companies/detail.html ────────────────────────────

class DetailPageStockStripTests(TestCase):

    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')

    def test_public_company_shows_stock_strip_near_name(self):
        co = _make_public_company()
        _make_profile(co)
        r = self.client.get(reverse('companies:detail', kwargs={'slug': co.slug}))
        self.assertContains(r, 'View stock profile')
        self.assertContains(r, 'ACME')

    def test_private_company_has_no_stock_strip_or_market_language(self):
        co = _make_public_company(
            slug='private-co', name='Private Co', ticker='', exchange='', is_public=False,
            stock_price=None, stock_price_currency='USD', stock_price_updated_at=None,
        )
        _make_profile(co)
        r = self.client.get(reverse('companies:detail', kwargs={'slug': co.slug}))
        self.assertNotContains(r, 'View stock profile')
        self.assertNotContains(r, 'stock-strip-ticker">')


# ── Stock profile page (/companies/<slug>/stock/) ──────────────────────────

class StockProfilePageTests(TestCase):

    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')

    def test_private_company_shows_not_public_message_no_price(self):
        co = _make_public_company(
            slug='private-co', ticker='', exchange='', is_public=False,
            stock_price=None, stock_price_updated_at=None,
        )
        _make_profile(co)
        r = self.client.get(reverse('companies:stock', kwargs={'slug': co.slug}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'is not publicly traded')
        self.assertNotContains(r, 'Market Data')

    def test_public_company_with_current_price(self):
        co = _make_public_company()
        _make_profile(co)
        r = self.client.get(reverse('companies:stock', kwargs={'slug': co.slug}))
        self.assertContains(r, '$42.00')
        self.assertContains(r, 'Market Data')
        self.assertNotContains(r, 'May be stale')

    def test_public_company_with_stale_price_shows_stale_badge_and_last_value(self):
        co = _make_public_company(
            stock_price_updated_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=96),
        )
        _make_profile(co)
        r = self.client.get(reverse('companies:stock', kwargs={'slug': co.slug}))
        self.assertContains(r, 'May be stale')
        # the last known price must still be shown, not hidden
        self.assertContains(r, '$42.00')

    def test_public_company_with_no_price_yet_shows_no_placeholder_zero(self):
        co = _make_public_company(stock_price=None, stock_price_updated_at=None)
        _make_profile(co)
        r = self.client.get(reverse('companies:stock', kwargs={'slug': co.slug}))
        self.assertContains(r, 'Price not yet available')
        self.assertNotContains(r, '$0.00')

    def test_internal_stock_profile_url_matches_property(self):
        co = _make_public_company()
        expected = reverse('companies:stock', kwargs={'slug': co.slug})
        self.assertEqual(co.stock_profile_url, expected)
        self.assertTrue(expected.endswith(f'/{co.slug}/stock/'))

    def test_external_tradingview_url_uses_explicit_exchange(self):
        co = _make_public_company(ticker='ACME', exchange='NASDAQ')
        self.assertEqual(co.tradingview_url, 'https://www.tradingview.com/symbols/NASDAQ:ACME/')


# ── Report model + versioning ────────────────────────────────────────────────

class ReportGenerationTests(TestCase):

    def setUp(self):
        self.co = _make_public_company()
        self.profile = _make_profile(self.co, ai_risk_notes='Supplier transparency gaps noted.')

    def test_report_creation_persists_structured_content(self):
        with patch('companies.investment_report._get_client', return_value=_fake_client()):
            report = generate_investment_relevance_report(self.profile)
        self.assertEqual(report.version, 1)
        self.assertEqual(report.status, 'draft')
        self.assertEqual(report.classification, 'moderate_exposure')
        self.assertEqual(report.content['executive_assessment'], _CANNED_REPORT_JSON['executive_assessment'])
        self.assertEqual(len(report.content['key_risks']), 1)
        self.assertTrue(report.source_snapshot)  # grounding snapshot was captured
        self.assertEqual(report.prohibited_language_flags, [])

    def test_regeneration_creates_new_version_without_touching_prior(self):
        with patch('companies.investment_report._get_client', return_value=_fake_client()):
            v1 = generate_investment_relevance_report(self.profile)
            v2 = generate_investment_relevance_report(self.profile)
        self.assertEqual(v1.version, 1)
        self.assertEqual(v2.version, 2)
        v1.refresh_from_db()
        self.assertEqual(v1.status, 'draft')  # untouched by the later generation
        self.assertEqual(InvestmentRelevanceReport.objects.filter(company=self.profile).count(), 2)

    def test_report_is_grounded_in_stored_profile_data(self):
        """The prompt sent to the model must contain real EcoIQ field values, not placeholders."""
        captured = {}

        def _capturing_create(**kwargs):
            captured['prompt'] = kwargs['messages'][0]['content']
            return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(_CANNED_REPORT_JSON))])

        fake_client = SimpleNamespace(messages=SimpleNamespace(create=_capturing_create))
        with patch('companies.investment_report._get_client', return_value=fake_client):
            generate_investment_relevance_report(self.profile)

        prompt = captured['prompt']
        self.assertIn(self.co.name, prompt)
        self.assertIn('65.0', prompt)  # ecoiq_total_score from the real profile
        self.assertIn('Supplier transparency gaps noted.', prompt)  # ai_risk_notes

    def test_insufficient_evidence_classification_is_persisted(self):
        payload = dict(_CANNED_REPORT_JSON, classification='insufficient_evidence',
                       data_confidence='Too little verified data to assess risk exposure.')
        with patch('companies.investment_report._get_client', return_value=_fake_client(payload)):
            report = generate_investment_relevance_report(self.profile)
        self.assertEqual(report.classification, 'insufficient_evidence')

    def test_invalid_classification_from_model_falls_back_to_insufficient_evidence(self):
        payload = dict(_CANNED_REPORT_JSON, classification='definitely buy this stock')
        with patch('companies.investment_report._get_client', return_value=_fake_client(payload)):
            report = generate_investment_relevance_report(self.profile)
        self.assertEqual(report.classification, 'insufficient_evidence')

    def test_prohibited_language_in_model_output_is_flagged_not_silently_dropped(self):
        payload = dict(_CANNED_REPORT_JSON,
                       executive_assessment='We recommend investors buy this undervalued stock.')
        with patch('companies.investment_report._get_client', return_value=_fake_client(payload)):
            report = generate_investment_relevance_report(self.profile)
        self.assertTrue(report.prohibited_language_flags)
        self.assertFalse(report.is_publishable)


# ── Prohibited-language checker (unit) ──────────────────────────────────────

class ProhibitedLanguageTests(TestCase):

    def test_unambiguous_terms_are_flagged(self):
        for phrase in [
            'This is a strong investment opportunity.',
            'Returns are guaranteed return on capital.',
            'The shares appear undervalued today.',
            'The shares appear overvalued today.',
            'Analysts set a price target of $50.',
            'The stock will rise sharply.',
            'The stock will fall sharply.',
        ]:
            with self.subTest(phrase=phrase):
                self.assertTrue(check_prohibited_language(phrase), phrase)

    def test_recommendation_shaped_buy_sell_hold_are_flagged(self):
        for phrase in [
            'Our hold rating reflects balanced risk.',
            'Analysts recommend a buy on this position.',
            'Investors should sell given weak fundamentals.',
            'We suggest investors buy this stock now.',
        ]:
            with self.subTest(phrase=phrase):
                self.assertTrue(check_prohibited_language(phrase), phrase)

    def test_ordinary_english_use_of_buy_sell_hold_is_not_flagged(self):
        for phrase in [
            "EcoIQ does not currently hold evidence on this exposure.",
            "The company continues to hold a strong market position in its sector.",
            "The company will sell products to industrial customers.",
            "Shareholders hold the company accountable through the AGM.",
        ]:
            with self.subTest(phrase=phrase):
                self.assertEqual(check_prohibited_language(phrase), [], phrase)

    def test_compliance_disclaimer_itself_is_not_flagged(self):
        disclaimer = (
            "EcoIQ provides environmental stewardship and sustainability-risk intelligence. "
            "It does not provide investment advice, financial recommendations or predictions "
            "of investment performance. This page, including any EcoIQ Investment Relevance "
            "Report, does not constitute a buy, sell or hold recommendation. Sustainability "
            "factors may or may not affect market value. Market data may be delayed and can "
            "become stale between updates. Users should conduct independent financial due "
            "diligence before making any investment decision."
        )
        self.assertEqual(check_prohibited_language(disclaimer), [])

    def test_empty_and_none_text_is_clean(self):
        self.assertEqual(check_prohibited_language(''), [])
        self.assertEqual(check_prohibited_language(None), [])


class RenderedStockProfileTemplateLanguageTests(TestCase):
    """Static regression guard: the actual rendered page must never contain
    live (non-negated) recommendation language, even in the disclaimer copy."""

    def test_rendered_page_has_no_live_prohibited_language(self):
        co = _make_public_company()
        _make_profile(co)
        client = Client(SERVER_NAME='localhost')
        r = client.get(reverse('companies:stock', kwargs={'slug': co.slug}))
        findings = check_prohibited_language(r.content.decode())
        self.assertEqual(findings, [], findings)


# ── Publish workflow: draft hidden publicly, published visible ─────────────

class ReportPublishWorkflowTests(TestCase):

    def setUp(self):
        self.co = _make_public_company()
        self.profile = _make_profile(self.co)
        self.staff = User.objects.create_user('staffer', password='x', is_staff=True)
        self.staff_client = Client(SERVER_NAME='localhost')
        self.staff_client.force_login(self.staff)
        self.anon_client = Client(SERVER_NAME='localhost')

    def _make_report(self, **kwargs):
        defaults = dict(
            company=self.profile, version=1, status='draft',
            classification='moderate_exposure', content=_CANNED_REPORT_JSON,
        )
        defaults.update(kwargs)
        return InvestmentRelevanceReport.objects.create(**defaults)

    def test_draft_report_hidden_from_public(self):
        self._make_report(status='draft')
        r = self.anon_client.get(reverse('companies:stock', kwargs={'slug': self.co.slug}))
        self.assertNotContains(r, _CANNED_REPORT_JSON['executive_assessment'])

    def test_draft_report_visible_to_staff(self):
        self._make_report(status='draft')
        r = self.staff_client.get(reverse('companies:stock', kwargs={'slug': self.co.slug}))
        self.assertContains(r, _CANNED_REPORT_JSON['executive_assessment'])

    def test_published_report_visible_to_public(self):
        self._make_report(status='published', published_at=datetime.datetime.now(datetime.timezone.utc))
        r = self.anon_client.get(reverse('companies:stock', kwargs={'slug': self.co.slug}))
        self.assertContains(r, _CANNED_REPORT_JSON['executive_assessment'])

    def test_no_report_yet_public_sees_clear_insufficient_message(self):
        r = self.anon_client.get(reverse('companies:stock', kwargs={'slug': self.co.slug}))
        self.assertContains(r, 'has not yet published an Investment Relevance Report')

    def test_anonymous_cannot_generate_report(self):
        r = self.anon_client.post(reverse('companies:stock_generate_report', kwargs={'slug': self.co.slug}))
        self.assertEqual(r.status_code, 403)
        self.assertEqual(InvestmentRelevanceReport.objects.count(), 0)

    def test_staff_can_move_draft_to_reviewed_to_published(self):
        report = self._make_report(status='draft')
        self.staff_client.post(
            reverse('companies:stock_report_status', kwargs={'slug': self.co.slug, 'report_id': report.pk}),
            {'action': 'mark_reviewed'},
        )
        report.refresh_from_db()
        self.assertEqual(report.status, 'reviewed')
        self.assertEqual(report.reviewed_by, self.staff)

        self.staff_client.post(
            reverse('companies:stock_report_status', kwargs={'slug': self.co.slug, 'report_id': report.pk}),
            {'action': 'publish'},
        )
        report.refresh_from_db()
        self.assertEqual(report.status, 'published')
        self.assertIsNotNone(report.published_at)

    def test_flagged_report_cannot_be_published(self):
        report = self._make_report(
            status='reviewed',
            prohibited_language_flags=[{'pattern_id': 'prohibited_investment_term', 'term': 'buy rating'}],
        )
        self.staff_client.post(
            reverse('companies:stock_report_status', kwargs={'slug': self.co.slug, 'report_id': report.pk}),
            {'action': 'publish'},
        )
        report.refresh_from_db()
        self.assertEqual(report.status, 'reviewed')  # unchanged — publish was refused
        self.assertIsNone(report.published_at)

    def test_anonymous_cannot_change_report_status(self):
        report = self._make_report(status='reviewed')
        r = self.anon_client.post(
            reverse('companies:stock_report_status', kwargs={'slug': self.co.slug, 'report_id': report.pk}),
            {'action': 'publish'},
        )
        self.assertEqual(r.status_code, 403)
        report.refresh_from_db()
        self.assertEqual(report.status, 'reviewed')
