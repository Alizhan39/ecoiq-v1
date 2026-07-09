from django.test import TestCase
from django.utils import timezone

from agent_runtime_model_router.models import AgentRegistryEntry, AgentRun
from agent_training_evaluation_lab.models import (
    AgentEvaluationRun, AgentHumanFeedback, AgentRegression, GoldenDatasetCase, ImprovementRecommendation,
)
from agent_training_evaluation_lab.services import golden_dataset, metrics, recommendations, regression_detection
from agent_training_evaluation_lab.services.evaluation_engine import run_agent_evaluation

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class AgentTrainingEvaluationLabPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'EcoIQ Agent Training & Evaluation Lab')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'Train, test and improve EcoIQ AI agents')

    def test_page_mentions_are_all_14_agents_required(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'Are all 14 agents required?')

    def test_page_mentions_mvp_agents(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'MVP agents')

    def test_page_mentions_github_agents_vs_ecoiq_agents(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'GitHub Agents vs EcoIQ Agents')

    def test_page_mentions_golden_test_cases(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'Golden Test Cases')

    def test_page_mentions_agent_output_schemas(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'Agent Output Schemas')

    def test_page_mentions_no_harm_gate_for_agent_training(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'No Harm Gate for Agent Training')

    def test_page_mentions_open_agent_training_lab(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'Open Agent Training Lab')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        for label in (
            'Open Agent Training Lab', 'View MVP Agents', 'Create Golden Test Case',
            'Run Agent Evaluation', 'Review Failed Output', 'Open Prompt Library',
            'View Human Approval Rules', 'Train Document Reader Agent',
            'Train MRV Agent', 'Train Finance Agent',
        ):
            self.assertContains(response, label)

    def test_page_shows_all_14_agent_cards(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        for name in (
            'Research Agent', 'Document Reader Agent', 'Photo / Visual Evidence Agent',
            'Asset Passport Agent', 'Playbook Matching Agent', 'Finance Modelling Agent',
            'Supplier / Funding Match Agent', 'MRV Agent', 'Governance Agent',
            'Report Generator Agent', 'Customer Success Agent', 'Sales CRM Agent',
            'Analytics Agent', 'Amanah Autopilot Supervisor',
        ):
            self.assertContains(response, name)

    def test_page_has_no_claim_agents_are_fully_autonomous(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        content = response.content.decode()
        self.assertIn('does not claim all agents are fully autonomous production agents yet', content)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageAgentTrainingEvaluationLabTeaserTests(TestCase):
    def test_platform_page_mentions_agent_training_evaluation_lab(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Agent Training & Evaluation Lab')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class MetricsTests(TestCase):
    """Every metric is a pure function over real, already-persisted AgentRun
    fields — these tests build small, explicitly-labelled synthetic AgentRun
    rows (not real production data) to prove each formula, not to fabricate
    a real agent's performance history."""

    def setUp(self):
        self.agent = AgentRegistryEntry.objects.create(agent_id='metrics-test-agent', agent_name='Metrics Test Agent')

    def _make_run(self, **kwargs):
        defaults = {
            'agent': self.agent, 'task_type': 'demo', 'execution_mode_requested': 'deterministic_test',
            'status': 'completed',
        }
        defaults.update(kwargs)
        return AgentRun.objects.create(**defaults)

    def test_empty_queryset_is_not_yet_measured_for_every_scored_metric(self):
        runs = AgentRun.objects.none()
        for name, (fn, _weight) in metrics.SCORED_METRICS.items():
            result = fn(runs)
            self.assertIsNone(result['score'], f'{name} should be None with no runs')
            self.assertIn('NOT YET MEASURED', result['explanation'])

    def test_factual_grounding_score_is_safety_pass_rate(self):
        self._make_run(safety_status='pass')
        self._make_run(safety_status='pass')
        self._make_run(safety_status='blocking')
        result = metrics.factual_grounding_score(AgentRun.objects.filter(agent=self.agent))
        self.assertEqual(result['score'], round(100 * 2 / 3, 1))

    def test_evidence_coverage_score_counts_runs_with_evidence(self):
        self._make_run(evidence_used=['source-a'])
        self._make_run(evidence_used=[])
        result = metrics.evidence_coverage_score(AgentRun.objects.filter(agent=self.agent))
        self.assertEqual(result['score'], 50.0)

    def test_evidence_quality_score_maps_quality_labels_to_points(self):
        self._make_run(evidence_provenance=[{'quality': 'strong'}, {'quality': 'weak'}])
        result = metrics.evidence_quality_score(AgentRun.objects.filter(agent=self.agent))
        self.assertEqual(result['score'], 65.0)  # mean(100, 30)

    def test_evidence_quality_not_yet_measured_when_no_provenance_recorded(self):
        self._make_run(evidence_provenance=[])
        result = metrics.evidence_quality_score(AgentRun.objects.filter(agent=self.agent))
        self.assertIsNone(result['score'])

    def test_confidence_calibration_checks_direction_only_when_risk_signal_present(self):
        self._make_run(risk_flags=['x'], raw_confidence=90, calibrated_confidence=70)  # correctly lowered
        self._make_run(risk_flags=['x'], raw_confidence=90, calibrated_confidence=95)  # incorrectly raised
        self._make_run(risk_flags=[], missing_data=[], raw_confidence=90, calibrated_confidence=90)  # excluded: no risk signal
        result = metrics.confidence_calibration_score(AgentRun.objects.filter(agent=self.agent))
        self.assertEqual(result['sample_size'], 2)
        self.assertEqual(result['score'], 50.0)

    def test_confidence_calibration_not_yet_measured_without_any_risk_signal(self):
        self._make_run(risk_flags=[], missing_data=[], calibrated_confidence=80)
        result = metrics.confidence_calibration_score(AgentRun.objects.filter(agent=self.agent))
        self.assertIsNone(result['score'])

    def test_consistency_score_is_perfect_when_repeated_task_type_has_zero_variance(self):
        self._make_run(task_type='loss_detection', calibrated_confidence=80)
        self._make_run(task_type='loss_detection', calibrated_confidence=80)
        result = metrics.consistency_score(AgentRun.objects.filter(agent=self.agent))
        self.assertEqual(result['score'], 100.0)

    def test_completeness_score_is_schema_valid_rate_excluding_unchecked_runs(self):
        self._make_run(schema_valid=True)
        self._make_run(schema_valid=False)
        self._make_run(schema_valid=None)
        result = metrics.completeness_score(AgentRun.objects.filter(agent=self.agent))
        self.assertEqual(result['sample_size'], 2)
        self.assertEqual(result['score'], 50.0)

    def test_reasoning_trace_completeness_counts_nonempty_audit_trails(self):
        self._make_run(audit_trail=[{'ts': '2026-01-01', 'event': 'started'}])
        self._make_run(audit_trail=[])
        result = metrics.reasoning_trace_completeness_score(AgentRun.objects.filter(agent=self.agent))
        self.assertEqual(result['score'], 50.0)

    def test_reliability_score_is_100_minus_failure_rate(self):
        self._make_run(status='completed')
        self._make_run(status='failed')
        result = metrics.reliability_score(AgentRun.objects.filter(agent=self.agent))
        self.assertEqual(result['score'], 50.0)

    def test_latency_metrics_computed_from_real_start_and_completion_timestamps(self):
        now = timezone.now()
        self._make_run(started_at=now, completed_at=now + timezone.timedelta(seconds=10))
        result = metrics.latency_metrics(AgentRun.objects.filter(agent=self.agent))
        self.assertEqual(result['score'], 10.0)

    def test_compute_overall_score_renormalizes_over_available_metrics_only(self):
        metric_results = {name: metrics._none('no data') for name in metrics.SCORED_METRICS}
        metric_results['factual_grounding'] = {'score': 80.0, 'explanation': 'x', 'sample_size': 1}
        self.assertEqual(metrics.compute_overall_score(metric_results), 80.0)

    def test_compute_overall_score_is_none_when_nothing_measured(self):
        metric_results = {name: metrics._none('no data') for name in metrics.SCORED_METRICS}
        self.assertIsNone(metrics.compute_overall_score(metric_results))


class GoldenDatasetSyncTests(TestCase):
    """sync_golden_dataset() mirrors the REAL ai_agents/*/test_cases.json
    files on disk — these tests read the actual files checked into this
    repository, they don't invent any test case."""

    def test_sync_creates_real_cases_from_disk_for_enabled_agents(self):
        golden_dataset.sync_golden_dataset()
        self.assertGreater(GoldenDatasetCase.objects.count(), 0)

    def test_sync_is_idempotent_no_duplicates_on_repeat_call(self):
        golden_dataset.sync_golden_dataset()
        first_count = GoldenDatasetCase.objects.count()
        golden_dataset.sync_golden_dataset()
        self.assertEqual(GoldenDatasetCase.objects.count(), first_count)

    def test_every_synced_case_has_a_real_case_id_and_known_type(self):
        golden_dataset.sync_golden_dataset()
        for case in GoldenDatasetCase.objects.all():
            self.assertTrue(case.case_id)
            self.assertIn(case.case_type, ('realistic', 'failure'))

    def test_realistic_case_expected_properties_carry_a_confidence_key(self):
        golden_dataset.sync_golden_dataset()
        realistic = GoldenDatasetCase.objects.filter(case_type='realistic').first()
        self.assertIsNotNone(realistic)
        self.assertIn('confidence', realistic.expected_properties)

    def test_failure_case_expected_properties_carry_an_expected_behaviour_key(self):
        golden_dataset.sync_golden_dataset()
        failure = GoldenDatasetCase.objects.filter(case_type='failure').first()
        self.assertIsNotNone(failure)
        self.assertIn('expected_behaviour', failure.expected_properties)


class EvaluationEngineTests(TestCase):
    def setUp(self):
        self.agent = AgentRegistryEntry.objects.create(agent_id='eval-test-agent', agent_name='Eval Test Agent')

    def _make_completed_run(self, **kwargs):
        defaults = {
            'agent': self.agent, 'task_type': 'demo', 'execution_mode_requested': 'deterministic_test',
            'status': 'completed', 'safety_status': 'pass', 'schema_valid': True,
            'evidence_used': ['source-a'], 'audit_trail': [{'ts': 'x', 'event': 'y'}],
        }
        defaults.update(kwargs)
        return AgentRun.objects.create(**defaults)

    def test_first_evaluation_has_no_previous_and_no_delta(self):
        self._make_completed_run()
        evaluation = run_agent_evaluation(self.agent)
        self.assertIsNone(evaluation.previous_evaluation)
        self.assertEqual(evaluation.score_delta, {})
        self.assertEqual(evaluation.runs_evaluated_count, 1)

    def test_evaluation_updates_registry_last_evaluation_score(self):
        self._make_completed_run()
        evaluation = run_agent_evaluation(self.agent)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.last_evaluation_score, evaluation.overall_score)

    def test_second_evaluation_links_to_first_and_computes_a_delta(self):
        self._make_completed_run()
        first = run_agent_evaluation(self.agent, evaluation_version='v1')
        self._make_completed_run(safety_status='blocking')
        second = run_agent_evaluation(self.agent, evaluation_version='v2')
        self.assertEqual(second.previous_evaluation_id, first.pk)
        self.assertIn('overall_score', second.score_delta)

    def test_evaluation_with_no_runs_has_no_overall_score(self):
        evaluation = run_agent_evaluation(self.agent)
        self.assertIsNone(evaluation.overall_score)
        self.assertEqual(evaluation.runs_evaluated_count, 0)

    def test_evaluation_checks_real_golden_dataset_cases(self):
        GoldenDatasetCase.objects.create(
            agent=self.agent, case_id='TC-01', case_type='realistic',
            expected_properties={'confidence': 80, 'human_approval_required': True},
        )
        self._make_completed_run(calibrated_confidence=82, human_approval_required=True)
        evaluation = run_agent_evaluation(self.agent)
        self.assertEqual(evaluation.golden_cases_checked, 1)
        self.assertEqual(evaluation.golden_cases_passed, 1)

    def test_evaluation_records_golden_case_failure_reason_honestly(self):
        GoldenDatasetCase.objects.create(
            agent=self.agent, case_id='TC-02', case_type='realistic',
            expected_properties={'confidence': 10, 'human_approval_required': False},
        )
        self._make_completed_run(calibrated_confidence=95, human_approval_required=True)
        evaluation = run_agent_evaluation(self.agent)
        self.assertEqual(evaluation.golden_cases_passed, 0)
        self.assertEqual(len(evaluation.failure_reasons), 1)
        self.assertIn('TC-02', evaluation.failure_reasons[0])


class RegressionDetectionTests(TestCase):
    """
    Regression detection is demonstrated here with explicitly synthetic,
    test-only AgentEvaluationRun rows — never by fabricating a decline in
    a real agent's real production data. detect_regressions() never
    modifies the agent itself; it only ever creates an AgentRegression row.
    """

    def setUp(self):
        self.agent = AgentRegistryEntry.objects.create(agent_id='regression-test-agent', agent_name='Regression Test Agent')

    def _make_evaluation(self, overall_score, metrics_dict=None, previous=None):
        evaluation = AgentEvaluationRun.objects.create(
            agent=self.agent, overall_score=overall_score, metrics=metrics_dict or {}, previous_evaluation=previous,
        )
        if previous is not None:
            delta = {}
            if previous.overall_score is not None and overall_score is not None:
                delta['overall_score'] = round(overall_score - previous.overall_score, 1)
            for name, result in (metrics_dict or {}).items():
                prev_score = (previous.metrics or {}).get(name, {}).get('score')
                if prev_score is not None and result.get('score') is not None:
                    delta[name] = round(result['score'] - prev_score, 1)
            evaluation.score_delta = delta
            evaluation.save(update_fields=['score_delta'])
        return evaluation

    def test_no_regressions_when_no_previous_evaluation(self):
        evaluation = self._make_evaluation(overall_score=80.0)
        self.assertEqual(regression_detection.detect_regressions(evaluation), [])

    def test_no_regressions_when_scores_are_stable(self):
        first = self._make_evaluation(overall_score=80.0, metrics_dict={'factual_grounding': {'score': 80.0}})
        second = self._make_evaluation(overall_score=80.0, metrics_dict={'factual_grounding': {'score': 80.0}}, previous=first)
        self.assertEqual(regression_detection.detect_regressions(second), [])

    def test_detects_a_synthetic_overall_score_decline(self):
        first = self._make_evaluation(overall_score=90.0)
        second = self._make_evaluation(overall_score=80.0, previous=first)  # -10, exceeds the 5.0 threshold
        findings = regression_detection.detect_regressions(second)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].metric_name, 'overall_score')
        self.assertEqual(findings[0].previous_value, 90.0)
        self.assertEqual(findings[0].current_value, 80.0)

    def test_severity_scales_with_size_of_the_decline(self):
        first = self._make_evaluation(overall_score=90.0)
        second = self._make_evaluation(overall_score=79.0, previous=first)  # -11, over 2x the 5.0 threshold
        findings = regression_detection.detect_regressions(second)
        self.assertEqual(findings[0].severity, 'high')

    def test_a_metric_specific_regression_is_detected_independent_of_overall_score(self):
        first = self._make_evaluation(overall_score=80.0, metrics_dict={'evidence_coverage': {'score': 90.0}})
        second = self._make_evaluation(overall_score=80.0, metrics_dict={'evidence_coverage': {'score': 70.0}}, previous=first)
        findings = regression_detection.detect_regressions(second)
        self.assertIn('evidence_coverage', [f.metric_name for f in findings])

    def test_latency_increase_is_treated_as_a_regression(self):
        first = self._make_evaluation(overall_score=80.0, metrics_dict={'latency': {'score': 5.0}})
        second = self._make_evaluation(overall_score=80.0, metrics_dict={'latency': {'score': 10.0}}, previous=first)
        findings = regression_detection.detect_regressions(second)
        self.assertIn('latency', [f.metric_name for f in findings])

    def test_regression_detection_never_modifies_the_agent_itself(self):
        agent_name_before = self.agent.agent_name
        first = self._make_evaluation(overall_score=90.0)
        second = self._make_evaluation(overall_score=80.0, previous=first)
        regression_detection.detect_regressions(second)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.agent_name, agent_name_before)


class RecommendationsTests(TestCase):
    def setUp(self):
        self.agent = AgentRegistryEntry.objects.create(agent_id='rec-test-agent', agent_name='Rec Test Agent')

    def _make_evaluation(self, **metric_scores):
        metrics_dict = {name: {'score': score} for name, score in metric_scores.items()}
        return AgentEvaluationRun.objects.create(agent=self.agent, metrics=metrics_dict)

    def test_low_evidence_coverage_triggers_improve_evidence_retrieval(self):
        evaluation = self._make_evaluation(evidence_coverage=30.0)
        recs = recommendations.generate_recommendations(evaluation)
        self.assertTrue(any(r.recommendation_type == 'improve_evidence_retrieval' for r in recs))

    def test_low_evidence_quality_triggers_increase_evidence_threshold(self):
        evaluation = self._make_evaluation(evidence_quality=20.0)
        recs = recommendations.generate_recommendations(evaluation)
        self.assertTrue(any(r.recommendation_type == 'increase_evidence_threshold' for r in recs))

    def test_low_calibration_triggers_review_confidence_calibration(self):
        evaluation = self._make_evaluation(confidence_calibration=10.0)
        recs = recommendations.generate_recommendations(evaluation)
        self.assertTrue(any(r.recommendation_type == 'review_confidence_calibration' for r in recs))

    def test_low_reliability_triggers_investigate_failure_category(self):
        evaluation = self._make_evaluation(reliability=50.0)
        recs = recommendations.generate_recommendations(evaluation)
        self.assertTrue(any(r.recommendation_type == 'investigate_failure_category' for r in recs))

    def test_low_trace_completeness_triggers_inspect_orchestration_failures(self):
        evaluation = self._make_evaluation(reasoning_trace_completeness=10.0)
        recs = recommendations.generate_recommendations(evaluation)
        self.assertTrue(any(r.recommendation_type == 'inspect_orchestration_failures' for r in recs))

    def test_no_recommendations_when_all_metrics_are_healthy(self):
        evaluation = self._make_evaluation(
            evidence_coverage=90.0, evidence_quality=90.0, confidence_calibration=90.0,
            reliability=95.0, reasoning_trace_completeness=90.0,
        )
        recs = recommendations.generate_recommendations(evaluation)
        self.assertEqual(recs, [])

    def test_low_golden_pass_rate_triggers_expand_golden_dataset(self):
        evaluation = AgentEvaluationRun.objects.create(agent=self.agent, golden_cases_checked=5, golden_cases_passed=1)
        recs = recommendations.generate_recommendations(evaluation)
        self.assertTrue(any(r.recommendation_type == 'expand_golden_dataset' for r in recs))

    def test_recommendation_names_the_triggering_evaluation_in_based_on(self):
        evaluation = self._make_evaluation(evidence_coverage=10.0)
        recs = recommendations.generate_recommendations(evaluation)
        self.assertIn(evaluation.pk, recs[0].based_on.get('evaluation_run_ids', []))

    def test_negative_human_feedback_rate_triggers_a_recommendation(self):
        run = AgentRun.objects.create(agent=self.agent, task_type='demo', execution_mode_requested='deterministic_test')
        AgentHumanFeedback.objects.create(agent_run=run, classification='INCORRECT')
        AgentHumanFeedback.objects.create(agent_run=run, classification='APPROVED')
        evaluation = self._make_evaluation(
            evidence_coverage=90.0, evidence_quality=90.0, confidence_calibration=90.0,
            reliability=95.0, reasoning_trace_completeness=90.0,
        )
        recs = recommendations.generate_recommendations(evaluation)
        self.assertTrue(any(r.recommendation_type == 'investigate_failure_category' for r in recs))

    def test_recommendations_never_modify_the_agent_or_the_run(self):
        run = AgentRun.objects.create(
            agent=self.agent, task_type='demo', execution_mode_requested='deterministic_test', status='completed',
        )
        evaluation = self._make_evaluation(evidence_coverage=10.0)
        recommendations.generate_recommendations(evaluation)
        run.refresh_from_db()
        self.assertEqual(run.status, 'completed')


class HumanFeedbackModelTests(TestCase):
    def test_str_shows_classification_label_not_a_social_rating(self):
        agent = AgentRegistryEntry.objects.create(agent_id='feedback-test-agent', agent_name='Feedback Test Agent')
        run = AgentRun.objects.create(agent=agent, task_type='demo', execution_mode_requested='deterministic_test')
        feedback = AgentHumanFeedback.objects.create(agent_run=run, classification='NEEDS_IMPROVEMENT')
        self.assertIn('Needs Improvement', str(feedback))


class AdminObservabilityTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.admin_user = User.objects.create_superuser('lab-admin', 'lab-admin@example.com', 'password123')
        self.client.force_login(self.admin_user)
        self.agent = AgentRegistryEntry.objects.create(agent_id='admin-test-agent', agent_name='Admin Test Agent')

    def test_golden_dataset_case_visible_but_not_addable(self):
        GoldenDatasetCase.objects.create(agent=self.agent, case_id='TC-ADMIN-01', case_type='realistic')
        response = self.client.get('/admin/agent_training_evaluation_lab/goldendatasetcase/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TC-ADMIN-01')
        add_response = self.client.get('/admin/agent_training_evaluation_lab/goldendatasetcase/add/')
        self.assertEqual(add_response.status_code, 403)

    def test_evaluation_run_visible_but_not_addable(self):
        AgentEvaluationRun.objects.create(agent=self.agent, overall_score=75.5)
        response = self.client.get('/admin/agent_training_evaluation_lab/agentevaluationrun/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '75.5')
        add_response = self.client.get('/admin/agent_training_evaluation_lab/agentevaluationrun/add/')
        self.assertEqual(add_response.status_code, 403)

    def test_regression_acknowledge_action_sets_reviewer_and_never_edits_agent(self):
        evaluation = AgentEvaluationRun.objects.create(agent=self.agent, overall_score=70.0)
        regression = AgentRegression.objects.create(
            agent=self.agent, evaluation_run=evaluation, metric_name='overall_score',
            previous_value=90.0, current_value=70.0, threshold=5.0, severity='high',
        )
        agent_name_before = self.agent.agent_name
        response = self.client.post('/admin/agent_training_evaluation_lab/agentregression/', {
            'action': 'acknowledge_selected',
            '_selected_action': [str(regression.pk)],
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        regression.refresh_from_db()
        self.assertTrue(regression.is_acknowledged)
        self.assertEqual(regression.acknowledged_by_id, self.admin_user.pk)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.agent_name, agent_name_before)

    def test_human_feedback_admin_allows_add_and_auto_assigns_reviewer(self):
        run = AgentRun.objects.create(agent=self.agent, task_type='demo', execution_mode_requested='deterministic_test')
        response = self.client.post('/admin/agent_training_evaluation_lab/agenthumanfeedback/add/', {
            'agent_run': run.pk, 'classification': 'APPROVED', 'notes': '',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        feedback = AgentHumanFeedback.objects.get(agent_run=run)
        self.assertEqual(feedback.reviewer_id, self.admin_user.pk)

    def test_improvement_recommendation_dismiss_action(self):
        rec = ImprovementRecommendation.objects.create(
            agent=self.agent, recommendation_type='improve_evidence_retrieval', description='test',
        )
        response = self.client.post('/admin/agent_training_evaluation_lab/improvementrecommendation/', {
            'action': 'mark_dismissed',
            '_selected_action': [str(rec.pk)],
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        rec.refresh_from_db()
        self.assertEqual(rec.status, 'DISMISSED')
