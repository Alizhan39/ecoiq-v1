from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from agent_runtime_model_router.models import AgentRegistryEntry
from agent_runtime_model_router.services.execution import create_agent_run, execute_agent
from agent_runtime_model_router.services.model_adapters import AdapterResult
from ai_observatory.models import AnalysisSession
from ai_observatory.services.governance import session_trace
from evidence_memory.models import EvidenceMemory
from evidence_memory.services.citations import capture_citation
from gold_intelligence.models import GoldProject, ProjectMembership


class GovernedRouterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = GoldProject.objects.create(name='Router project', slug='router-audit')
        cls.user = get_user_model().objects.create_user('router-analyst')
        ProjectMembership.objects.create(project=cls.project, user=cls.user, role='analyst')
        cls.agent = AgentRegistryEntry.objects.create(agent_id='audit-test', agent_name='Audit Test')
        cls.memory = EvidenceMemory.objects.create(project=cls.project, text_chunk='Private source excerpt.', is_demo=False)

    def run_record(self):
        return create_agent_run(self.agent.agent_name, 'audit-check', execution_mode='live',
                                input_summary='Private prompt', evidence_provenance=[capture_citation(self.memory)],
                                user=self.user, project=self.project)

    def execute_mocked(self, run, results):
        from contextlib import ExitStack
        adapter = type('Adapter', (), {'provider': 'openai'})()
        with ExitStack() as stack:
            call = stack.enter_context(patch.object(adapter, 'run', side_effect=results, create=True))
            stack.enter_context(patch('agent_runtime_model_router.services.execution.get_adapter', return_value=adapter))
            stack.enter_context(patch('agent_runtime_model_router.services.execution.validate_training_pack', return_value={'valid': True}))
            stack.enter_context(patch('agent_runtime_model_router.services.execution.load_training_pack', return_value={
                'aliases': {'system_prompt': 'System', 'task_prompt': 'Task'}, 'test_cases': {}}))
            execute_agent(run)
            return call.call_count

    def test_sources_routing_retry_tokens_and_cost_share_one_session(self):
        run = self.run_record()
        failed = AdapterResult(status='failed', failure_reason='rate_limit', model_provider='openai', model_name='test-model')
        success = AdapterResult(status='success', model_provider='openai', model_name='test-model',
                                actual_usage={'prompt_tokens': 23, 'completion_tokens': 7},
                                output={'output_summary': 'An unverified finding', 'confidence': 30,
                                        'evidence_used': [], 'missing_data': ['review'], 'risk_flags': []})
        self.assertEqual(self.execute_mocked(run, [failed, success]), 2)
        trace = session_trace(run.observatory_session)
        self.assertEqual(len(trace['model_calls']), 2)
        self.assertIsNone(trace['model_calls'][0]['input_tokens'])
        self.assertEqual(trace['model_calls'][1]['input_tokens'], 23)
        self.assertEqual(trace['model_calls'][1]['retry_count'], 1)
        self.assertIsNone(trace['actual_cost_usd'])
        self.assertIsNotNone(trace['routes'][0]['estimated_cost_usd'])
        self.assertEqual([e['stage_key'] for e in trace['events']], ['agent_sources', 'model_routed', 'agent_result'])
        source = trace['events'][0]['metadata']['sources'][0]
        self.assertEqual(source['snapshot_sha256'], run.evidence_provenance[0]['snapshot_sha256'])
        self.assertNotIn('Private source excerpt', str(trace))
        self.assertNotIn('Private prompt', str(trace))
        # A duplicate scoped execution never makes another physical request.
        self.assertEqual(self.execute_mocked(run, []), 0)

    def test_cross_project_session_and_revoked_actor_are_rejected_before_call(self):
        run = self.run_record()
        other = GoldProject.objects.create(name='Other', slug='router-other')
        session = AnalysisSession.objects.create(project=other, user=self.user)
        with self.assertRaises(ValueError):
            execute_agent(run, observatory_session=session)
        ProjectMembership.objects.filter(user=self.user).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            execute_agent(run)
        self.assertFalse(run.observatory_session.model_invocations.exists())

    def test_changed_source_prevents_provider_call(self):
        run = self.run_record()
        self.memory.text_chunk = 'Changed source'
        self.memory.save()
        with self.assertRaises(ValueError):
            execute_agent(run)
        self.assertFalse(run.observatory_session.model_invocations.exists())

    def test_interrupted_run_is_not_automatically_replayed(self):
        run = self.run_record()
        run.status = 'running'
        run.save()
        with self.assertRaises(ValueError):
            execute_agent(run)
        self.assertFalse(run.observatory_session.model_invocations.exists())

    def test_queued_duplicates_reuse_run_but_different_question_does_not(self):
        run = self.run_record()
        self.assertEqual(self.run_record().pk, run.pk)
        changed = create_agent_run(self.agent.agent_name, 'audit-check', execution_mode='live',
                                   input_summary='A different question', evidence_provenance=run.evidence_provenance,
                                   user=self.user, project=self.project)
        self.assertNotEqual(changed.pk, run.pk)

    def test_unexpected_adapter_error_requires_manual_review(self):
        run = self.run_record()
        with self.assertRaises(RuntimeError):
            self.execute_mocked(run, [RuntimeError('private error')])
        run.refresh_from_db()
        self.assertEqual(run.status, 'needs_human_review')
        self.assertEqual(self.execute_mocked(run, []), 0)
