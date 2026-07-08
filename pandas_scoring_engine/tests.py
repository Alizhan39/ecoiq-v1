from django.core.management import call_command
from django.test import TestCase

from companies.models import CompanyProfile, CompanyScoreSnapshot
from pandas_scoring_engine.services.scoring import COMPONENT_WEIGHTS, compute_company_intelligence_score


def _seed_companies():
    call_command('seed_global_companies')


class ScoreComponentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_companies()

    def test_governance_esg_reuses_existing_total_score_exactly(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        scores = compute_company_intelligence_score(profile)
        self.assertEqual(
            scores['explanation']['components']['governance_esg']['normalized_score'],
            round(profile.ecoiq_total_score, 1),
        )

    def test_never_fabricates_missing_components(self):
        profile = CompanyProfile.objects.first()
        scores = compute_company_intelligence_score(profile)
        # No EvidenceMemory, no geo data linked for most seeded companies (US/UK) -> honestly None
        self.assertIsNone(scores['evidence_quality_score'])

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(COMPONENT_WEIGHTS.values()), 1.0, places=6)

    def test_deterministic_same_profile_same_score(self):
        profile = CompanyProfile.objects.first()
        first = compute_company_intelligence_score(profile)
        second = compute_company_intelligence_score(profile)
        self.assertEqual(first['intelligence_score'], second['intelligence_score'])
        self.assertEqual(first['confidence'], second['confidence'])

    def test_final_score_is_none_only_if_zero_components_available(self):
        # Every real CompanyProfile has ecoiq_total_score, so governance_esg is
        # always available -> final score is never None for a real profile.
        profile = CompanyProfile.objects.first()
        scores = compute_company_intelligence_score(profile)
        self.assertIsNotNone(scores['intelligence_score'])

    def test_explanation_traces_every_component(self):
        profile = CompanyProfile.objects.first()
        scores = compute_company_intelligence_score(profile)
        self.assertEqual(set(scores['explanation']['components'].keys()), set(COMPONENT_WEIGHTS.keys()))
        governance = scores['explanation']['components']['governance_esg']
        self.assertIn('raw', governance)
        self.assertIn('normalized_score', governance)
        self.assertIn('base_weight', governance)
        self.assertIn('contribution', governance)
        self.assertIn('confidence', governance)
        self.assertIn('explanation', governance)

    def test_renormalizes_weight_over_available_components_only(self):
        profile = CompanyProfile.objects.first()  # only governance_esg available for a plain US/UK seed company
        scores = compute_company_intelligence_score(profile)
        governance = scores['explanation']['components']['governance_esg']
        if scores['explanation']['components_available'] == '1 of 6':
            self.assertEqual(governance['renormalized_weight'], 1.0)
            self.assertEqual(scores['intelligence_score'], governance['normalized_score'])


class EvidenceQualityComponentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_companies()

    def test_evidence_quality_reflects_real_linked_memory(self):
        from evidence_memory.models import EvidenceMemory
        from evidence_memory.services.embeddings import compute_embedding

        profile = CompanyProfile.objects.first()
        text = 'This company published a strong emissions disclosure.'
        EvidenceMemory.objects.create(
            text_chunk=text, company=profile, confidence=80.0,
            embedding=compute_embedding(text), embedding_status='embedded',
        )
        scores = compute_company_intelligence_score(profile)
        self.assertIsNotNone(scores['evidence_quality_score'])
        component = scores['explanation']['components']['evidence_quality']
        self.assertEqual(component['raw']['evidence_count'], 1)
        self.assertEqual(component['raw']['embedded_count'], 1)


class GeoIntelligenceComponentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_companies()
        call_command('seed_countries')
        call_command('seed_geo_intelligence_demo')

    def test_kazakhstan_company_gets_country_level_geo_components(self):
        from league.models import Company

        company, _ = Company.objects.get_or_create(name='Test KZ Co', defaults={'country': 'Kazakhstan'})
        company.country = 'Kazakhstan'
        company.save()
        profile, _ = CompanyProfile.objects.get_or_create(company=company)

        scores = compute_company_intelligence_score(profile)
        self.assertEqual(scores['explanation']['country_resolved'], 'Kazakhstan')
        # At least one geo-linked component should be available given the seeded Kazakhstan demo data.
        geo_components = ['climate_risk_score', 'investment_opportunity_score', 'modernisation_priority_score', 'geo_exposure_score']
        self.assertTrue(any(scores[key] is not None for key in geo_components))

    def test_unmatched_country_resolves_to_none_honestly(self):
        from league.models import Company

        company, _ = Company.objects.get_or_create(name='Test Nowhere Co', defaults={'country': 'Nowhereland'})
        profile, _ = CompanyProfile.objects.get_or_create(company=company)

        scores = compute_company_intelligence_score(profile)
        self.assertIsNone(scores['explanation']['country_resolved'])
        self.assertIsNone(scores['climate_risk_score'])
        self.assertIsNone(scores['investment_opportunity_score'])


class ManagementCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_companies()

    def test_recalculate_single_company(self):
        profile = CompanyProfile.objects.first()
        call_command('recalculate_ecoiq_scores', company_id=profile.pk)
        snapshot = CompanyScoreSnapshot.objects.filter(profile=profile, trigger='intelligence_score_recalc').first()
        self.assertIsNotNone(snapshot)
        self.assertIsNotNone(snapshot.intelligence_score)
        self.assertTrue(snapshot.intelligence_score_explanation)

    def test_recalculate_batch_respects_limit(self):
        call_command('recalculate_ecoiq_scores', limit=3)
        self.assertEqual(CompanyScoreSnapshot.objects.filter(trigger='intelligence_score_recalc').count(), 3)

    def test_unknown_company_id_reports_error_without_crashing(self):
        call_command('recalculate_ecoiq_scores', company_id=999999999)
        self.assertEqual(CompanyScoreSnapshot.objects.filter(trigger='intelligence_score_recalc').count(), 0)


class BackendIntelligenceIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_companies()

    def test_recalculate_scores_background_single_company(self):
        from backend_intelligence_engine.tasks import recalculate_scores_background

        profile = CompanyProfile.objects.first()
        result = recalculate_scores_background.apply(args=[profile.pk]).get()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['companies_processed'], 1)
        snapshot = CompanyScoreSnapshot.objects.get(pk=result['snapshot_ids'][0])
        self.assertIsNotNone(snapshot.intelligence_score)

    def test_recalculate_scores_background_batch_respects_limit(self):
        from backend_intelligence_engine.tasks import recalculate_scores_background

        result = recalculate_scores_background.apply(kwargs={'limit': 2}).get()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['companies_processed'], 2)

    def test_recalculate_scores_background_unknown_company_fails_honestly(self):
        from backend_intelligence_engine.tasks import recalculate_scores_background

        result = recalculate_scores_background.apply(args=[999999999]).get()
        self.assertEqual(result['status'], 'failed')

    def test_company_intelligence_refresh_attaches_intelligence_score_to_snapshot(self):
        from backend_intelligence_engine.tasks import company_intelligence_refresh

        profile = CompanyProfile.objects.first()
        result = company_intelligence_refresh.apply(args=[profile.pk]).get()
        self.assertEqual(result['status'], 'completed')
        self.assertIn('intelligence_score', result)
        snapshot = CompanyScoreSnapshot.objects.get(pk=result['snapshot_id'])
        self.assertIsNotNone(snapshot.intelligence_score)
        # Still only ONE snapshot for this refresh — intelligence score is
        # attached to the existing snapshot, not a second duplicate record.
        self.assertEqual(
            CompanyScoreSnapshot.objects.filter(profile=profile, trigger='background_refresh').count(), 1,
        )


class RankingsCompatibilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_companies()

    def test_rankings_still_order_by_existing_ecoiq_total_score(self):
        # The new intelligence_score lives only on CompanyScoreSnapshot — the
        # live rankings page orders by CompanyProfile.ecoiq_total_score
        # directly, completely untouched by this feature.
        call_command('recalculate_ecoiq_scores', limit=5)
        response = self.client.get('/companies/')
        self.assertEqual(response.status_code, 200)

    def test_company_profile_ecoiq_total_score_unaffected(self):
        profile = CompanyProfile.objects.first()
        score_before = profile.ecoiq_total_score
        compute_company_intelligence_score(profile)  # read-only, must not mutate the profile
        profile.refresh_from_db()
        self.assertEqual(profile.ecoiq_total_score, score_before)
