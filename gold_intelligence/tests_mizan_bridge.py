"""Contract tests for the read-only Gold Intelligence -> Mizan bridge."""
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from gold_intelligence.services.mizan_bridge import build_gold_mizan_readiness
from gold_intelligence.models import GoldProject, ProjectMembership
from mizan.system_balance import INSUFFICIENT_DATA, MIZAN_DIMENSIONS


class GoldMizanReadinessTests(SimpleTestCase):
    def project(self, **kwargs):
        return SimpleNamespace(data_sources='', is_demo=False, **kwargs)

    def test_empty_project_cannot_produce_a_mizan_score(self):
        result = build_gold_mizan_readiness(self.project())
        self.assertEqual(result['assessment'].status, INSUFFICIENT_DATA)
        self.assertEqual(result['declared_count'], 0)
        self.assertEqual(result['verified_count'], 0)
        self.assertEqual(
            {dimension.key for dimension in result['assessment'].dimensions},
            set(MIZAN_DIMENSIONS),
        )
        self.assertTrue(all(d.status == INSUFFICIENT_DATA for d in result['assessment'].dimensions))

    def test_declared_gold_inputs_are_observations_not_verified_assessments(self):
        project = self.project(
            ore_grade_g_per_tonne=1.3,
            recovery_rate_pct=89.0,
            total_capex_usd=0.0,
        )
        project.data_sources = 'Technical report awaiting independent review'
        result = build_gold_mizan_readiness(project)
        by_key = {item['field']: item for item in result['observations']}
        self.assertEqual(result['declared_count'], 3)
        self.assertEqual(by_key['total_capex_usd']['value'], 0.0)
        self.assertEqual(by_key['ore_grade_g_per_tonne']['source_status'], 'CITED_UNVERIFIED')
        self.assertEqual(by_key['annual_opex_usd']['source_status'], 'MISSING_VALUE')
        self.assertEqual(result['verified_count'], 0)
        self.assertEqual(result['assessment'].status, INSUFFICIENT_DATA)

    def test_demo_data_never_claims_independent_verification(self):
        project = self.project(recovery_rate_pct=95.0)
        project.is_demo = True
        project.data_sources = 'Synthetic source'
        result = build_gold_mizan_readiness(project)
        self.assertEqual(result['observations'][1]['source_status'], 'DEMO_UNVERIFIED')
        self.assertEqual(result['verified_count'], 0)

    def test_bad_values_stay_missing(self):
        result = build_gold_mizan_readiness(self.project(
            total_capex_usd=float('nan'),
            recovery_rate_pct=float('inf'),
            ore_grade_g_per_tonne=True,
        ))
        self.assertEqual(result['declared_count'], 0)
        self.assertEqual(result['assessment'].status, INSUFFICIENT_DATA)

    def test_does_not_modify_project_inputs(self):
        project = self.project(total_capex_usd=12_000_000)
        before = dict(vars(project))
        build_gold_mizan_readiness(project)
        self.assertEqual(vars(project), before)


class GoldMizanInvestorViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user('mizan-gold-viewer')
        cls.project = GoldProject.objects.create(
            name='Protected gold demonstration', slug='protected-gold-demo',
            is_demo=True, ore_grade_g_per_tonne=1.2,
        )
        ProjectMembership.objects.create(
            project=cls.project, user=cls.user, role=ProjectMembership.Role.VIEWER,
        )

    def test_investor_view_displays_insufficient_data_not_a_false_mizan_score(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('gold_intelligence:investor_view', args=[self.project.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['mizan_readiness']['declared_count'], 1)
        self.assertContains(response, 'Insufficient data')
        self.assertContains(response, 'Not independently verified')

    def test_nonmember_cannot_read_project_mizan_inputs(self):
        stranger = get_user_model().objects.create_user('mizan-gold-stranger')
        self.client.force_login(stranger)
        response = self.client.get(reverse('gold_intelligence:investor_view', args=[self.project.slug]))
        self.assertEqual(response.status_code, 404)
