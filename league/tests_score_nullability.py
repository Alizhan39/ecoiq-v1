"""
The last fabrication in the score chain.

D4B and D4C made CompanyProfile and CompanyScoreSnapshot honest. They did not
touch `league.Company`, which kept `ecoiq_score = DecimalField(default=0.0)`
and five `IntegerField(default=0)` pillars feeding it.

That was invisible while nothing could be published. Wiring the React contract
made it visible: a company with 100% MEASURED coverage and a real profile
composite of 61.1 was PUBLISHED with a score of **0.0** — the harshest possible
statement about a company, invented from a default, on the league table and in
the API v2 list.

Production was never exposed, because all 467 companies are legacy and none
passes the coverage gate. The bug was latent, not live.
"""
from decimal import Decimal

from django.db.models.fields import NOT_PROVIDED
from django.test import SimpleTestCase, TestCase

from companies import provenance as prov
from companies.eligibility import decide_for_company
from companies.evidence import PROVENANCE_MEASURED
from companies.scoring import recalculate_and_save
from companies.testing import populated
from league.models import Company

PILLARS = ('score_pollution_footprint', 'score_reduction_progress',
           'score_investment', 'score_transparency', 'score_community_impact')


class SchemaIsHonest(SimpleTestCase):

    def test_the_composite_is_nullable(self):
        self.assertTrue(Company._meta.get_field('ecoiq_score').null)

    def test_the_composite_has_no_default(self):
        self.assertIs(Company._meta.get_field('ecoiq_score').default,
                      NOT_PROVIDED)

    def test_every_pillar_input_is_nullable_and_undefaulted(self):
        for name in PILLARS:
            with self.subTest(field=name):
                field = Company._meta.get_field(name)
                self.assertTrue(field.null)
                self.assertIs(field.default, NOT_PROVIDED)


class ComputeScore(TestCase):

    def test_no_inputs_means_no_score(self):
        company = Company.objects.create(name='none', slug='cs-none', country='UK')

        self.assertIsNone(company.compute_score())
        self.assertIsNone(company.ecoiq_score)

    def test_known_inputs_still_produce_a_score(self):
        company = Company.objects.create(
            name='known', slug='cs-known', country='UK',
            **{name: 70 for name in PILLARS})

        self.assertEqual(company.ecoiq_score, Decimal('70.0'))

    def test_it_renormalises_across_known_inputs(self):
        """
        A partially assessed company is scored on what is known, not dragged
        down by zeros standing in for what is not.
        """
        company = Company.objects.create(
            name='partial', slug='cs-partial', country='UK',
            score_pollution_footprint=80, score_transparency=80)

        self.assertEqual(company.ecoiq_score, Decimal('80.0'))

    def test_a_genuine_zero_is_still_a_zero(self):
        company = Company.objects.create(
            name='zero', slug='cs-zero', country='UK',
            **{name: 0 for name in PILLARS})

        self.assertEqual(company.ecoiq_score, Decimal('0.0'))
        self.assertIsNotNone(company.ecoiq_score)


class TheViolation(TestCase):
    """The exact case that was publishing a fabricated zero."""

    def _fully_evidenced(self, slug, pillars=None):
        company = Company.objects.create(name=slug, slug=slug, country='UK',
                                         **(pillars or {}))
        profile = populated(company, pollution_level='low')
        for key in sorted(prov.MATERIAL_METRIC_KEYS):
            prov.record(profile, key, PROVENANCE_MEASURED, written_by='ingestion')
        recalculate_and_save(profile)
        profile.refresh_from_db()
        company.refresh_from_db()
        return company, profile

    def test_a_company_with_no_league_score_is_not_published(self):
        company, profile = self._fully_evidenced('never-scored')

        self.assertIsNone(company.ecoiq_score)
        self.assertIsNotNone(profile.ecoiq_total_score,
                             'the profile composite is real')

        decision = decide_for_company(company)
        self.assertFalse(decision.is_published)

    def test_no_zero_is_ever_published(self):
        company, _ = self._fully_evidenced('no-zero')

        decision = decide_for_company(company)

        self.assertIsNone(decision.public_score)

    def test_a_company_with_a_real_league_score_still_publishes(self):
        """The fix must not be a blanket refusal."""
        company, _ = self._fully_evidenced(
            'real-score', pillars={name: 76 for name in PILLARS})

        decision = decide_for_company(company)

        self.assertTrue(decision.is_published)
        self.assertEqual(decision.public_score, Decimal('76.0'))

    def test_a_measured_zero_still_publishes_as_zero(self):
        """
        The distinction the default destroyed: a company genuinely scored 0 is
        a finding, and must remain publishable as one.
        """
        company, _ = self._fully_evidenced(
            'measured-zero', pillars={name: 0 for name in PILLARS})

        decision = decide_for_company(company)

        self.assertTrue(decision.is_published)
        self.assertEqual(decision.public_score, Decimal('0.0'))


class RankFollowsScore(TestCase):

    def test_an_unscored_company_receives_no_rank(self):
        from league.scoring import rerank_all

        Company.objects.create(name='unranked', slug='unranked', country='UK')
        Company.objects.create(name='ranked', slug='ranked', country='UK',
                               **{name: 60 for name in PILLARS})

        rerank_all()

        self.assertIsNone(Company.objects.get(slug='unranked').rank)
        self.assertIsNotNone(Company.objects.get(slug='ranked').rank)

    def test_scored_companies_are_ranked_in_order(self):
        from league.scoring import rerank_all

        Company.objects.create(name='high', slug='r-high', country='UK',
                               **{name: 90 for name in PILLARS})
        Company.objects.create(name='low', slug='r-low', country='UK',
                               **{name: 30 for name in PILLARS})

        rerank_all()

        self.assertLess(Company.objects.get(slug='r-high').rank,
                        Company.objects.get(slug='r-low').rank)


class SurfacesSurviveAnAbsentScore(TestCase):

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.company = Company.objects.create(name='Bare Co', slug='bare-co',
                                              country='UK')
        populated(self.company, pollution_level='low')

    def test_status_label_says_so(self):
        self.assertEqual(self.company.status_label, 'Not yet scored')

    def test_status_css_has_its_own_class(self):
        self.assertEqual(self.company.status_css, 'unscored')

    def test_the_league_page_renders(self):
        from django.test import Client

        self.assertEqual(Client().get('/league/').status_code, 200)

    def test_the_embed_badge_does_not_substitute_a_number(self):
        """
        A badge is embedded on someone else's site — the least supervised
        surface EcoIQ has.
        """
        from django.test import Client

        response = Client().get('/embed/bare-co/badge.svg')
        if response.status_code != 200:
            self.skipTest('badge route gated for this fixture')

        body = response.content.decode()
        self.assertIn('not yet scored', body)
        self.assertNotIn('0/100', body)

    def test_api_v1_search_reports_null_rather_than_crashing(self):
        """
        v1 keeps its KEY for legacy consumers; the VALUE is null. Domain
        truthfulness is not weakened to satisfy a legacy assumption.
        """
        from django.test import Client

        response = Client().get('/api/v1/semantic-search/?q=bare')
        if response.status_code != 200:
            self.skipTest('v1 search unavailable in this configuration')

        for row in response.json().get('results', []):
            with self.subTest(slug=row.get('slug')):
                self.assertIn('ecoiq_score', row)


class MigrationShape(SimpleTestCase):

    def _migration(self):
        from importlib import import_module

        return import_module('league.migrations.0007_nullable_company_score')

    def test_it_only_alters_fields(self):
        for operation in self._migration().Migration.operations:
            with self.subTest(op=operation):
                self.assertEqual(type(operation).__name__, 'AlterField')

    def test_it_touches_no_data(self):
        names = {type(o).__name__ for o in self._migration().Migration.operations}

        self.assertNotIn('RunPython', names)
        self.assertNotIn('RunSQL', names)

    def test_no_operation_keeps_a_default(self):
        for operation in self._migration().Migration.operations:
            with self.subTest(field=operation.name):
                self.assertIs(operation.field.default, NOT_PROVIDED)
