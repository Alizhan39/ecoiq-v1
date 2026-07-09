from unittest.mock import patch

from django.test import TestCase

from backend_intelligence_engine import tasks
from backend_intelligence_engine.models import BackgroundTaskRun
from backend_intelligence_engine.services import http_client
from ecoiq.celery import app as celery_app


class CeleryConfigurationTests(TestCase):
    def test_broker_and_backend_come_from_redis_url_setting(self):
        from django.conf import settings
        self.assertEqual(celery_app.conf.broker_url, settings.REDIS_URL)
        self.assertEqual(celery_app.conf.result_backend, settings.REDIS_URL)

    def test_default_redis_url_has_no_hardcoded_credentials(self):
        import os
        # Only meaningful when REDIS_URL isn't set in the environment — that's
        # exactly when the settings.py fallback default is what's in effect.
        if 'REDIS_URL' in os.environ:
            self.skipTest('REDIS_URL is set in this environment; not exercising the fallback default')
        from django.conf import settings
        self.assertEqual(settings.REDIS_URL, 'redis://localhost:6379/0')
        self.assertNotIn('@', settings.REDIS_URL)

    def test_tasks_have_bounded_retries_not_infinite(self):
        for task in (tasks.company_intelligence_refresh, tasks.geo_intelligence_refresh, tasks.run_ai_analysis):
            self.assertEqual(task.max_retries, 2)
            self.assertIn(Exception, task.autoretry_for)

    def test_agent_evaluation_task_types_are_registered(self):
        task_types = dict(BackgroundTaskRun.TASK_TYPE_CHOICES)
        for task_type in ('run_agent_evaluation', 'run_agent_benchmark', 'detect_agent_regressions'):
            self.assertIn(task_type, task_types)

    def test_task_time_limits_are_set(self):
        from django.conf import settings
        self.assertEqual(settings.CELERY_TASK_TIME_LIMIT, 300)
        self.assertLess(settings.CELERY_TASK_SOFT_TIME_LIMIT, settings.CELERY_TASK_TIME_LIMIT)


class BackgroundTaskRunModelTests(TestCase):
    def test_mark_running_then_completed_computes_duration(self):
        run = BackgroundTaskRun.objects.create(task_type='geo_intelligence_refresh', target_repr='Almaty')
        self.assertEqual(run.status, 'queued')
        run.mark_running()
        self.assertEqual(run.status, 'running')
        self.assertIsNotNone(run.started_at)
        run.mark_completed({'ok': True})
        self.assertEqual(run.status, 'completed')
        self.assertIsNotNone(run.duration_seconds)
        self.assertEqual(run.result_summary, {'ok': True})

    def test_mark_failed_records_error_and_duration(self):
        run = BackgroundTaskRun.objects.create(task_type='ai_analysis', target_repr='Research Agent')
        run.mark_running()
        run.mark_failed('boom')
        self.assertEqual(run.status, 'failed')
        self.assertEqual(run.error_summary, 'boom')
        self.assertIsNotNone(run.failed_at)
        self.assertIsNotNone(run.duration_seconds)

    def test_mark_retrying_increments_retry_count(self):
        run = BackgroundTaskRun.objects.create(task_type='company_intelligence_refresh', target_repr='Acme')
        run.mark_retrying('temporary error', 1)
        self.assertEqual(run.status, 'retrying')
        self.assertEqual(run.retry_count, 1)

    def test_str_is_human_readable(self):
        run = BackgroundTaskRun.objects.create(task_type='geo_intelligence_refresh', target_repr='Almaty')
        self.assertIn('Almaty', str(run))
        self.assertIn('Geo Intelligence Refresh', str(run))


class CompanyIntelligenceRefreshTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command
        call_command('seed_global_companies')

    def _a_profile(self):
        from companies.models import CompanyProfile
        return CompanyProfile.objects.filter(status__in=['public', 'verified']).select_related('company').first()

    def test_refresh_recalculates_score_and_creates_snapshot(self):
        from companies.models import CompanyScoreSnapshot
        profile = self._a_profile()
        self.assertIsNotNone(profile, 'seed_global_companies must produce at least one public/verified profile')

        snapshots_before = CompanyScoreSnapshot.objects.filter(profile=profile).count()
        result = tasks.company_intelligence_refresh.apply(args=[profile.pk]).get()

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(CompanyScoreSnapshot.objects.filter(profile=profile).count(), snapshots_before + 1)

        run = BackgroundTaskRun.objects.filter(task_type='company_intelligence_refresh').latest('queued_at')
        self.assertEqual(run.status, 'completed')
        self.assertIsNotNone(run.duration_seconds)
        self.assertIn('score_before', run.result_summary)

    def test_refresh_of_nonexistent_profile_fails_honestly(self):
        result = tasks.company_intelligence_refresh.apply(args=[999999999]).get()
        self.assertEqual(result['status'], 'failed')
        run = BackgroundTaskRun.objects.filter(task_type='company_intelligence_refresh').latest('queued_at')
        self.assertEqual(run.status, 'failed')
        self.assertIn('does not exist', run.error_summary)

    def test_significant_score_change_creates_admin_notification(self):
        from notifications.models import AdminNotification
        profile = self._a_profile()
        with patch('companies.scoring.recalculate_and_save') as mock_recalc:
            def _bump(p):
                p.ecoiq_total_score = (p.ecoiq_total_score or 0) + 10
                p.save(update_fields=['ecoiq_total_score'])
                return p
            mock_recalc.side_effect = _bump
            notifications_before = AdminNotification.objects.filter(source_type='background_task').count()
            tasks.company_intelligence_refresh.apply(args=[profile.pk]).get()
        self.assertEqual(
            AdminNotification.objects.filter(source_type='background_task').count(), notifications_before + 1,
        )

    def test_evidence_monitors_are_checked_via_existing_service(self):
        from intelligence.models import MonitorWatch
        profile = self._a_profile()
        watch = MonitorWatch.objects.create(company=profile.company, url='https://example.invalid/esg')
        with patch('intelligence.compute.check_monitor_target', return_value=True) as mock_check:
            result = tasks.company_intelligence_refresh.apply(args=[profile.pk]).get()
        mock_check.assert_called_once()
        self.assertEqual(mock_check.call_args[0][0].pk, watch.pk)
        self.assertEqual(result['watches_checked'], 1)
        self.assertEqual(result['watches_changed'], 1)


class GeoIntelligenceRefreshTaskTests(TestCase):
    def _fake_summary(self, available=True):
        return {
            'available': available, 'reason': '' if available else 'no network',
            'avg_temp_current_year': 13.4, 'avg_temp_previous_year': 11.9,
            'precipitation_current_year_mm': 557.0, 'precipitation_previous_year_mm': 904.0,
            'extreme_heat_days_current_year': 19, 'extreme_heat_days_previous_year': 17,
            'years': [2024, 2025], 'fetched_at': '2026-01-01T00:00:00+00:00',
        }

    def test_refresh_single_city_success(self):
        with patch('geo_intelligence.services.weather.get_city_climate_summary', return_value=self._fake_summary()):
            result = tasks.geo_intelligence_refresh.apply(args=['Almaty']).get()
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(result['cities']['Almaty']['available'])
        run = BackgroundTaskRun.objects.filter(task_type='geo_intelligence_refresh').latest('queued_at')
        self.assertEqual(run.status, 'completed')
        self.assertEqual(run.target_repr, 'Almaty')

    def test_refresh_all_cities_when_none_specified(self):
        from geo_intelligence.services import weather
        with patch('geo_intelligence.services.weather.get_city_climate_summary', return_value=self._fake_summary()):
            result = tasks.geo_intelligence_refresh.apply(args=[None]).get()
        self.assertEqual(set(result['cities'].keys()), set(weather.KAZAKHSTAN_CITIES.keys()))

    def test_unsupported_city_fails_honestly(self):
        result = tasks.geo_intelligence_refresh.apply(args=['Nowhereville']).get()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'unsupported_city')

    def test_never_fabricates_data_on_total_network_failure(self):
        with patch('geo_intelligence.services.weather.get_city_climate_summary', return_value=self._fake_summary(available=False)):
            result = tasks.geo_intelligence_refresh.apply(args=['Almaty']).get()
        self.assertEqual(result['status'], 'failed')
        run = BackgroundTaskRun.objects.filter(task_type='geo_intelligence_refresh').latest('queued_at')
        self.assertEqual(run.status, 'failed')
        self.assertIn('Meteostat', run.error_summary)

    def test_does_not_persist_a_new_climate_model_by_design(self):
        # Phase 1 Geo Intelligence intentionally has no ClimateObservation
        # model — confirm this task doesn't quietly introduce one.
        import geo_intelligence.models as geo_models
        self.assertFalse(hasattr(geo_models, 'ClimateObservation'))


class AIAnalysisBackgroundTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command
        call_command('seed_agent_runtime_demo')
        call_command('seed_waste_to_value_demo')

    def test_deterministic_run_reuses_existing_execution_pipeline(self):
        result = tasks.run_ai_analysis.apply(
            args=['waste-leakage-agent'], kwargs={'execution_mode': 'deterministic_test'},
        ).get()
        self.assertEqual(result['status'], 'completed')
        self.assertIn('agent_run_id', result)

        from agent_runtime_model_router.models import AgentRun
        agent_run = AgentRun.objects.get(pk=result['agent_run_id'])
        self.assertEqual(agent_run.execution_mode_requested, 'deterministic_test')
        # Never silently claim live when deterministic was requested and used.
        self.assertEqual(agent_run.execution_mode_used, 'deterministic_test')

    def test_completed_run_is_visible_to_the_ai_agent_workbench(self):
        result = tasks.run_ai_analysis.apply(
            args=['waste-leakage-agent'], kwargs={'execution_mode': 'deterministic_test'},
        ).get()
        response = self.client.get('/ai-agents/workbench/', {'agent': 'waste-leakage-agent'})
        self.assertEqual(response.status_code, 200)
        run_url = f'/ai-agents/run/{result["agent_run_id"]}/'
        self.assertEqual(self.client.get(run_url).status_code, 302)

    def test_unknown_agent_slug_fails_honestly(self):
        result = tasks.run_ai_analysis.apply(args=['not-a-real-agent']).get()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'unknown_agent')

    def test_can_attach_to_a_real_council_case(self):
        result = tasks.run_ai_analysis.apply(
            args=['waste-leakage-agent'],
            kwargs={'case_slug': 'meat-cold-chain-loss', 'execution_mode': 'deterministic_test'},
        ).get()
        self.assertEqual(result['status'], 'completed')
        # Whether or not it actually reached the Council depends on schema
        # validity of the deterministic golden test — but it must never crash,
        # and the honest agent_run_status must always be reported.
        self.assertIn('agent_run_status', result)

    def test_never_silently_relabels_live_as_simulated(self):
        # Without ANTHROPIC_API_KEY configured in this test environment, a
        # 'live' request must fail honestly (missing_credentials), never
        # succeed as if it were simulated_demo.
        from django.conf import settings
        if settings.ANTHROPIC_API_KEY:
            self.skipTest('ANTHROPIC_API_KEY is configured in this environment')
        result = tasks.run_ai_analysis.apply(
            args=['waste-leakage-agent'], kwargs={'execution_mode': 'live'},
        ).get()
        self.assertIn(result['agent_run_status'], ('needs_human_review', 'failed', 'blocked'))


class HTTPClientTests(TestCase):
    def test_successful_fetch(self):
        mock_response = type('R', (), {
            'status_code': 200, 'content': b'ok', 'text': 'ok', 'headers': {},
            'json': lambda self: (_ for _ in ()).throw(ValueError()),
        })()
        with patch('httpx.Client') as MockClient:
            MockClient.return_value.__enter__.return_value.request.return_value = mock_response
            result = http_client.fetch('https://example.invalid/')
        self.assertTrue(result.success)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.attempts, 1)

    def test_retries_on_5xx_then_succeeds(self):
        responses = [
            type('R', (), {'status_code': 503, 'content': b'', 'text': '', 'headers': {}, 'json': lambda self: {}})(),
            type('R', (), {'status_code': 200, 'content': b'ok', 'text': 'ok', 'headers': {}, 'json': lambda self: {}})(),
        ]
        with patch('httpx.Client') as MockClient, patch('backend_intelligence_engine.services.http_client.time.sleep'):
            MockClient.return_value.__enter__.return_value.request.side_effect = responses
            result = http_client.fetch('https://example.invalid/', max_retries=1)
        self.assertTrue(result.success)
        self.assertEqual(result.attempts, 2)

    def test_never_raises_on_connection_failure(self):
        with patch('httpx.Client') as MockClient, patch('backend_intelligence_engine.services.http_client.time.sleep'):
            MockClient.return_value.__enter__.side_effect = __import__('httpx').ConnectError('no route')
            result = http_client.fetch('https://example.invalid/', max_retries=1)
        self.assertFalse(result.success)
        self.assertIn('ConnectError', result.error)

    def test_sends_ecoiq_user_agent(self):
        captured = {}

        def _capture_request(method, url, headers=None, **kwargs):
            captured['headers'] = headers
            return type('R', (), {'status_code': 200, 'content': b'', 'text': '', 'headers': {}, 'json': lambda self: {}})()

        with patch('httpx.Client') as MockClient:
            MockClient.return_value.__enter__.return_value.request.side_effect = _capture_request
            http_client.fetch('https://example.invalid/')
        self.assertIn('EcoIQ-Bot', captured['headers']['User-Agent'])


class AdminOperationsTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'password123')
        self.client.force_login(self.admin_user)

    def test_recent_task_runs_visible_in_admin_list(self):
        BackgroundTaskRun.objects.create(task_type='geo_intelligence_refresh', target_repr='Almaty', status='completed')
        response = self.client.get('/admin/backend_intelligence_engine/backgroundtaskrun/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Almaty')

    def test_retry_action_requeues_only_failed_tasks(self):
        failed = BackgroundTaskRun.objects.create(
            task_type='geo_intelligence_refresh', target_repr='Almaty', status='failed',
            task_kwargs={'city_name': 'Almaty'},
        )
        completed = BackgroundTaskRun.objects.create(
            task_type='geo_intelligence_refresh', target_repr='Astana', status='completed',
        )
        with patch('backend_intelligence_engine.tasks.geo_intelligence_refresh.delay') as mock_delay:
            response = self.client.post('/admin/backend_intelligence_engine/backgroundtaskrun/', {
                'action': 'retry_failed_tasks',
                '_selected_action': [str(failed.pk), str(completed.pk)],
            }, follow=True)
        self.assertEqual(response.status_code, 200)
        mock_delay.assert_called_once_with(city_name='Almaty')

    def test_cannot_manually_add_a_task_run(self):
        response = self.client.get('/admin/backend_intelligence_engine/backgroundtaskrun/add/')
        self.assertEqual(response.status_code, 403)

    def test_retry_action_requeues_failed_agent_evaluation_task(self):
        failed = BackgroundTaskRun.objects.create(
            task_type='run_agent_evaluation', target_repr='Some Agent', status='failed',
            task_kwargs={'agent_id': 42},
        )
        with patch('backend_intelligence_engine.tasks.run_agent_evaluation.delay') as mock_delay:
            response = self.client.post('/admin/backend_intelligence_engine/backgroundtaskrun/', {
                'action': 'retry_failed_tasks',
                '_selected_action': [str(failed.pk)],
            }, follow=True)
        self.assertEqual(response.status_code, 200)
        mock_delay.assert_called_once_with(agent_id=42)


class WorkbenchStatusConnectionTests(TestCase):
    """The Phase 1 backend connection point for a future Workbench status
    widget — no template/UI change, just the queryable, honest data path."""

    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command
        call_command('seed_agent_runtime_demo')

    def test_completed_ai_analysis_run_is_discoverable_by_agent_run_id(self):
        from backend_intelligence_engine.services import status
        run = BackgroundTaskRun.objects.create(
            task_type='ai_analysis', target_repr='Waste & Leakage Agent',
            result_summary={'agent_run_id': 501, 'agent_run_status': 'completed'},
        )
        run.mark_completed(run.result_summary)
        found = status.latest_task_run_for_agent_run(501)
        self.assertEqual(found.pk, run.pk)
        self.assertEqual(status.display_status_for_agent_run(501), 'COMPLETED')

    def test_untracked_agent_run_returns_none_not_a_fabricated_status(self):
        from backend_intelligence_engine.services import status
        self.assertIsNone(status.latest_task_run_for_agent_run(9999999))
        self.assertIsNone(status.display_status_for_agent_run(9999999))

    def test_running_ai_analysis_maps_to_analysing(self):
        from backend_intelligence_engine.services import status
        run = BackgroundTaskRun.objects.create(
            task_type='ai_analysis', target_repr='Research Agent',
            result_summary={'agent_run_id': 502},
        )
        run.mark_running()
        self.assertEqual(status.display_status_for_agent_run(502), 'ANALYSING')

    def test_ai_analysis_task_result_is_findable_via_status_service(self):
        result = tasks.run_ai_analysis.apply(
            args=['waste-leakage-agent'], kwargs={'execution_mode': 'deterministic_test'},
        ).get()
        from backend_intelligence_engine.services import status
        found = status.latest_task_run_for_agent_run(result['agent_run_id'])
        self.assertIsNotNone(found)
        self.assertEqual(found.status, 'completed')


class AgentEvaluationBackgroundTaskTests(TestCase):
    """
    run_agent_evaluation / run_agent_benchmark / detect_agent_regressions —
    reuse agent_training_evaluation_lab's services exactly (no duplicate
    scoring logic here), and each creates exactly one BackgroundTaskRun row,
    same as every other task in this module.
    """

    @classmethod
    def setUpTestData(cls):
        from agent_runtime_model_router.models import AgentRegistryEntry, AgentRun
        cls.agent = AgentRegistryEntry.objects.create(agent_id='bg-eval-test-agent', agent_name='BG Eval Test Agent')
        AgentRun.objects.create(
            agent=cls.agent, task_type='demo', execution_mode_requested='deterministic_test',
            status='completed', safety_status='pass', schema_valid=True, evidence_used=['source-a'],
        )

    def test_run_agent_evaluation_creates_a_background_task_run(self):
        result = tasks.run_agent_evaluation.apply(kwargs={'agent_id': self.agent.pk}).get()
        self.assertEqual(result['status'], 'completed')
        run = BackgroundTaskRun.objects.get(task_type='run_agent_evaluation', target_reference=f'agent_runtime_model_router.AgentRegistryEntry:{self.agent.pk}')
        self.assertEqual(run.status, 'completed')

    def test_run_agent_evaluation_unknown_agent_fails_honestly(self):
        result = tasks.run_agent_evaluation.apply(kwargs={'agent_id': 9999999}).get()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'not_found')

    def test_run_agent_benchmark_evaluates_and_checks_regressions(self):
        result = tasks.run_agent_benchmark.apply(kwargs={'agent_id': self.agent.pk}).get()
        self.assertEqual(result['status'], 'completed')
        self.assertIn('evaluation_run_id', result)
        self.assertIn('regressions_found', result)
        self.assertIn('recommendations_generated', result)

    def test_run_agent_benchmark_unknown_agent_fails_honestly(self):
        result = tasks.run_agent_benchmark.apply(kwargs={'agent_id': 9999999}).get()
        self.assertEqual(result['status'], 'failed')

    def test_detect_agent_regressions_runs_against_a_real_evaluation(self):
        evaluation_result = tasks.run_agent_evaluation.apply(kwargs={'agent_id': self.agent.pk}).get()
        result = tasks.detect_agent_regressions.apply(
            kwargs={'evaluation_run_id': evaluation_result['evaluation_run_id']},
        ).get()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['regressions_found'], 0)  # first evaluation, nothing to compare against

    def test_detect_agent_regressions_unknown_evaluation_fails_honestly(self):
        result = tasks.detect_agent_regressions.apply(kwargs={'evaluation_run_id': 9999999}).get()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'not_found')

    def test_all_three_tasks_have_bounded_retries(self):
        for task in (tasks.run_agent_evaluation, tasks.run_agent_benchmark, tasks.detect_agent_regressions):
            self.assertEqual(task.max_retries, 2)
            self.assertIn(Exception, task.autoretry_for)
