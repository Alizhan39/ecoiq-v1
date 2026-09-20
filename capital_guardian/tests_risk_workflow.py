from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from ai_observatory.models import AnalysisSession
from capital_guardian.models import CapitalTraceEntry, RiskFollowUp
from capital_guardian.services import risk_workflow as workflow
from evidence_memory.models import EvidenceMemory
from gold_intelligence.models import GoldProject, ProjectMembership


@override_settings(ALLOWED_HOSTS=['testserver'])
class RiskWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = GoldProject.objects.create(name='Workflow controls', slug='workflow-controls')
        cls.other = GoldProject.objects.create(name='Other project', slug='workflow-other')
        cls.analyst = get_user_model().objects.create_user('wf-analyst')
        cls.reviewer = get_user_model().objects.create_user('wf-reviewer')
        cls.viewer = get_user_model().objects.create_user('wf-viewer')
        for user, role in ((cls.analyst, 'analyst'), (cls.reviewer, 'reviewer'), (cls.viewer, 'viewer')):
            ProjectMembership.objects.create(project=cls.project, user=user, role=role)
        cls.entry = CapitalTraceEntry.objects.create(project=cls.project, date=date(2026, 9, 1),
                                                   amount_usd=100, purpose='Test delivery', payment_status='paid', is_demo=False)
        cls.rule = f'evidence_missing_{cls.entry.pk}'

    def start(self):
        return workflow.start_followup(self.project, self.analyst, self.rule)

    def document(self):
        return EvidenceMemory.objects.create(project=self.project,
            source_reference=f'capital_guardian.CapitalTraceEntry:{self.entry.pk}',
            text_chunk='Delivery note: test equipment received.', is_demo=False)

    def ready(self):
        task = self.start()
        document = self.document()
        workflow.submit_document(task.pk, self.project, self.analyst, document.pk)
        return task, document

    def test_full_api_process_and_duplicate_delivery(self):
        client = APIClient()
        client.force_authenticate(self.analyst)
        start_url = reverse('api_v2:risk_workflows', args=[self.project.slug])
        first = client.post(start_url, {'rule_key': self.rule}, format='json')
        self.assertEqual(first.status_code, 200, first.data)
        task_id = first.data['id']
        self.assertEqual(client.post(start_url, {'rule_key': self.rule}).data['id'], task_id)
        self.assertEqual(RiskFollowUp.objects.count(), 1)
        document = self.document()
        original_verification = document.verification_status
        url = reverse('api_v2:risk_workflow_detail', args=[self.project.slug, task_id])
        result = client.post(url, {'action': 'document', 'memory_id': document.pk}, format='json')
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data['state'], 'awaiting_approval')
        self.assertTrue(result.data['score']['available'])
        self.assertEqual(result.data['citation']['quote'], document.text_chunk)
        self.assertEqual(result.data['trace']['model_calls'], [])
        self.assertIsNone(result.data['trace']['actual_cost_usd'])
        self.assertEqual(client.post(url, {'action': 'document', 'memory_id': document.pk}).data['attempts'], 1)
        self.assertEqual(client.post(url, {'action': 'recalculate'}).data['attempts'], 1)
        client.force_authenticate(self.reviewer)
        payload = {'action': 'review', 'decision': 'approved', 'assessment_digest': result.data['assessment_digest'],
                   'notes': 'Reviewed this source and recalculated assessment; no payment authorised.'}
        approved = client.post(url, payload, format='json')
        self.assertEqual(approved.status_code, 200, approved.data)
        self.assertEqual(approved.data['state'], 'approved')
        self.assertEqual(client.post(url, payload, format='json').data['state'], 'approved')
        task = RiskFollowUp.objects.get(pk=task_id)
        self.assertEqual(task.session.stages.filter(stage_key='human_review_recorded').count(), 1)
        self.assertEqual(task.session.stages.get(stage_key='human_review_recorded').actor_id, self.reviewer.pk)
        self.assertTrue(task.session.human_review_completed)
        document.refresh_from_db()
        self.assertEqual(document.verification_status, original_verification)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.verification_status, 'unverified')

    def test_failure_recovery_uses_persisted_checkpoint(self):
        task, document = self.ready()
        with patch.object(workflow, 'compute_capital_protection_score', side_effect=RuntimeError('secret credential text')):
            failed = workflow.advance(task.pk, self.project, self.analyst)
        self.assertEqual(failed.state, 'failed')
        self.assertEqual(failed.last_error, 'RuntimeError')
        self.assertNotIn('secret credential', str(workflow.task_detail(failed, self.analyst)))
        recovered = workflow.advance(RiskFollowUp.objects.get(pk=task.pk).pk, self.project, self.analyst)
        self.assertEqual(recovered.state, 'awaiting_approval')
        self.assertEqual(recovered.attempts, 2)
        self.assertEqual(recovered.session.stages.filter(stage_key='document_requested').count(), 1)
        self.assertEqual(recovered.session.stages.filter(stage_key='score_recalculated').count(), 1)
        self.assertEqual(workflow.advance(task.pk, self.project, self.analyst).attempts, 2)

    def test_bounded_failures(self):
        task, _ = self.ready()
        with patch.object(workflow, 'compute_capital_protection_score', side_effect=RuntimeError):
            for _ in range(workflow.MAX_ATTEMPTS):
                workflow.advance(task.pk, self.project, self.analyst)
            with self.assertRaises(ValueError):
                workflow.advance(task.pk, self.project, self.analyst)

    def test_audit_failure_rolls_back_task_creation(self):
        with patch.object(workflow, '_event', side_effect=RuntimeError), self.assertRaises(RuntimeError):
            self.start()
        self.assertFalse(RiskFollowUp.objects.exists())
        self.assertFalse(AnalysisSession.objects.exists())
        self.assertEqual(self.start().state, 'awaiting_document')

    def test_interruption_between_document_and_score_can_resume(self):
        task, _ = self.ready()
        self.assertEqual(RiskFollowUp.objects.get(pk=task.pk).state, 'ready')
        self.assertEqual(workflow.advance(task.pk, self.project, self.analyst).state, 'awaiting_approval')

    def test_roles_cross_project_and_self_approval(self):
        with self.assertRaises(PermissionDenied):
            workflow.start_followup(self.project, self.viewer, self.rule)
        task, _ = self.ready()
        task = workflow.advance(task.pk, self.project, self.analyst)
        with self.assertRaises(PermissionDenied):
            workflow.advance(task.pk, self.other, self.analyst)
        ProjectMembership.objects.filter(user=self.analyst).update(role='manager')
        with self.assertRaises(PermissionDenied):
            workflow.review(task.pk, self.project, self.analyst, 'approved', task.assessment_digest, 'Self review')
        ProjectMembership.objects.filter(user=self.reviewer).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            workflow.review(task.pk, self.project, self.reviewer, 'approved', task.assessment_digest, 'Review')

    def test_wrong_document_and_expired_or_changed_source(self):
        task = self.start()
        document = self.document()
        document.source_reference = 'unrelated'
        document.save()
        with self.assertRaises(ValueError):
            workflow.submit_document(task.pk, self.project, self.analyst, document.pk)
        document.source_reference = f'capital_guardian.CapitalTraceEntry:{self.entry.pk}'
        document.save()
        workflow.submit_document(task.pk, self.project, self.analyst, document.pk)
        task = workflow.advance(task.pk, self.project, self.analyst)
        document.text_chunk = 'The source was corrected.'
        document.save()
        with self.assertRaises(ValueError):
            workflow.review(task.pk, self.project, self.reviewer, 'approved', task.assessment_digest, 'Review')
        document.expiry_date = date(2000, 1, 1)
        document.save()
        with self.assertRaises(PermissionDenied):
            workflow.submit_document(task.pk, self.project, self.analyst, document.pk)

    def test_stale_assessment_requires_recalculation_and_reject_is_final(self):
        task, _ = self.ready()
        task = workflow.advance(task.pk, self.project, self.analyst)
        old_digest = task.assessment_digest
        self.entry.verification_status = 'verified'
        self.entry.save()
        with self.assertRaises(ValueError):
            workflow.review(task.pk, self.project, self.reviewer, 'approved', old_digest, 'Review')
        task = workflow.recalculate(task.pk, self.project, self.analyst)
        self.assertNotEqual(task.assessment_digest, old_digest)
        task = workflow.review(task.pk, self.project, self.reviewer, 'rejected', task.assessment_digest, 'Insufficient supporting review.')
        self.assertEqual(task.state, 'rejected')
        with self.assertRaises(ValueError):
            workflow.review(task.pk, self.project, self.reviewer, 'approved', task.assessment_digest, 'Changed decision')

    def test_revoked_source_redacts_cached_trace(self):
        task, document = self.ready()
        task = workflow.advance(task.pk, self.project, self.analyst)
        document.verification_status = 'rejected'
        document.save()
        output = workflow.task_detail(task, self.analyst)
        self.assertIsNone(output['trace'])
        self.assertIsNone(output['score'])
        self.assertIsNone(output['citation'])

    def test_api_rejects_forged_identity_missing_fields_and_csrf(self):
        task = self.start()
        url = reverse('api_v2:risk_workflow_detail', args=[self.project.slug, task.pk])
        client = APIClient()
        self.assertEqual(client.get(url).status_code, 403)
        client.force_authenticate(self.viewer)
        self.assertEqual(client.post(url, {'action': 'resume', 'user_id': self.analyst.pk}).status_code, 403)
        client.force_authenticate(self.analyst)
        self.assertEqual(client.post(url, {'action': 'document'}).status_code, 400)
        self.assertEqual(client.get(reverse('api_v2:risk_workflow_detail', args=[self.other.slug, task.pk])).status_code, 404)
        csrf = APIClient(enforce_csrf_checks=True)
        csrf.force_login(self.analyst)
        self.assertEqual(csrf.post(url, {'action': 'resume'}).status_code, 403)

    def test_approval_and_audit_are_atomic(self):
        task, _ = self.ready()
        task = workflow.advance(task.pk, self.project, self.analyst)
        with patch.object(workflow, '_event', side_effect=RuntimeError), self.assertRaises(RuntimeError):
            workflow.review(task.pk, self.project, self.reviewer, 'approved', task.assessment_digest, 'Review')
        task.refresh_from_db()
        self.assertEqual(task.state, 'awaiting_approval')
        self.assertIsNone(task.reviewed_by)
