"""
Deterministic calculation engine tests — no AI, no live market calls.
Covers: market-value calculation, stale price, missing price, classification
weighting, insufficient evidence handling, historical snapshot preservation,
sector concentration, and per-company exposure contribution.
"""
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from companies.models import CompanyProfile, InvestmentRelevanceReport
from investor_portfolio.calculations import compute_portfolio_snapshot
from investor_portfolio.methodology import CLASSIFICATION_RISK_SCORE, STALE_THRESHOLD_DAYS
from investor_portfolio.models import Holding, Portfolio, PortfolioSnapshot
from league.models import Company


def _make_company(slug, **kwargs):
    defaults = {'name': slug.title(), 'sector': 'energy', 'ticker': slug.upper()[:6]}
    defaults.update(kwargs)
    return Company.objects.create(slug=slug, **defaults)


def _published_report(profile, classification='moderate_exposure', published_at=None, content=None):
    report = InvestmentRelevanceReport.objects.create(
        company=profile, version=1, status='published', classification=classification,
        content=content or {'key_risks': [{'evidence_type': 'company_reported'}]},
        published_at=published_at or timezone.now(),
    )
    return report


class MarketValueCalculationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('carol', password='x')
        self.portfolio = Portfolio.objects.create(owner=self.user, name='P', base_currency='USD')

    def test_market_value_uses_live_price(self):
        co = _make_company('mvco', stock_price=Decimal('25.00'), stock_price_currency='USD')
        h = Holding.objects.create(portfolio=self.portfolio, company=co, shares=Decimal('4'))
        result = compute_portfolio_snapshot(self.portfolio)
        row = result['holding_snapshots'][0]
        self.assertEqual(row['market_value'], '100.00')
        self.assertFalse(row['missing_market_data'])

    def test_gbp_pence_converted_before_valuation(self):
        co = _make_company('lseco', stock_price=Decimal('2500.00'), stock_price_currency='GBp')
        Holding.objects.create(portfolio=self.portfolio, company=co, shares=Decimal('2'))
        result = compute_portfolio_snapshot(self.portfolio)
        row = result['holding_snapshots'][0]
        self.assertEqual(row['currency'], 'GBP')
        self.assertEqual(row['market_value'], '50.00')  # 2 * (2500p / 100) = £50, not £5000

    def test_manual_value_used_when_no_live_price(self):
        co = _make_company('privco')  # no ticker/price at all
        Holding.objects.create(portfolio=self.portfolio, company=co, shares=Decimal('3'),
                                manual_current_value=Decimal('75.00'))
        result = compute_portfolio_snapshot(self.portfolio)
        row = result['holding_snapshots'][0]
        self.assertEqual(row['market_value'], '75.00')
        self.assertFalse(row['missing_market_data'])
        self.assertEqual(row['currency'], 'USD')  # assumed portfolio base_currency

    def test_missing_market_data_never_shows_zero(self):
        co = _make_company('nodataco')  # no ticker, no manual value
        Holding.objects.create(portfolio=self.portfolio, company=co, shares=Decimal('9'))
        result = compute_portfolio_snapshot(self.portfolio)
        row = result['holding_snapshots'][0]
        self.assertIsNone(row['market_value'])
        self.assertTrue(row['missing_market_data'])

    def test_stale_price_flagged_but_value_preserved(self):
        co = _make_company('staleco', stock_price=Decimal('10.00'), stock_price_currency='USD',
                            stock_price_updated_at=timezone.now() - datetime.timedelta(hours=72))
        Holding.objects.create(portfolio=self.portfolio, company=co, shares=Decimal('1'))
        result = compute_portfolio_snapshot(self.portfolio)
        row = result['holding_snapshots'][0]
        self.assertTrue(row['stale_price'])
        self.assertEqual(row['market_value'], '10.00')  # still shown, not hidden

    def test_empty_portfolio_is_not_reported_as_fx_incomplete(self):
        """An empty portfolio has zero currencies in play — total is $0, not a mixed-currency warning."""
        result = compute_portfolio_snapshot(self.portfolio)
        self.assertFalse(result['fx_incomplete'])
        self.assertIsNone(result['total_market_value'])  # nothing to sum, but NOT flagged as incomplete
        self.assertEqual(result['currency_subtotals'], {})

    def test_single_currency_total_is_summed(self):
        co1 = _make_company('c1', stock_price=Decimal('10'), stock_price_currency='USD')
        co2 = _make_company('c2', stock_price=Decimal('20'), stock_price_currency='USD')
        Holding.objects.create(portfolio=self.portfolio, company=co1, shares=Decimal('1'))
        Holding.objects.create(portfolio=self.portfolio, company=co2, shares=Decimal('1'))
        result = compute_portfolio_snapshot(self.portfolio)
        self.assertFalse(result['fx_incomplete'])
        self.assertEqual(result['total_market_value'], 30.0)
        self.assertEqual(result['total_value_currency'], 'USD')

    def test_mixed_currency_total_is_incomplete_not_fabricated(self):
        co1 = _make_company('usco', stock_price=Decimal('10'), stock_price_currency='USD')
        co2 = _make_company('gbco', stock_price=Decimal('1000'), stock_price_currency='GBp')
        Holding.objects.create(portfolio=self.portfolio, company=co1, shares=Decimal('1'))
        Holding.objects.create(portfolio=self.portfolio, company=co2, shares=Decimal('1'))
        result = compute_portfolio_snapshot(self.portfolio)
        self.assertTrue(result['fx_incomplete'])
        self.assertIsNone(result['total_market_value'])
        self.assertIn('USD', result['currency_subtotals'])
        self.assertIn('GBP', result['currency_subtotals'])

    def test_gain_loss_computed_when_currencies_match(self):
        co = _make_company('gainco', stock_price=Decimal('15.00'), stock_price_currency='USD')
        Holding.objects.create(portfolio=self.portfolio, company=co, shares=Decimal('10'),
                                avg_acquisition_price=Decimal('10.00'), acquisition_currency='USD')
        result = compute_portfolio_snapshot(self.portfolio)
        row = result['holding_snapshots'][0]
        self.assertEqual(row['gain_amount'], '50.00')
        self.assertAlmostEqual(row['gain_pct'], 50.0)

    def test_gain_loss_refused_on_currency_mismatch(self):
        co = _make_company('mismatchco', stock_price=Decimal('15.00'), stock_price_currency='USD')
        Holding.objects.create(portfolio=self.portfolio, company=co, shares=Decimal('10'),
                                avg_acquisition_price=Decimal('10.00'), acquisition_currency='EUR')
        result = compute_portfolio_snapshot(self.portfolio)
        row = result['holding_snapshots'][0]
        self.assertIsNone(row['gain_amount'])  # refused rather than fabricating an FX-adjusted figure


class ExposureWeightingTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('dave', password='x')
        self.portfolio = Portfolio.objects.create(owner=self.user, name='P', base_currency='USD')

    def _holding_with_report(self, slug, classification, weight_price, sector='energy', evidence_type='verified_evidence'):
        co = _make_company(slug, sector=sector, stock_price=Decimal(str(weight_price)), stock_price_currency='USD')
        profile = CompanyProfile.objects.create(company=co, status='public')
        _published_report(profile, classification=classification,
                           content={'key_risks': [{'evidence_type': evidence_type}]})
        Holding.objects.create(portfolio=self.portfolio, company=co, shares=Decimal('1'))
        return co

    def test_classification_weighting_reflects_risk_score(self):
        self._holding_with_report('lowco', 'lower_exposure', 100)
        result = compute_portfolio_snapshot(self.portfolio)
        self.assertEqual(result['exposure_score'], CLASSIFICATION_RISK_SCORE['lower_exposure'])

    def test_two_equal_holdings_average_their_risk_scores(self):
        self._holding_with_report('lowco2', 'lower_exposure', 100)
        self._holding_with_report('highco2', 'high_exposure', 100)
        result = compute_portfolio_snapshot(self.portfolio)
        expected = (CLASSIFICATION_RISK_SCORE['lower_exposure'] + CLASSIFICATION_RISK_SCORE['high_exposure']) / 2
        self.assertAlmostEqual(result['exposure_score'], expected, delta=0.5)

    def test_insufficient_evidence_excluded_from_known_not_treated_as_low(self):
        known = self._holding_with_report('knownco', 'lower_exposure', 100)
        # a second holding with NO report at all
        unassessed = _make_company('unassessedco', stock_price=Decimal('100'), stock_price_currency='USD')
        Holding.objects.create(portfolio=self.portfolio, company=unassessed, shares=Decimal('1'))

        result = compute_portfolio_snapshot(self.portfolio)
        # exposure_score must be based ONLY on the known holding's lower_exposure score —
        # if insufficient evidence were silently treated as 0 (low risk), the score would
        # still equal lower_exposure's score, so this test also checks the *coverage* split.
        self.assertEqual(result['exposure_score'], CLASSIFICATION_RISK_SCORE['lower_exposure'])
        self.assertEqual(result['known_exposure_pct'], 50.0)
        self.assertEqual(result['unknown_exposure_pct'], 50.0)
        self.assertEqual(result['distribution']['insufficient_evidence'], 50.0)

    def test_report_with_insufficient_evidence_classification_also_counts_as_unknown(self):
        co = _make_company('ieco', stock_price=Decimal('50'), stock_price_currency='USD')
        profile = CompanyProfile.objects.create(company=co, status='public')
        _published_report(profile, classification='insufficient_evidence')
        Holding.objects.create(portfolio=self.portfolio, company=co, shares=Decimal('1'))

        result = compute_portfolio_snapshot(self.portfolio)
        self.assertIsNone(result['exposure_score'])  # nothing known to average
        self.assertEqual(result['unknown_exposure_pct'], 100.0)
        self.assertEqual(result['distribution']['insufficient_evidence'], 100.0)

    def test_evidence_confidence_affects_weighting(self):
        # Two lower_exposure holdings, one verified (weight 1.0), one ai_interpretation (weight 0.4).
        # The overall score should still equal lower_exposure's flat risk score (both same
        # classification) but coverage % should differ — verified more evenly the confidence-*.
        self._holding_with_report('vco', 'lower_exposure', 100, evidence_type='verified_evidence')
        self._holding_with_report('aico', 'lower_exposure', 100, evidence_type='ai_interpretation')
        result = compute_portfolio_snapshot(self.portfolio)
        self.assertLess(result['evidence_coverage_pct'], 100.0)  # not all verified
        self.assertGreater(result['evidence_coverage_pct'], 0.0)

    def test_stale_report_flagged_in_stale_analysis_pct(self):
        co = _make_company('staleanalysisco', stock_price=Decimal('100'), stock_price_currency='USD')
        profile = CompanyProfile.objects.create(company=co, status='public')
        _published_report(profile, classification='moderate_exposure',
                           published_at=timezone.now() - datetime.timedelta(days=STALE_THRESHOLD_DAYS + 10))
        Holding.objects.create(portfolio=self.portfolio, company=co, shares=Decimal('1'))
        result = compute_portfolio_snapshot(self.portfolio)
        self.assertEqual(result['stale_analysis_pct'], 100.0)

    def test_excluded_holding_does_not_affect_exposure_score(self):
        self._holding_with_report('includedco', 'lower_exposure', 100)
        excluded_co = self._holding_with_report('excludedco', 'high_exposure', 100)
        Holding.objects.filter(company=excluded_co).update(include_in_analytics=False)
        result = compute_portfolio_snapshot(self.portfolio)
        self.assertEqual(result['exposure_score'], CLASSIFICATION_RISK_SCORE['lower_exposure'])

    def test_sector_concentration(self):
        self._holding_with_report('energy1', 'lower_exposure', 100, sector='energy')
        self._holding_with_report('energy2', 'lower_exposure', 100, sector='energy')
        self._holding_with_report('mining1', 'lower_exposure', 100, sector='mining')
        result = compute_portfolio_snapshot(self.portfolio)
        by_sector = result['concentration']['by_sector']
        self.assertAlmostEqual(by_sector['Energy / Power'], 66.67, delta=0.5)
        self.assertAlmostEqual(by_sector['Mining'], 33.33, delta=0.5)

    def test_company_level_exposure_contribution(self):
        self._holding_with_report('bigrisk', 'high_exposure', 300)  # 75% of value
        self._holding_with_report('smallrisk', 'lower_exposure', 100)  # 25% of value
        result = compute_portfolio_snapshot(self.portfolio)
        rows = {r['company_name']: r for r in result['holding_snapshots']}
        # the high_exposure holding, with 3x the weight AND a higher risk score,
        # must contribute far more to the blended score than the small lower_exposure one
        self.assertGreater(rows['Bigrisk']['exposure_contribution'], rows['Smallrisk']['exposure_contribution'])


class SnapshotPreservationTests(TestCase):

    def test_recalculation_creates_new_snapshot_never_overwrites(self):
        user = User.objects.create_user('erin', password='x')
        portfolio = Portfolio.objects.create(owner=user, name='P', base_currency='USD')
        co = _make_company('snapco', stock_price=Decimal('10'), stock_price_currency='USD')
        Holding.objects.create(portfolio=portfolio, company=co, shares=Decimal('1'))

        result1 = compute_portfolio_snapshot(portfolio)
        snap1 = PortfolioSnapshot.objects.create(portfolio=portfolio, **result1)

        co.stock_price = Decimal('20')
        co.save()
        result2 = compute_portfolio_snapshot(portfolio)
        snap2 = PortfolioSnapshot.objects.create(portfolio=portfolio, **result2)

        self.assertNotEqual(snap1.pk, snap2.pk)
        self.assertEqual(PortfolioSnapshot.objects.filter(portfolio=portfolio).count(), 2)
        # the first snapshot's historical value must be untouched by the second calculation
        snap1.refresh_from_db()
        self.assertEqual(snap1.total_market_value, Decimal('10.00'))
        self.assertEqual(portfolio.latest_snapshot.pk, snap2.pk)
