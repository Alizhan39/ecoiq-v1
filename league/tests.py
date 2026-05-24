"""
EcoIQ Good Deeds League — test suite.
Run with: python manage.py test league --verbosity=2
"""
import datetime
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse

from .models import Company, EnvironmentalProject, Evidence, ScoreHistory
from .scoring import compute_ecoiq_score, get_tier, rerank_all


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_company(name='Test Corp', **kwargs):
    defaults = {
        'sector': 'oil_gas',
        'score_pollution_footprint': 60,
        'score_reduction_progress':  55,
        'score_investment':          50,
        'score_transparency':        65,
        'score_community_impact':    70,
    }
    defaults.update(kwargs)
    return Company.objects.create(name=name, **defaults)


def _make_project(company, **kwargs):
    defaults = {
        'name': 'Test Project',
        'project_type': 'renewable',
        'status': 'completed',
        'investment_usd': 1_000_000,
        'co2_reduction_tonnes': 5_000,
        'households_helped': 1_000,
    }
    defaults.update(kwargs)
    return EnvironmentalProject.objects.create(company=company, **defaults)


# ── Scoring unit tests ────────────────────────────────────────────────────────

class ScoringTests(TestCase):

    def test_formula_weights(self):
        score = compute_ecoiq_score(100, 100, 100, 100, 100)
        self.assertEqual(score, Decimal('100.0'))

    def test_zero_scores(self):
        score = compute_ecoiq_score(0, 0, 0, 0, 0)
        self.assertEqual(score, Decimal('0.0'))

    def test_formula_correctness(self):
        # 60*0.35 + 55*0.25 + 50*0.20 + 65*0.10 + 70*0.10
        # = 21 + 13.75 + 10 + 6.5 + 7 = 58.25
        score = compute_ecoiq_score(60, 55, 50, 65, 70)
        self.assertEqual(score, Decimal('58.2'))

    def test_tier_restorative(self):
        tier = get_tier(90)
        self.assertEqual(tier.css, 'restorative')
        self.assertIn('Restorative', tier.label)

    def test_tier_transition(self):
        self.assertEqual(get_tier(75).css, 'transition')

    def test_tier_improving(self):
        self.assertEqual(get_tier(60).css, 'improving')

    def test_tier_high_impact(self):
        self.assertEqual(get_tier(45).css, 'high-impact')

    def test_tier_polluter(self):
        self.assertEqual(get_tier(20).css, 'polluter')

    def test_tier_boundary_exact_85(self):
        self.assertEqual(get_tier(85).css, 'restorative')

    def test_tier_boundary_exact_70(self):
        self.assertEqual(get_tier(70).css, 'transition')


# ── Model tests ───────────────────────────────────────────────────────────────

class CompanyModelTests(TestCase):

    def test_ecoiq_score_computed_on_save(self):
        co = _make_company()
        # 60*0.35+55*0.25+50*0.20+65*0.10+70*0.10 = 58.25 → 58.2
        expected = Decimal('58.2')
        self.assertEqual(co.ecoiq_score, expected)

    def test_slug_auto_generated(self):
        co = _make_company('QazaqGaz National')
        self.assertEqual(co.slug, 'qazaqgaz-national')

    def test_str_repr(self):
        co = _make_company('ACME Industries')
        self.assertIn('ACME Industries', str(co))

    def test_status_label_restorative(self):
        co = _make_company(
            score_pollution_footprint=100, score_reduction_progress=100,
            score_investment=100, score_transparency=100, score_community_impact=100
        )
        self.assertEqual(co.status_label, 'Restorative Leader')

    def test_status_label_polluter(self):
        co = _make_company(
            score_pollution_footprint=0, score_reduction_progress=0,
            score_investment=0, score_transparency=0, score_community_impact=0
        )
        self.assertEqual(co.status_label, 'Major Polluter')

    def test_total_co2_sums_completed_projects(self):
        co = _make_company()
        _make_project(co, co2_reduction_tonnes=10_000, status='completed')
        _make_project(co, co2_reduction_tonnes=5_000, status='active')  # not counted
        self.assertEqual(co.total_co2_reduced, 10_000)

    def test_total_households_sums_completed(self):
        co = _make_company()
        _make_project(co, households_helped=500, status='completed')
        _make_project(co, households_helped=200, status='planned')   # not counted
        self.assertEqual(co.total_households_helped, 500)

    def test_total_investment_includes_all_statuses(self):
        co = _make_company()
        _make_project(co, investment_usd=1_000_000, status='completed')
        _make_project(co, investment_usd=500_000,   status='active')
        self.assertEqual(co.total_investment_usd, 1_500_000)


# ── rerank_all tests ──────────────────────────────────────────────────────────

class ReRankTests(TestCase):

    def test_ranks_assigned_descending(self):
        c1 = _make_company('Alpha', score_pollution_footprint=80)
        c2 = _make_company('Beta',  score_pollution_footprint=30)
        rerank_all()
        c1.refresh_from_db()
        c2.refresh_from_db()
        self.assertLess(c1.rank, c2.rank)   # higher score → lower rank number

    def test_rank_1_is_highest_score(self):
        c1 = _make_company('High', score_pollution_footprint=95)
        c2 = _make_company('Low',  score_pollution_footprint=20)
        rerank_all()
        c1.refresh_from_db()
        self.assertEqual(c1.rank, 1)


# ── View tests ────────────────────────────────────────────────────────────────

class LeaderboardViewTests(TestCase):

    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')
        self.co = _make_company('Green Corp')
        rerank_all()

    def test_leaderboard_200(self):
        r = self.client.get(reverse('league:leaderboard'))
        self.assertEqual(r.status_code, 200)

    def test_leaderboard_contains_company_name(self):
        r = self.client.get(reverse('league:leaderboard'))
        self.assertContains(r, 'Green Corp')

    def test_leaderboard_sector_filter(self):
        _make_company('Oil Co', sector='oil_gas')
        _make_company('Miner', sector='mining')
        r = self.client.get(reverse('league:leaderboard') + '?sector=mining')
        self.assertContains(r, 'Miner')
        self.assertNotContains(r, 'Oil Co')

    def test_leaderboard_is_public(self):
        """No login required."""
        self.client.logout()
        r = self.client.get(reverse('league:leaderboard'))
        self.assertEqual(r.status_code, 200)


class CompanyProfileViewTests(TestCase):

    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')
        self.co = _make_company('Energy Giant')
        _make_project(self.co)

    def test_profile_200(self):
        r = self.client.get(reverse('league:company', kwargs={'slug': self.co.slug}))
        self.assertEqual(r.status_code, 200)

    def test_profile_contains_company_name(self):
        r = self.client.get(reverse('league:company', kwargs={'slug': self.co.slug}))
        self.assertContains(r, 'Energy Giant')

    def test_profile_shows_project(self):
        r = self.client.get(reverse('league:company', kwargs={'slug': self.co.slug}))
        self.assertContains(r, 'Test Project')

    def test_profile_404_on_bad_slug(self):
        r = self.client.get(reverse('league:company', kwargs={'slug': 'does-not-exist'}))
        self.assertEqual(r.status_code, 404)

    def test_profile_is_public(self):
        self.client.logout()
        r = self.client.get(reverse('league:company', kwargs={'slug': self.co.slug}))
        self.assertEqual(r.status_code, 200)

    def test_profile_context_has_pillars(self):
        r = self.client.get(reverse('league:company', kwargs={'slug': self.co.slug}))
        self.assertEqual(len(r.context['pillars']), 5)

    def test_profile_context_has_tier(self):
        r = self.client.get(reverse('league:company', kwargs={'slug': self.co.slug}))
        self.assertIn('tier', r.context)
        self.assertIsNotNone(r.context['tier'])
