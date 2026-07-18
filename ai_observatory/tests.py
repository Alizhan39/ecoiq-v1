"""
ai_observatory/tests.py — feat/ai-observatory. Every test asserts recorded
or computed values against real fixtures; no test fabricates telemetry the
recorder wouldn't produce.
"""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from gold_intelligence.models import GoldProject

from ai_observatory.models import AnalysisSession, ModelInvocation, PipelineStageExecution
from ai_observatory.services import comparison, metrics, proxies, recorder

User = get_user_model()


class RecorderTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('obs_staff', 'obs_staff@ecoiq.uk', 'password123', is_staff=True)
        self.project = GoldProject.objects.create(name='Obs Project', slug='obs-project', commodity='other')

    def test_session_records_real_timing_and_user(self):
        session = recorder.start_session(self.project, 'project_analysis', user=self.staff)
        with recorder.record_stage(session, 'mizan_analysis', 'Mizan') as stage:
            stage['items_processed'] = 3
        recorder.finish_session(session, evidence_retrieved=2, evidence_reused=1, warnings=['gap one'])

        session.refresh_from_db()
        self.assertEqual(session.status, 'completed')
        self.assertEqual(session.user, self.staff)
        self.assertIsNotNone(session.finished_at)
        self.assertIsNotNone(session.duration_ms)
        self.assertEqual(session.evidence_retrieved_count, 2)
        self.assertEqual(session.evidence_reused_count, 1)
        self.assertEqual(session.warnings, ['gap one'])
        stage_row = session.stages.get()
        self.assertEqual(stage_row.stage_key, 'mizan_analysis')
        self.assertEqual(stage_row.items_processed, 3)
        self.assertTrue(stage_row.success)
        self.assertIsNotNone(stage_row.duration_ms)

    def test_failed_stage_recorded_and_exception_propagates(self):
        session = recorder.start_session(self.project, 'project_analysis')
        with self.assertRaises(ValueError):
            with recorder.record_stage(session, 'boom', 'Boom stage'):
                raise ValueError('real failure')
        stage = session.stages.get()
        self.assertFalse(stage.success)

    def test_recorder_failure_never_breaks_product_flow(self):
        # A None session (start failed / telemetry off) is a supported input
        # everywhere — the wrapped work still runs and nothing raises.
        with recorder.record_stage(None, 'x', 'X') as stage:
            stage['items_processed'] = 1
        self.assertIsNone(recorder.finish_session(None))
        self.assertEqual(PipelineStageExecution.objects.count(), 0)

    def test_model_invocation_never_invents_tokens(self):
        session = recorder.start_session(self.project, 'other')
        inv = recorder.record_model_invocation(session, provider='anthropic', model_name='claude-sonnet-5')
        self.assertIsNone(inv.input_tokens)
        self.assertIsNone(inv.output_tokens)
        self.assertIsNone(inv.cached_tokens)
        self.assertIsNone(inv.streaming)

    def test_multiple_sessions_for_one_project(self):
        for kind in ('project_analysis', 'better_way_comparison', 'capital_decision'):
            recorder.finish_session(recorder.start_session(self.project, kind))
        self.assertEqual(AnalysisSession.objects.filter(project=self.project).count(), 3)

    def test_mark_human_review_completed_targets_only_linked_sessions(self):
        linked = recorder.start_session(self.project, 'capital_decision')
        with recorder.record_stage(linked, 'capital_decision_preparation', 'Prep') as stage:
            stage['metadata'] = {'decision_id': 42}
        recorder.finish_session(linked)
        unlinked = recorder.start_session(self.project, 'capital_decision')
        recorder.finish_session(unlinked)

        recorder.mark_human_review_completed(self.project, 42)
        linked.refresh_from_db(); unlinked.refresh_from_db()
        self.assertTrue(linked.human_review_completed)
        self.assertFalse(unlinked.human_review_completed)


class ProxyAndComparisonTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='Proxy Project', slug='proxy-project', commodity='other')
        self.session = recorder.start_session(self.project, 'project_analysis')
        with recorder.record_stage(self.session, 'a', 'A'):
            pass
        with recorder.record_stage(self.session, 'b', 'B', category='retrieval'):
            pass
        with recorder.record_stage(self.session, 'c', 'C', category='governance'):
            pass
        recorder.finish_session(self.session)

    def test_workload_counts_are_real(self):
        counts = proxies.workload_counts([self.session])
        self.assertEqual(counts['deterministic_stage'], 1)
        self.assertEqual(counts['retrieval_stage'], 1)
        self.assertEqual(counts['governance_stage'], 1)
        self.assertEqual(counts['llm_call_fresh'], 0)
        self.assertEqual(counts['llm_reported_tokens'], 0)

    def test_indices_use_documented_default_weights(self):
        indices = proxies.proxy_indices([self.session])
        # 1 deterministic ×1.0 + 1 retrieval ×2.0 + 1 governance ×1.0 = 4.0
        self.assertEqual(indices['relative_compute_index'], 4.0)
        self.assertEqual(indices['relative_carbon_proxy'], indices['relative_compute_index'])

    @override_settings(AI_OBSERVATORY_PROXY_WEIGHTS={'retrieval_stage': 10.0})
    def test_weights_are_configurable(self):
        indices = proxies.proxy_indices([self.session])
        self.assertEqual(indices['relative_compute_index'], 12.0)

    def test_cached_vs_fresh_call_classification(self):
        recorder.record_model_invocation(self.session, provider='anthropic', model_name='m', input_tokens=1000, output_tokens=100, cached_tokens=800)
        recorder.record_model_invocation(self.session, provider='anthropic', model_name='m', input_tokens=1000, output_tokens=100, cached_tokens=0)
        counts = proxies.workload_counts([self.session])
        self.assertEqual(counts['llm_call_cached'], 1)
        self.assertEqual(counts['llm_call_fresh'], 1)

    def test_missing_provider_values_counted_as_unreported(self):
        recorder.record_model_invocation(self.session, provider='anthropic', model_name='m')
        counts = proxies.workload_counts([self.session])
        self.assertEqual(counts['llm_unreported_calls'], 1)
        self.assertEqual(counts['llm_reported_tokens'], 0)

    def test_comparison_labels_generic_side_estimated(self):
        result = comparison.compare(self.project, [self.session])
        self.assertFalse(result['ecoiq']['estimated'])
        self.assertTrue(result['generic']['estimated'])
        # 3 stages × 1 generation each, no real LLM calls.
        self.assertEqual(result['generic']['model_calls'], 3)
        self.assertEqual(result['ecoiq']['model_calls'], 0)
        self.assertEqual(result['generic']['deterministic_steps'], 0)
        self.assertGreater(result['generic']['compute_index'], result['ecoiq']['compute_index'])

    @override_settings(AI_OBSERVATORY_BASELINE_ASSUMPTIONS={'generations_per_stage': 2})
    def test_baseline_assumptions_configurable(self):
        result = comparison.compare(self.project, [self.session])
        self.assertEqual(result['generic']['model_calls'], 6)
        self.assertEqual(result['assumptions']['generations_per_stage'], 2)

    def test_deterministic_step_ratio(self):
        self.assertEqual(self.session.deterministic_step_ratio, 1.0)
        recorder.record_model_invocation(self.session, provider='anthropic', model_name='m')
        self.assertEqual(self.session.deterministic_step_ratio, 0.75)


class QualityMetricsTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='Metrics Project', slug='metrics-project', commodity='other')

    def test_metrics_return_not_measured_when_no_data(self):
        result = metrics.quality_metrics(self.project)
        self.assertIsNone(result['evidence_traceability']['value'])
        self.assertEqual(result['evidence_traceability']['display'], 'Not measured yet')
        self.assertIsNone(result['deterministic_step_ratio']['value'])
        self.assertEqual(result['blocked_unsafe_outputs']['value'], 0)

    def test_every_metric_has_full_documentation(self):
        for definition in metrics.METRIC_DEFINITIONS:
            for key in ('measures', 'calculation', 'assumptions', 'not_claimed'):
                self.assertTrue(definition[key], f'{definition["key"]} missing {key}')

    def test_human_oversight_and_blocked_counts(self):
        s1 = recorder.start_session(self.project, 'better_way_comparison')
        recorder.finish_session(s1, blocked_recommendations=2)
        result = metrics.quality_metrics(self.project)
        self.assertEqual(result['blocked_unsafe_outputs']['value'], 2)
        self.assertEqual(result['human_oversight']['value'], 1.0)


class ObservatoryViewTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')
        self.staff = User.objects.create_user('obs_view_staff', 'ovs@ecoiq.uk', 'password123', is_staff=True)
        self.normal = User.objects.create_user('obs_view_normal', 'ovn@example.com', 'password123', is_staff=False)
        self.project = GoldProject.objects.create(name='Obs View Project', slug='obs-view-project', commodity='other')
        self.other_project = GoldProject.objects.create(name='Obs Other Project', slug='obs-other-project', commodity='other')
        self.session = recorder.start_session(self.project, 'project_analysis', user=self.staff)
        with recorder.record_stage(self.session, 'mizan_analysis', 'Mizan Project Analysis'):
            pass
        recorder.finish_session(self.session, warnings=['a real gap'])

    def _url(self, project=None):
        return reverse('ai_observatory:observatory', args=[(project or self.project).slug])

    def test_anonymous_denied(self):
        r = self.client.get(self._url())
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])

    def test_non_staff_denied(self):
        self.client.force_login(self.normal)
        r = self.client.get(self._url())
        self.assertEqual(r.status_code, 302)

    def test_staff_sees_dashboard_with_real_session(self):
        self.client.force_login(self.staff)
        r = self.client.get(self._url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Mizan Project Analysis')
        self.assertContains(r, 'a real gap')
        self.assertContains(r, 'Relative Compute Index')
        self.assertContains(r, 'Comparative indicators only')

    def test_zero_model_calls_shown_as_real_value(self):
        self.client.force_login(self.staff)
        r = self.client.get(self._url())
        self.assertContains(r, 'Zero model calls')

    def test_cross_project_session_404s(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse('ai_observatory:session_detail', args=[self.other_project.slug, self.session.pk]))
        self.assertEqual(r.status_code, 404)

    def test_other_project_dashboard_never_shows_this_projects_sessions(self):
        self.client.force_login(self.staff)
        r = self.client.get(self._url(project=self.other_project))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, f'#{self.session.pk} —')
        self.assertContains(r, 'No telemetry has been recorded for this project yet')

    def test_invalid_project_slug_404s(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse('ai_observatory:observatory', args=['no-such-project']))
        self.assertEqual(r.status_code, 404)

    def test_invalid_session_id_404s(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse('ai_observatory:session_detail', args=[self.project.slug, 999999]))
        self.assertEqual(r.status_code, 404)

    def test_methodology_page_documents_everything(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse('ai_observatory:methodology', args=[self.project.slug]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'What it does NOT claim')
        self.assertContains(r, 'llm_call_fresh')
        self.assertContains(r, 'generations_per_stage')
        self.assertContains(r, 'No electricity, energy or carbon measurement')

    def test_session_detail_shows_selected_session(self):
        second = recorder.start_session(self.project, 'better_way_comparison', user=self.staff)
        recorder.finish_session(second)
        self.client.force_login(self.staff)
        r = self.client.get(reverse('ai_observatory:session_detail', args=[self.project.slug, self.session.pk]))
        self.assertContains(r, 'Project Analysis (Mizan + Resource Purpose + Retrieval)')


class PipelineInstrumentationTests(TestCase):
    """The instrumented capital_guardian flows record real sessions."""

    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')
        self.staff = User.objects.create_user('obs_pipe_staff', 'ops@ecoiq.uk', 'password123', is_staff=True)
        self.client.force_login(self.staff)
        self.project = GoldProject.objects.create(
            name='Obs Pipeline Project', slug='obs-pipeline-project', commodity='other',
        )

    def test_run_project_analysis_records_session(self):
        r = self.client.post(reverse('capital_guardian:run_project_analysis', args=[self.project.slug]))
        self.assertEqual(r.status_code, 200)
        session = AnalysisSession.objects.get(project=self.project, kind='project_analysis')
        self.assertEqual(session.status, 'completed')
        self.assertEqual(session.user, self.staff)
        keys = set(session.stages.values_list('stage_key', flat=True))
        self.assertIn('mizan_analysis', keys)
        self.assertIn('resource_purpose_review', keys)
        self.assertIn('evidence_memory_retrieval', keys)
        self.assertEqual(session.model_invocations.count(), 0)
        self.assertEqual(session.final_recommendation_status, 'human_review_required')

    def test_better_way_records_blocked_recommendations(self):
        from waste_to_value_capital_allocation_engine.models import InterventionOption, OperationalLoss
        loss = OperationalLoss.objects.create(
            project=self.project.name, title='Obs loss', loss_type='heat_loss', financial_loss_amount=10000,
        )
        InterventionOption.objects.create(
            operational_loss=loss, title='Eligible insulation', intervention_type='prevention',
            capex_estimate=2000, estimated_annual_savings=1500, estimated_loss_avoided=3000,
        )
        InterventionOption.objects.create(
            operational_loss=loss, title='Sell coal ash as fertiliser', intervention_type='resale',
        )
        r = self.client.post(reverse('capital_guardian:run_better_way_comparison', args=[self.project.slug, loss.pk]))
        self.assertEqual(r.status_code, 200)
        session = AnalysisSession.objects.get(project=self.project, kind='better_way_comparison')
        self.assertEqual(session.blocked_recommendation_count, 1)
        self.assertTrue(session.stages.filter(stage_key='safety_gate', category='governance').exists())

    def test_two_analyses_create_two_sessions(self):
        self.client.post(reverse('capital_guardian:run_project_analysis', args=[self.project.slug]))
        self.client.post(reverse('capital_guardian:run_project_analysis', args=[self.project.slug]))
        self.assertEqual(AnalysisSession.objects.filter(project=self.project, kind='project_analysis').count(), 2)


class CommandCentreTelemetryStageTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')
        self.staff = User.objects.create_user('obs_cc_staff', 'occ@ecoiq.uk', 'password123', is_staff=True)
        self.project = GoldProject.objects.create(name='Obs CC Project', slug='obs-cc-project', commodity='other')

    def _stage(self):
        from capital_guardian.services.command_centre import build_command_centre_context
        ctx = build_command_centre_context(GoldProject.objects.get(pk=self.project.pk), user=self.staff)
        return next(s for s in ctx['stages'] if s.key == 'telemetry')

    def test_no_sessions_is_not_started_with_observatory_link(self):
        stage = self._stage()
        self.assertEqual(stage.status, 'NOT_STARTED')
        self.assertTrue(stage.is_available)
        self.assertEqual(stage.action_label, 'Open Observatory')
        self.assertIn('/ai-observatory/', stage.action_url)

    def test_recorded_session_summarised(self):
        session = recorder.start_session(self.project, 'project_analysis', user=self.staff)
        recorder.finish_session(session, warnings=['w1'])
        stage = self._stage()
        self.assertEqual(stage.status, 'ACTIVE_MONITORING')
        self.assertIn('1 session(s) recorded', stage.summary)
        self.assertIn('warning', stage.blocked_reason)

    def test_command_centre_page_shows_latest_session_and_link(self):
        session = recorder.start_session(self.project, 'project_analysis', user=self.staff)
        recorder.finish_session(session)
        self.client.force_login(self.staff)
        r = self.client.get(reverse('capital_guardian:project_command_centre', args=[self.project.slug]))
        self.assertContains(r, 'Open Observatory')
        self.assertContains(r, f'#{session.pk} —')
        self.assertNotContains(r, 'Not available in this release. Token/latency')

    def test_command_centre_never_shows_other_projects_session(self):
        other = GoldProject.objects.create(name='Obs CC Other', slug='obs-cc-other', commodity='other')
        session = recorder.start_session(other, 'project_analysis', user=self.staff)
        recorder.finish_session(session)
        stage = self._stage()
        self.assertEqual(stage.status, 'NOT_STARTED')
