from django.core.management import call_command
from django.test import TestCase

from companies.models import CompanyProfile
from countries.models import CountryProfile
from geo_intelligence.models import GeoAsset, GeoRiskZone, InvestmentGeoOpportunity
from intelligence_analytics_engine.services import (
    clustering, evidence_distribution, outliers, ranking, recommendations, similarity,
)
from intelligence_analytics_engine.services.features import build_company_features, build_country_features


def _seed_base():
    call_command('seed_global_companies')
    call_command('seed_countries')


class FeatureBuilderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def test_company_features_has_core_columns_for_every_scored_company(self):
        df = build_company_features()
        self.assertGreater(len(df), 0)
        for col in ('public_benefit_score', 'ecoiq_total_score', 'name', 'country'):
            self.assertIn(col, df.columns)
        self.assertFalse(df['ecoiq_total_score'].isna().any())  # queryset already filters to non-null

    def test_country_features_has_geo_columns(self):
        df = build_country_features()
        self.assertEqual(len(df), CountryProfile.objects.count())
        for col in ('climate_risk_score', 'investment_opportunity_score', 'company_count'):
            self.assertIn(col, df.columns)


class CompanySimilarityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def test_returns_available_results_excluding_self(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        result = similarity.find_similar_companies(profile.pk, top_n=3)
        self.assertTrue(result['available'])
        self.assertLessEqual(len(result['results']), 3)
        self.assertNotIn(profile.pk, [r['id'] for r in result['results']])

    def test_each_result_names_its_basis(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        result = similarity.find_similar_companies(profile.pk, top_n=3)
        for r in result['results']:
            self.assertIn('most_similar_on', r)
            self.assertIn('most_different_on', r)
            self.assertIn('distance', r)

    def test_unknown_company_is_honest(self):
        result = similarity.find_similar_companies(999999999, top_n=3)
        self.assertFalse(result['available'])


class CountrySimilarityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()
        call_command('add_400_companies')

    def test_returns_available_results_for_countries_with_companies(self):
        uk = CountryProfile.objects.filter(name__icontains='United Kingdom').first()
        result = similarity.find_similar_countries(uk.pk, top_n=3)
        self.assertTrue(result['available'])


class ClusteringTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()
        call_command('seed_geo_intelligence_demo')  # gives Kazakhstan real geo data
        uk = CountryProfile.objects.get(name__icontains='United Kingdom')
        us = CountryProfile.objects.get(name__icontains='United States')
        GeoRiskZone.objects.create(
            name='UK test zone', risk_type='flood', country=uk, latitude=51.5, longitude=-0.1,
            severity='low', confidence=70, is_demo=True,
        )
        GeoRiskZone.objects.create(
            name='US test zone', risk_type='drought', country=us, latitude=39.8, longitude=-98.5,
            severity='medium', confidence=70, is_demo=True,
        )
        GeoAsset.objects.create(
            name='UK test asset', asset_type='city', latitude=51.5, longitude=-0.1, country=uk,
            climate_exposure_score=30, is_demo=True,
        )
        GeoAsset.objects.create(
            name='US test asset', asset_type='city', latitude=39.8, longitude=-98.5, country=us,
            climate_exposure_score=55, is_demo=True,
        )
        InvestmentGeoOpportunity.objects.create(
            title='UK test opp', country=uk, latitude=51.5, longitude=-0.1, investment_score=40, confidence=60,
        )
        InvestmentGeoOpportunity.objects.create(
            title='US test opp', country=us, latitude=39.8, longitude=-98.5, investment_score=65, confidence=60,
        )

    def test_climate_risk_clusters_separates_distinct_countries(self):
        result = clustering.climate_risk_clusters(n_clusters=3)
        self.assertTrue(result['available'])
        self.assertEqual(len(result['clusters']), 3)
        kazakhstan_cluster = next(c for c in result['clusters'] if any(x['name'] == 'Kazakhstan' for x in c['countries']))
        uk_cluster = next(c for c in result['clusters'] if any('United Kingdom' in x['name'] for x in c['countries']))
        self.assertNotEqual(kazakhstan_cluster['cluster_id'], uk_cluster['cluster_id'])
        self.assertGreater(kazakhstan_cluster['centroid']['climate_risk_score'], uk_cluster['centroid']['climate_risk_score'])

    def test_every_cluster_has_a_defining_feature_explanation(self):
        result = clustering.climate_risk_clusters(n_clusters=3)
        for cluster in result['clusters']:
            self.assertIn('defining_feature', cluster)
            self.assertIn('explanation', cluster)

    def test_investment_opportunity_clusters_available_with_enough_data(self):
        result = clustering.investment_opportunity_clusters(n_clusters=3)
        self.assertTrue(result['available'])

    def test_insufficient_data_reports_honestly(self):
        result = clustering.climate_risk_clusters(n_clusters=50)  # more clusters than countries with real data
        self.assertFalse(result['available'])
        self.assertIn('reason', result)


class RankingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def test_ranking_available_and_ordered(self):
        result = ranking.modernisation_priority_ranking(scope='company', top_n=5)
        self.assertTrue(result['available'])
        scores = [r['score'] for r in result['results']]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_percentiles_between_zero_and_hundred(self):
        result = ranking.modernisation_priority_ranking(scope='company', top_n=5)
        for r in result['results']:
            self.assertGreaterEqual(r['percentile'], 0)
            self.assertLessEqual(r['percentile'], 100)

    def test_falls_back_to_six_pillar_score_honestly(self):
        result = ranking.modernisation_priority_ranking(scope='company', top_n=None)
        # Most seeded companies have no Geo Intelligence link -> fallback source
        fallback_sources = [r for r in result['results'] if r['source'] == 'six_pillar_modernization_score_fallback']
        self.assertGreater(len(fallback_sources), 0)


class EvidenceQualityDistributionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def test_no_data_reports_honestly(self):
        from evidence_memory.models import EvidenceMemory
        EvidenceMemory.objects.all().delete()
        result = evidence_distribution.evidence_quality_distribution()
        self.assertFalse(result['available'])

    def test_distribution_stats_present_with_real_data(self):
        from evidence_memory.models import EvidenceMemory
        profile = CompanyProfile.objects.first()
        for confidence in (40.0, 60.0, 80.0):
            EvidenceMemory.objects.create(text_chunk='x', company=profile, confidence=confidence)

        result = evidence_distribution.evidence_quality_distribution(company=profile)
        self.assertTrue(result['available'])
        self.assertEqual(result['count'], 3)
        self.assertEqual(result['mean'], 60.0)
        self.assertIn('histogram', result)
        self.assertIn('quartiles', result)

    def test_by_source_type_breakdown(self):
        from evidence_memory.models import EvidenceMemory
        profile = CompanyProfile.objects.first()
        EvidenceMemory.objects.create(text_chunk='a', company=profile, confidence=90.0, source_type='harvester_evidence')
        EvidenceMemory.objects.create(text_chunk='b', company=profile, confidence=10.0, source_type='agent_output')

        result = evidence_distribution.evidence_quality_distribution(company=profile)
        self.assertIn('harvester_evidence', result['by_source_type'])
        self.assertIn('agent_output', result['by_source_type'])


class OutlierDetectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def test_detects_at_least_one_outlier_in_diverse_real_data(self):
        result = outliers.detect_company_outliers()
        self.assertTrue(result['available'])
        self.assertIsInstance(result['outliers'], list)

    def test_every_flagged_outlier_names_its_deviating_features(self):
        result = outliers.detect_company_outliers()
        for o in result['outliers']:
            self.assertGreater(len(o['flagged_features']), 0)
            for f in o['flagged_features']:
                self.assertIn('z_score', f)
                self.assertIn('direction', f)

    def test_lower_threshold_flags_at_least_as_many(self):
        strict = outliers.detect_company_outliers(z_threshold=3.0)
        loose = outliers.detect_company_outliers(z_threshold=1.0)
        self.assertGreaterEqual(len(loose['outliers']), len(strict['outliers']))


class RecommendationEngineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def test_returns_recommendations_with_traceable_basis(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        result = recommendations.recommend_for_company(profile.pk)
        self.assertTrue(result['available'])
        for rec in result['recommendations']:
            self.assertIn('summary', rec)
            self.assertIn('basis', rec)
            self.assertIn('source', rec)

    def test_evidence_gap_suggests_ai_agent_workbench(self):
        from evidence_memory.models import EvidenceMemory
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        EvidenceMemory.objects.filter(company=profile).delete()

        result = recommendations.recommend_for_company(profile.pk)
        evidence_gap = next((r for r in result['recommendations'] if r['type'] == 'evidence_gap'), None)
        self.assertIsNotNone(evidence_gap)
        self.assertIn('ai_agent_workbench_suggestion', evidence_gap)
        self.assertIn('workbench_url', evidence_gap['ai_agent_workbench_suggestion'])

    def test_unknown_company_is_honest(self):
        result = recommendations.recommend_for_company(999999999)
        self.assertFalse(result['available'])

    def test_never_runs_an_agent_only_suggests(self):
        from agent_runtime_model_router.models import AgentRun
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        count_before = AgentRun.objects.count()
        recommendations.recommend_for_company(profile.pk)
        self.assertEqual(AgentRun.objects.count(), count_before)
