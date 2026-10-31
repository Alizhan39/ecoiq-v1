"""Project grants, identity propagation and revocation across real consumers."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.urls import reverse

from evidence_memory.models import EvidenceMemory
from evidence_memory.services.embeddings import compute_embedding
from evidence_memory.services.memory import search_similar
from evidence_memory.services.retrieval_policy import set_visibility
from gold_intelligence import access
from gold_intelligence.models import GoldProject, ProjectMembership


@override_settings(ALLOWED_HOSTS=['*'])
class ProjectAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = GoldProject.objects.create(name='Private heating project', slug='private-heating', is_demo=False)
        cls.other = GoldProject.objects.create(name='Other private project', slug='other-private', is_demo=False)
        cls.users = {}
        for role in ProjectMembership.Role.values:
            user = get_user_model().objects.create_user(f'project-{role}')
            ProjectMembership.objects.create(project=cls.project, user=user, role=role)
            cls.users[role] = user
        cls.stranger = get_user_model().objects.create_user('project-stranger')
        cls.staff = get_user_model().objects.create_user('project-staff', is_staff=True)
        cls.memory = EvidenceMemory.objects.create(
            project=cls.project, text_chunk='PRIVATE HEATING EVIDENCE: insulation reduces heat loss.',
            source_reference=f'gold_intelligence.GoldProject:{cls.project.pk}',
            embedding=compute_embedding('insulation heat loss'), embedding_status='embedded',
        )
        cls.other_memory = EvidenceMemory.objects.create(
            project=cls.other, text_chunk='OTHER PRIVATE HEATING EVIDENCE',
            embedding=cls.memory.embedding, embedding_status='embedded',
        )

    def setUp(self):
        cache.clear()

    def test_role_matrix_and_project_boundary(self):
        expected = {'viewer': {'read'}, 'analyst': {'read', 'analyse'},
                    'reviewer': {'read', 'approve'}, 'manager': {'read', 'analyse', 'share', 'approve'}}
        for role, permissions in expected.items():
            for permission in ('read', 'analyse', 'share', 'approve'):
                with self.subTest(role=role, permission=permission):
                    self.assertEqual(access.can(self.users[role], self.project, permission), permission in permissions)
                    self.assertFalse(access.can(self.users[role], self.other, permission))
        self.assertTrue(access.can(self.staff, self.other, access.APPROVE))
        self.assertFalse(access.can(self.staff, self.project, 'unknown-action'))

    def test_member_search_and_revocation(self):
        viewer = self.users['viewer']
        self.assertEqual([r.pk for r in search_similar('heat loss', project=self.project, user=viewer)], [self.memory.pk])
        ProjectMembership.objects.filter(user=viewer).update(is_active=False)
        self.assertEqual(search_similar('heat loss', project=self.project, user=viewer), [])
        with self.assertRaises(PermissionDenied):
            access.resolve_context(viewer.pk, self.project.pk, permission=access.READ)

    def test_inactive_account_and_missing_context_fail_closed(self):
        analyst = self.users['analyst']
        get_user_model().objects.filter(pk=analyst.pk).update(is_active=False)
        for actor_id, project_id in ((analyst.pk, self.project.pk), (self.staff.pk, None),
                                     (None, self.project.pk), (self.staff.pk, 'bad-id')):
            with self.subTest(actor=actor_id, project=project_id), self.assertRaises(PermissionDenied):
                access.resolve_context(actor_id, project_id)

    def test_only_project_manager_can_share(self):
        for user in (None, self.stranger, self.users['viewer'], self.users['analyst'], self.users['reviewer']):
            with self.subTest(user=user), self.assertRaises(PermissionDenied):
                set_visibility(self.memory, 'project_private', actor=user)
        self.memory.organisation = 'Trusted organisation'
        self.memory.save()
        set_visibility(self.memory, 'organisation_shared', actor=self.users['manager'])
        self.memory.refresh_from_db()
        self.assertEqual(self.memory.visibility, 'organisation_shared')
        with self.assertRaises(PermissionDenied):
            set_visibility(self.other_memory, 'project_private', actor=self.users['manager'])

    def test_company_link_does_not_publish_project_evidence(self):
        from types import SimpleNamespace
        from evidence_memory.services.retrieval_policy import is_company_record_accessible
        self.assertFalse(is_company_record_accessible(self.memory, SimpleNamespace(pk=self.memory.company_id)))

    def test_studio_uses_logged_in_actor_and_preserves_project_in_followup(self):
        from decision_studio.models import DecisionQuery
        self.client.force_login(self.users['analyst'])
        response = self.client.post(reverse('decision_studio:ask'), {
            'question': 'Where is the evidence too weak?', 'project_id': self.project.pk,
            'requesting_user_id': self.stranger.pk,
        })
        self.assertEqual(response.status_code, 302)
        query = DecisionQuery.objects.latest('pk')
        self.assertEqual(query.project_id, self.project.pk)
        self.assertEqual(query.user_id, self.users['analyst'].pk)
        self.assertIn(self.memory.text_chunk, str(query.result['supporting_evidence']))
        self.assertNotIn(self.other_memory.text_chunk, str(query.result))
        self.assertEqual(self.client.post(reverse('decision_studio:ask'), {
            'question': 'What evidence is available?', 'parent_query_id': query.pk,
        }).status_code, 302)
        self.assertEqual(DecisionQuery.objects.latest('pk').project_id, self.project.pk)
        self.assertEqual(self.client.post(reverse('decision_studio:ask'), {
            'question': 'What evidence is available?', 'parent_query_id': query.pk, 'project_id': self.other.pk,
        }).status_code, 404)

    def test_suggested_question_uses_the_selected_project(self):
        from decision_studio.models import DecisionQuery
        self.client.force_login(self.users['analyst'])
        response = self.client.post(reverse('decision_studio:ask'), {
            'question': '', 'suggested_question': 'Where is the evidence too weak?',
            'project_id': self.project.pk,
        })
        self.assertEqual(response.status_code, 302)
        query = DecisionQuery.objects.latest('pk')
        self.assertEqual(query.project_id, self.project.pk)
        self.assertIn(self.memory.text_chunk, str(query.result['supporting_evidence']))

    def test_studio_viewer_cannot_analyse_or_spoof_actor(self):
        from decision_studio.models import DecisionQuery
        self.client.force_login(self.users['viewer'])
        response = self.client.post(reverse('decision_studio:ask'), {
            'question': 'Show evidence', 'project_id': self.project.pk, 'user_id': self.staff.pk,
        })
        self.assertEqual(response.status_code, 404)
        self.assertFalse(DecisionQuery.objects.exists())

    def test_saved_query_requires_ownership_and_current_membership(self):
        from decision_studio.models import DecisionQuery
        self.client.force_login(self.users['analyst'])
        query = DecisionQuery.objects.create(
            question_text='Private question', user=self.users['analyst'], project=self.project,
            session_key=self.client.session.session_key, result={'supporting_evidence': [self.memory.text_chunk]},
        )
        url = reverse('decision_studio:result_detail', args=[query.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        ProjectMembership.objects.filter(user=self.users['analyst']).update(is_active=False)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertNotContains(self.client.get(reverse('decision_studio:studio')), query.question_text)
        self.assertEqual(self.client.post(reverse('decision_studio:ask'), {
            'question': 'Continue', 'parent_query_id': query.pk,
        }).status_code, 404)
        self.client.force_login(self.users['manager'])
        self.assertEqual(self.client.get(url).status_code, 404)
        with self.assertRaises(ProtectedError):
            self.project.delete()

    def test_graph_reads_project_evidence_and_rechecks_revoked_roles(self):
        from langgraph_orchestration.graph import run_orchestration
        kwargs = dict(user_request='insulation heat loss', latitude=1, longitude=1,
                      requesting_user_id=self.users['analyst'].pk, project_id=self.project.pk)
        with patch('langgraph_orchestration.nodes.gather_geo_intelligence', side_effect=lambda state: state):
            state = run_orchestration(**kwargs)
        self.assertEqual([m['id'] for m in state['evidence_context']['memories']], [self.memory.pk])
        ProjectMembership.objects.filter(user=self.users['analyst']).update(role='viewer')
        with patch('langgraph_orchestration.nodes.retrieve_evidence_memory') as retrieval:
            denied = run_orchestration(**kwargs)
        retrieval.assert_not_called()
        self.assertEqual(denied['status'], 'failed')
        self.assertEqual(denied['evidence_context'], {})

    def test_graph_clears_context_when_membership_is_revoked_between_nodes(self):
        from langgraph_orchestration.graph import run_orchestration
        from langgraph_orchestration.nodes import retrieve_evidence_memory
        def retrieve_then_revoke(state):
            state = retrieve_evidence_memory(state)
            ProjectMembership.objects.filter(user=self.users['analyst']).update(is_active=False)
            return state
        with patch('langgraph_orchestration.nodes.retrieve_evidence_memory', side_effect=retrieve_then_revoke), \
                patch('langgraph_orchestration.nodes.gather_geo_intelligence') as geo:
            state = run_orchestration(user_request='heat loss', latitude=1, longitude=1,
                                      requesting_user_id=self.users['analyst'].pk, project_id=self.project.pk)
        geo.assert_not_called()
        self.assertEqual(state['evidence_context'], {})
        self.assertEqual(state['status'], 'failed')

    def test_queued_graph_persists_context_and_result_access_is_revocable(self):
        from backend_intelligence_engine.tasks import run_langgraph_intelligence_workflow
        from backend_intelligence_engine.models import BackgroundTaskRun
        from langgraph_orchestration.models import OrchestrationRun
        kwargs = dict(user_request='heat loss', latitude=1, longitude=1,
                      requesting_user_id=self.users['analyst'].pk, project_id=self.project.pk)
        with patch('langgraph_orchestration.nodes.gather_geo_intelligence', side_effect=lambda state: state):
            result = run_langgraph_intelligence_workflow.apply(kwargs=kwargs).get()
        run = OrchestrationRun.objects.get(pk=result['orchestration_run_id'])
        self.assertEqual(run.project_id, self.project.pk)
        self.assertEqual(BackgroundTaskRun.objects.latest('pk').task_kwargs['requesting_user_id'], self.users['analyst'].pk)
        url = reverse('ai_agent_workbench:orchestration_detail', args=[run.pk])
        self.client.force_login(self.users['viewer'])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(url).status_code, 404)
        ProjectMembership.objects.filter(user=self.users['analyst']).update(is_active=False)
        denied = run_langgraph_intelligence_workflow.apply(kwargs=kwargs).get()
        self.assertEqual(denied['reason'], 'invalid_retrieval_context')
        self.assertEqual(OrchestrationRun.objects.count(), 1)

    def test_agent_idempotency_and_details_do_not_cross_projects(self):
        from agent_runtime_model_router.models import AgentRegistryEntry
        from agent_runtime_model_router.services.execution import create_agent_run, submit_agent_position_to_council
        agent = AgentRegistryEntry.objects.create(agent_id='project-access-agent', agent_name='Project Access Agent')
        first = create_agent_run(agent.agent_name, 'analysis', execution_mode='deterministic_test',
                                 input_summary='PRIVATE PROMPT', project=self.project, user=self.users['analyst'])
        first.status = 'completed'
        first.save()
        same = create_agent_run(agent.agent_name, 'analysis', execution_mode='deterministic_test',
                                input_summary='PRIVATE PROMPT', project=self.project, user=self.users['analyst'])
        other = create_agent_run(agent.agent_name, 'analysis', execution_mode='deterministic_test',
                                 input_summary='PRIVATE PROMPT', project=self.other, user=self.staff)
        self.assertEqual(same.pk, first.pk)
        self.assertNotEqual(other.pk, first.pk)
        with self.assertRaises(ValueError):
            submit_agent_position_to_council(first)
        url = reverse('agent_runtime_model_router:run_detail', args=[first.pk])
        self.client.force_login(self.users['viewer'])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_project_pages_require_a_read_grant(self):
        url = reverse('capital_guardian:evidence_centre', args=[self.project.slug])
        self.client.force_login(self.users['viewer'])
        self.assertContains(self.client.get(url), self.memory.text_chunk)
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_manager_can_use_sharing_page_without_staff_write_forms(self):
        from waste_to_value_capital_allocation_engine.models import (
            OperationalLoss, InterventionOption, CapitalAllocationDecision, VerifiedCapitalOutcome,
        )
        loss = OperationalLoss.objects.create(project=self.project.name, title='Heat loss', financial_loss_amount=10, loss_type='heat_loss')
        option = InterventionOption.objects.create(operational_loss=loss, title='Insulation', intervention_type='prevention')
        decision = CapitalAllocationDecision.objects.create(project=self.project.name, intervention=option)
        outcome = VerifiedCapitalOutcome.objects.create(decision=decision, intervention=option)
        self.memory.originating_outcome = outcome
        self.memory.source_reference = f'waste_to_value_capital_allocation_engine.VerifiedCapitalOutcome:{outcome.pk}'
        self.memory.is_demo = True
        self.memory.save()
        url = reverse('capital_guardian:record_outcome_confirm', args=[self.project.slug, decision.pk])
        share_url = reverse('capital_guardian:share_outcome_evidence', args=[self.project.slug, decision.pk])
        self.client.force_login(self.users['manager'])
        response = self.client.get(url)
        self.assertContains(response, 'Share as Demo Learning Evidence')
        self.assertNotContains(response, 'Enter Actual Results')
        self.assertEqual(self.client.post(share_url, {'visibility': 'platform_learning_demo'}).status_code, 302)
        self.memory.refresh_from_db()
        self.assertEqual(self.memory.visibility, 'platform_learning_demo')
        self.client.force_login(self.users['viewer'])
        self.assertNotContains(self.client.get(url), 'Make Project-Private Again')
        self.assertEqual(self.client.post(share_url, {'visibility': 'project_private'}).status_code, 403)

    def test_approval_service_enforces_role_and_decision_ownership(self):
        from capital_guardian.services.human_decision_gate import submit_review
        from waste_to_value_capital_allocation_engine.models import OperationalLoss, InterventionOption, CapitalAllocationDecision
        loss = OperationalLoss.objects.create(project=self.project.name, title='Heat loss', financial_loss_amount=10, loss_type='heat_loss')
        option = InterventionOption.objects.create(operational_loss=loss, title='Insulation', intervention_type='prevention')
        decision = CapitalAllocationDecision.objects.create(project=self.project.name, intervention=option)
        for actor in (self.users['analyst'], self.users['viewer'], self.stranger):
            with self.subTest(actor=actor), self.assertRaises(PermissionDenied):
                submit_review(decision, 'reject', actor, notes='Evidence missing', project=self.project)
        with self.assertRaises(PermissionDenied):
            submit_review(decision, 'reject', self.users['reviewer'], notes='Evidence missing', project=self.other)
        result = submit_review(decision, 'reject', self.users['reviewer'], notes='Evidence missing', project=self.project)
        self.assertEqual(result.new_status, 'rejected')
        self.assertEqual(result.event.actor_id, self.users['reviewer'].pk)
