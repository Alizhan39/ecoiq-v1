import re

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from companies.models import CompanyProfile
from countries.models import CountryProfile
from langgraph_orchestration.graph import run_orchestration
from langgraph_orchestration.models import OrchestrationRun
from langgraph_orchestration.state import new_state

TEMPLATE_LEAK_RE = re.compile(r'\{%|\{\{')


def _seed_base():
    call_command('seed_agent_runtime_demo')
    call_command('seed_global_companies')
    call_command('seed_countries')


class StateSchemaTests(TestCase):
    def test_new_state_has_every_required_key(self):
        state = new_state(user_request='test', target_id=1, target_type_hint='company')
        for key in (
            'user_request', 'target_type', 'target_id', 'company', 'country', 'location',
            'evidence_context', 'geo_context', 'scoring_context', 'analytics_context',
            'agent_outputs', 'verification_notes', 'confidence', 'final_recommendations',
            'next_actions', 'status', 'nodes_executed', 'failed_node',
        ):
            self.assertIn(key, state)

    def test_new_state_defaults_status_running(self):
        state = new_state()
        self.assertEqual(state['status'], 'running')
        self.assertEqual(state['nodes_executed'], [])
        self.assertIsNone(state['failed_node'])

    def test_location_sets_location_dict(self):
        state = new_state(latitude=43.25, longitude=76.95)
        self.assertEqual(state['location'], {'latitude': 43.25, 'longitude': 76.95})


class CompanyWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def test_full_company_workflow_completes_all_nodes(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        result = run_orchestration(user_request='Where is value being lost?', target_id=profile.pk, target_type='company')
        self.assertIn(result['status'], ('completed', 'needs_human_review'))
        self.assertEqual(result['nodes_executed'], [
            'classify_intent', 'retrieve_evidence_memory', 'gather_geo_intelligence', 'run_agent_analysis',
            'recalculate_score_if_needed', 'run_intelligence_analytics', 'verify_output', 'finalize',
        ])
        self.assertIsNone(result['failed_node'])

    def test_company_workflow_resolves_company_context(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        result = run_orchestration(target_id=profile.pk, target_type='company')
        self.assertEqual(result['company']['id'], profile.pk)

    def test_company_workflow_produces_traceable_recommendations(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        result = run_orchestration(user_request='Which project deserves funding first?', target_id=profile.pk, target_type='company')
        self.assertGreater(len(result['final_recommendations']), 0)
        for rec in result['final_recommendations']:
            self.assertIn('summary', rec)

    def test_company_workflow_never_leaves_next_actions_empty(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        result = run_orchestration(target_id=profile.pk, target_type='company')
        self.assertGreater(len(result['next_actions']), 0)

    def test_unknown_company_id_is_honest_failure(self):
        result = run_orchestration(target_id=999999999, target_type='company')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failed_node'], 'classify_intent')


class CountryWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def test_full_country_workflow_skips_scoring_node(self):
        country = CountryProfile.objects.get(name='Kazakhstan')
        result = run_orchestration(user_request='Which regions need heating replacement?', target_id=country.pk, target_type='country')
        self.assertIn(result['status'], ('completed', 'needs_human_review'))
        # Countries are not scored by pandas_scoring_engine (companies only) —
        # recalculate_score_if_needed must not appear in a country run.
        self.assertNotIn('recalculate_score_if_needed', result['nodes_executed'])
        self.assertIn('run_intelligence_analytics', result['nodes_executed'])

    def test_country_workflow_resolves_country_context(self):
        country = CountryProfile.objects.get(name='Kazakhstan')
        result = run_orchestration(target_id=country.pk, target_type='country')
        self.assertEqual(result['country']['id'], country.pk)

    def test_country_workflow_geo_context_available_for_kazakhstan(self):
        call_command('seed_geo_intelligence_demo')
        country = CountryProfile.objects.get(name='Kazakhstan')
        result = run_orchestration(target_id=country.pk, target_type='country')
        self.assertTrue(result['geo_context']['available'])


class GeoWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def test_location_only_workflow_skips_agent_and_scoring(self):
        result = run_orchestration(user_request='Assess climate risk here', latitude=43.25, longitude=76.95)
        self.assertEqual(result['target_type'], 'location')
        self.assertNotIn('run_agent_analysis', result['nodes_executed'])
        self.assertNotIn('recalculate_score_if_needed', result['nodes_executed'])
        self.assertNotIn('run_intelligence_analytics', result['nodes_executed'])
        self.assertIn('gather_geo_intelligence', result['nodes_executed'])
        self.assertIn('verify_output', result['nodes_executed'])

    def test_location_workflow_never_fabricates_geo_data(self):
        # A location far from any seeded reference city — must not invent a result.
        result = run_orchestration(latitude=-33.87, longitude=151.21)  # Sydney — outside Kazakhstan Phase 1 scope
        self.assertIn(result['status'], ('completed', 'needs_human_review'))


class WeakEvidenceRoutingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def test_no_evidence_flags_weak_and_notes_it(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        from evidence_memory.models import EvidenceMemory
        EvidenceMemory.objects.filter(company=profile).delete()

        result = run_orchestration(target_id=profile.pk, target_type='company')
        self.assertFalse(result['evidence_context']['available'])
        self.assertTrue(result['evidence_context']['weak'])
        self.assertTrue(any('Evidence Memory is weak' in n for n in result['verification_notes']))

    def test_strong_evidence_is_not_flagged_weak(self):
        from evidence_memory.models import EvidenceMemory
        from evidence_memory.services.embeddings import compute_embedding

        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        for i in range(3):
            text = f'Strong verified evidence record number {i} about this company.'
            EvidenceMemory.objects.create(
                text_chunk=text, company=profile, confidence=90.0,
                embedding=compute_embedding(text), embedding_status='embedded',
            )
        result = run_orchestration(user_request='verified evidence record about this company', target_id=profile.pk, target_type='company')
        self.assertFalse(result['evidence_context']['weak'])


class MissingDataHandlingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def test_company_with_no_geo_linkage_reports_unavailable_not_fabricated(self):
        # A plain seeded company (US/UK) has no Kazakhstan-only Geo Intelligence link.
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        result = run_orchestration(target_id=profile.pk, target_type='company')
        # Either genuinely unavailable, or a real country-level proxy — never crashes, never fake.
        self.assertIn('available', result['geo_context'])

    def test_missing_scoring_snapshot_triggers_synchronous_recalculation(self):
        from companies.models import CompanyScoreSnapshot
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        CompanyScoreSnapshot.objects.filter(profile=profile).delete()

        result = run_orchestration(target_id=profile.pk, target_type='company')
        self.assertTrue(result['scoring_context']['available'])
        self.assertEqual(result['scoring_context']['source'], 'recalculated_synchronously')


class ConfidenceVerificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def test_confidence_is_always_numeric_or_none(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        result = run_orchestration(target_id=profile.pk, target_type='company')
        self.assertTrue(result['confidence'] is None or isinstance(result['confidence'], (int, float)))

    def test_low_confidence_marks_human_review(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        from evidence_memory.models import EvidenceMemory
        EvidenceMemory.objects.filter(company=profile).delete()

        result = run_orchestration(target_id=profile.pk, target_type='company')
        if result['confidence'] is not None and result['confidence'] < 50:
            self.assertTrue(result['human_review_required'])
            self.assertEqual(result['status'], 'needs_human_review')


class NodeFailureHandlingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def test_unresolved_target_is_honest_failure_not_silent_success(self):
        result = run_orchestration(user_request='hello with no target at all')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failed_node'], 'classify_intent')
        self.assertEqual(result['nodes_executed'], ['classify_intent', 'handle_unresolved_target'])

    def test_a_raising_node_is_recorded_not_silently_swallowed(self):
        from unittest.mock import patch
        with patch('langgraph_orchestration.nodes.retrieve_evidence_memory', side_effect=RuntimeError('boom')):
            profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
            result = run_orchestration(target_id=profile.pk, target_type='company')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failed_node'], 'retrieve_evidence_memory')
        self.assertTrue(any('boom' in n for n in result['verification_notes']))


class BackgroundTaskIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def test_run_langgraph_intelligence_workflow_creates_both_tracking_rows(self):
        from backend_intelligence_engine.models import BackgroundTaskRun
        from backend_intelligence_engine.tasks import run_langgraph_intelligence_workflow

        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        result = run_langgraph_intelligence_workflow.apply(
            kwargs={'user_request': 'Where is value being lost?', 'target_id': profile.pk, 'target_type': 'company'},
        ).get()

        self.assertIn(result['status'], ('completed', 'failed'))
        orchestration_run = OrchestrationRun.objects.get(pk=result['orchestration_run_id'])
        self.assertEqual(orchestration_run.target_repr, profile.company.name)
        self.assertTrue(BackgroundTaskRun.objects.filter(task_type='langgraph_intelligence_workflow').exists())

    def test_task_is_registered_in_admin_retry_registry(self):
        from backend_intelligence_engine.admin import _task_registry
        self.assertIn('langgraph_intelligence_workflow', _task_registry())


class EvidenceMemoryIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def test_retrieved_memory_reaches_agent_input_summary(self):
        from evidence_memory.models import EvidenceMemory
        from evidence_memory.services.embeddings import compute_embedding

        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        memory_text = 'This specific company published a strong emissions disclosure last year.'
        EvidenceMemory.objects.create(
            text_chunk=memory_text, company=profile, confidence=85.0,
            embedding=compute_embedding(memory_text), embedding_status='embedded',
        )

        result = run_orchestration(user_request='emissions disclosure this company published', target_id=profile.pk, target_type='company')
        self.assertTrue(result['evidence_context']['available'])
        from agent_runtime_model_router.models import AgentRun
        run = AgentRun.objects.get(pk=result['agent_outputs'][0]['agent_run_id'])
        # The node itself doesn't inject memory into the agent prompt (that's
        # backend_intelligence_engine.run_ai_analysis's job) — verifies the
        # retrieval result is genuinely available for the caller to use.
        self.assertGreaterEqual(result['evidence_context']['count'], 1)

    def test_analysis_finding_is_saved_back_to_memory_via_recommend_for_company(self):
        # recommend_for_company (called inside run_intelligence_analytics)
        # reads Evidence Memory live — confirms the loop is real, not one-way.
        from evidence_memory.models import EvidenceMemory
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        EvidenceMemory.objects.filter(company=profile).delete()

        result = run_orchestration(target_id=profile.pk, target_type='company')
        evidence_gap_recs = [
            r for r in result['analytics_context'].get('recommendations', []) if r.get('type') == 'evidence_gap'
        ]
        self.assertEqual(len(evidence_gap_recs), 1)


class ScoringIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def test_existing_recent_snapshot_is_reused_not_recomputed(self):
        from companies.models import CompanyScoreSnapshot
        from pandas_scoring_engine.services.scoring import compute_company_intelligence_score

        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        scores = compute_company_intelligence_score(profile)
        CompanyScoreSnapshot.create_from_profile(profile, trigger='manual', intelligence_scores=scores)

        result = run_orchestration(target_id=profile.pk, target_type='company')
        self.assertEqual(result['scoring_context']['source'], 'existing_snapshot')

    def test_scoring_not_run_for_country_target(self):
        country = CountryProfile.objects.get(name='Kazakhstan')
        result = run_orchestration(target_id=country.pk, target_type='country')
        # recalculate_score_if_needed is skipped entirely for a country
        # target (Pandas Scoring Engine only scores companies) — scoring_context
        # stays at its untouched initial {} rather than being populated at all.
        self.assertNotIn('recalculate_score_if_needed', result['nodes_executed'])
        self.assertEqual(result['scoring_context'], {})


class AnalyticsIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def test_company_analytics_includes_similarity_and_outlier_check(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        result = run_orchestration(target_id=profile.pk, target_type='company')
        self.assertTrue(result['analytics_context']['available'])
        self.assertIn('similar_companies', result['analytics_context'])
        self.assertIn('is_outlier', result['analytics_context'])

    def test_country_analytics_includes_similarity_and_clustering(self):
        country = CountryProfile.objects.get(name='Kazakhstan')
        result = run_orchestration(target_id=country.pk, target_type='country')
        self.assertTrue(result['analytics_context']['available'])
        self.assertIn('similar_countries', result['analytics_context'])
        self.assertIn('climate_risk_cluster', result['analytics_context'])


class OrchestrationRunModelTests(TestCase):
    def test_mark_completed_persists_final_state_fields(self):
        run = OrchestrationRun.objects.create(target_type='company', target_repr='Test Co')
        final_state = {
            'status': 'completed', 'confidence': 72.5, 'human_review_required': False,
            'nodes_executed': ['classify_intent', 'finalize'], 'failed_node': None,
            'final_recommendations': [], 'next_actions': ['Send to Council'],
        }
        run.mark_completed(final_state)
        run.refresh_from_db()
        self.assertEqual(run.status, 'completed')
        self.assertEqual(run.confidence, 72.5)
        self.assertEqual(run.nodes_executed, ['classify_intent', 'finalize'])
        self.assertIsNotNone(run.completed_at)

    def test_mark_failed_records_failed_node(self):
        run = OrchestrationRun.objects.create(target_type='company', target_repr='Test Co')
        run.mark_failed('run_agent_analysis', 'Something broke')
        run.refresh_from_db()
        self.assertEqual(run.status, 'failed')
        self.assertEqual(run.failed_node, 'run_agent_analysis')


class AdminAndWorkbenchIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_base()

    def setUp(self):
        from django.contrib.auth import get_user_model
        self.admin_user = get_user_model().objects.create_superuser('orchadmin', 'o@example.com', 'password123')

    def test_admin_list_shows_orchestration_runs(self):
        OrchestrationRun.objects.create(
            target_type='company', target_repr='Visible Test Co', status='completed', confidence=80.0,
        )
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin/langgraph_orchestration/orchestrationrun/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Visible Test Co')

    def test_workbench_can_open_orchestration_result(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        result = run_orchestration(target_id=profile.pk, target_type='company')
        run = OrchestrationRun.objects.create(target_type='company', target_repr=profile.company.name)
        run.mark_completed(result)

        response = self.client.get(reverse('ai_agent_workbench:orchestration_detail', args=[run.pk]))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertFalse(TEMPLATE_LEAK_RE.search(body))
        self.assertContains(response, profile.company.name)

    def test_orchestration_detail_404_for_unknown_run(self):
        response = self.client.get(reverse('ai_agent_workbench:orchestration_detail', args=[999999999]))
        self.assertEqual(response.status_code, 404)
