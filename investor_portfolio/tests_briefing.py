"""
AI Portfolio Briefing tests — the briefing must summarize deterministic
snapshot numbers, never calculate them, and must never contain
recommendation-style language. No live AI calls (see fake_client below).
"""
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from companies.investment_report import check_prohibited_language
from companies.models import CompanyProfile, InvestmentRelevanceReport
from investor_portfolio.briefing import build_grounding_context, generate_portfolio_briefing
from investor_portfolio.calculations import compute_portfolio_snapshot
from investor_portfolio.changes import diff_snapshots
from investor_portfolio.models import Holding, Portfolio, PortfolioBriefing, PortfolioSnapshot
from league.models import Company

CANNED = {
    'summary': 'Grounded summary referencing the given exposure score.',
    'largest_exposure_concentrations': 'Concentration in the given sector.',
    'top_contributors': 'The given top contributor company.',
    'insufficient_evidence_areas': 'The given unknown exposure percentage.',
    'changes_since_prior_snapshot': 'The given change description.',
    'due_diligence_questions': ['A grounded due-diligence question?'],
}


def _fake_client(payload=None):
    resp = SimpleNamespace(content=[SimpleNamespace(text=json.dumps(payload or CANNED))])
    return SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: resp))


def _setup_portfolio_with_snapshot(classification='elevated_exposure'):
    user = User.objects.create_user('briefinguser', password='x')
    co = Company.objects.create(slug='briefco', name='Brief Co', sector='mining', ticker='BRF',
                                 stock_price=Decimal('40'), stock_price_currency='USD')
    profile = CompanyProfile.objects.create(company=co, status='public')
    InvestmentRelevanceReport.objects.create(
        company=profile, version=1, status='published', classification=classification,
        content={'key_risks': [{'evidence_type': 'verified_evidence'}]},
    )
    portfolio = Portfolio.objects.create(owner=user, name='Brief Portfolio', base_currency='USD')
    Holding.objects.create(portfolio=portfolio, company=co, shares=Decimal('10'))
    result = compute_portfolio_snapshot(portfolio)
    snapshot = PortfolioSnapshot.objects.create(portfolio=portfolio, **result)
    return user, portfolio, snapshot


class BriefingGroundingTests(TestCase):

    def test_grounding_context_contains_real_snapshot_numbers(self):
        _user, _portfolio, snapshot = _setup_portfolio_with_snapshot()
        diff = diff_snapshots(None, snapshot)
        context = build_grounding_context(snapshot, diff)
        self.assertIn(str(snapshot.exposure_score), context)
        self.assertIn('Brief Co', context)
        self.assertIn('BRF', context)

    def test_generation_persists_versioned_briefing_linked_to_snapshot(self):
        _user, portfolio, snapshot = _setup_portfolio_with_snapshot()
        diff = diff_snapshots(None, snapshot)
        with patch('investor_portfolio.briefing._get_client', return_value=_fake_client()):
            briefing = generate_portfolio_briefing(portfolio, snapshot, diff)
        self.assertEqual(briefing.version, 1)
        self.assertEqual(briefing.snapshot, snapshot)
        self.assertEqual(briefing.status, 'draft')
        self.assertEqual(briefing.content['summary'], CANNED['summary'])

    def test_regeneration_creates_new_version(self):
        _user, portfolio, snapshot = _setup_portfolio_with_snapshot()
        diff = diff_snapshots(None, snapshot)
        with patch('investor_portfolio.briefing._get_client', return_value=_fake_client()):
            b1 = generate_portfolio_briefing(portfolio, snapshot, diff)
            b2 = generate_portfolio_briefing(portfolio, snapshot, diff)
        self.assertEqual(b1.version, 1)
        self.assertEqual(b2.version, 2)
        self.assertEqual(PortfolioBriefing.objects.filter(portfolio=portfolio).count(), 2)

    def test_briefing_defaults_to_private_draft_status(self):
        _user, portfolio, snapshot = _setup_portfolio_with_snapshot()
        diff = diff_snapshots(None, snapshot)
        with patch('investor_portfolio.briefing._get_client', return_value=_fake_client()):
            briefing = generate_portfolio_briefing(portfolio, snapshot, diff)
        self.assertEqual(briefing.status, 'draft')
        self.assertIsNone(briefing.published_at)


class BriefingProhibitedLanguageTests(TestCase):

    def test_clean_briefing_has_no_flags(self):
        _user, portfolio, snapshot = _setup_portfolio_with_snapshot()
        diff = diff_snapshots(None, snapshot)
        with patch('investor_portfolio.briefing._get_client', return_value=_fake_client()):
            briefing = generate_portfolio_briefing(portfolio, snapshot, diff)
        self.assertEqual(briefing.prohibited_language_flags, [])
        self.assertTrue(briefing.is_publishable)

    def test_recommendation_language_from_model_is_flagged(self):
        _user, portfolio, snapshot = _setup_portfolio_with_snapshot()
        diff = diff_snapshots(None, snapshot)
        bad_payload = dict(CANNED, summary='We recommend investors buy this undervalued portfolio.')
        with patch('investor_portfolio.briefing._get_client', return_value=_fake_client(bad_payload)):
            briefing = generate_portfolio_briefing(portfolio, snapshot, diff)
        self.assertTrue(briefing.prohibited_language_flags)
        self.assertFalse(briefing.is_publishable)

    def test_direct_checker_catches_portfolio_specific_prohibited_phrases(self):
        self.assertTrue(check_prohibited_language('This portfolio is a strong investment with guaranteed return.'))
        self.assertTrue(check_prohibited_language('Investors should sell these holdings now.'))
        self.assertEqual(check_prohibited_language(
            'EcoIQ does not provide investment advice or predictions of investment performance.'
        ), [])
