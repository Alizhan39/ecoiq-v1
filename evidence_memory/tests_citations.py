from copy import deepcopy

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase, override_settings
from django.urls import reverse

from decision_studio.models import DecisionQuery
from decision_studio.services.citation_support import add_claim_support
from evidence_memory.models import EvidenceCitationSnapshot, EvidenceMemory
from evidence_memory.services.citations import assess_claim, capture_citation, resolve_citation
from evidence_memory.services.embeddings import compute_embedding
from gold_intelligence.models import GoldProject, ProjectMembership


@override_settings(ALLOWED_HOSTS=['*'])
class CitationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = GoldProject.objects.create(name='Citation project', slug='citation-project')
        cls.other = GoldProject.objects.create(name='Other project', slug='citation-other')
        cls.user = get_user_model().objects.create_user('citation-analyst')
        cls.stranger = get_user_model().objects.create_user('citation-stranger')
        ProjectMembership.objects.create(project=cls.project, user=cls.user, role='analyst')
        cls.memory = EvidenceMemory.objects.create(
            project=cls.project, source_reference='manual:inspection',
            text_chunk='Flood damage is excluded. Fire damage is covered.',
            embedding=compute_embedding('Flood damage insurance'), embedding_status='embedded',
        )

    def test_exact_quote_idempotency_and_new_source_version(self):
        citation = capture_citation(self.memory, start=0, end=25)
        self.assertEqual(citation['quote'], self.memory.text_chunk[:25])
        self.assertEqual(capture_citation(self.memory, start=0, end=25), citation)
        self.assertEqual(EvidenceCitationSnapshot.objects.count(), 1)
        self.memory.text_chunk = 'Flood damage is now covered.'
        self.memory.save()
        updated = capture_citation(self.memory)
        self.assertNotEqual(updated['document_version'], citation['document_version'])
        resolved = resolve_citation(citation, user=self.user, project=self.project)
        self.assertTrue(resolved['source_changed'])
        self.assertEqual(resolved['quote'], 'Flood damage is excluded.')

    def test_snapshot_edit_and_bad_ranges_are_rejected(self):
        capture_citation(self.memory)
        with self.assertRaises(ValueError):
            EvidenceCitationSnapshot.objects.get().save()
        for start, end in ((-1, 5), (1, 0), (0, 1000), (True, 4)):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                capture_citation(self.memory, start=start, end=end)

    def test_tampered_quote_digest_and_snapshot_fail_closed(self):
        citation = capture_citation(self.memory)
        for key, value in (('quote', 'Flood is covered.'), ('snapshot_sha256', '0' * 64), ('end', 1), ('memory_id', 999)):
            altered = {**citation, key: value}
            with self.subTest(key=key), self.assertRaises(PermissionDenied):
                resolve_citation(altered, user=self.user, project=self.project)
        snapshot = EvidenceCitationSnapshot.objects.get()
        payload = deepcopy(snapshot.payload)
        payload['text'] = 'Tampered stored bytes'
        EvidenceCitationSnapshot.objects.filter(pk=snapshot.pk).update(payload=payload)
        with self.assertRaises(PermissionDenied):
            resolve_citation(citation, user=self.user, project=self.project)

    def test_unauthorised_actor_and_project_are_rejected(self):
        citation = capture_citation(self.memory)
        for user, project in ((None, self.project), (self.stranger, self.project), (self.user, self.other)):
            with self.subTest(user=user, project=project), self.assertRaises(PermissionDenied):
                resolve_citation(citation, user=user, project=project)
        ProjectMembership.objects.filter(user=self.user).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            resolve_citation(citation, user=self.user, project=self.project)

    def test_source_document_identity_location_and_version(self):
        from harvester.models import Source, SourceDocument, Evidence
        source = Source.objects.create(name='Insurer', source_type='other')
        document = SourceDocument.objects.create(source=source, company_slug='control', title='Insurance schedule',
                                                url='https://example.org/insurance', content_hash='a' * 64)
        evidence = Evidence.objects.create(document=document, company_slug='control', title='Coverage',
                                           source_location='Page 4, exclusions', excerpt=self.memory.text_chunk)
        self.memory.source_reference = f'harvester.Evidence:{evidence.pk}'
        self.memory.save()
        citation = capture_citation(self.memory)
        self.assertEqual(citation['document_title'], 'Insurance schedule')
        self.assertEqual(citation['document_version'], 'a' * 64)
        self.assertEqual(citation['source_location'], 'Page 4, exclusions')
        evidence.excerpt = 'New source text not yet synced to memory'
        evidence.save()
        stale = capture_citation(self.memory)
        self.assertIn('original document version unavailable', stale['version_kind'])

    def test_nearest_document_and_matching_id_do_not_prove_conclusion(self):
        citation = capture_citation(self.memory)
        mapping = {citation['citation_id']: citation}
        claim = {'kind': 'conclusion', 'text': 'Flood losses will be reimbursed.', 'citation_ids': [citation['citation_id']]}
        self.assertEqual(assess_claim(claim, mapping)['support_status'], 'insufficient_evidence')
        claim.update(kind='source_quote', text=citation['quote'])
        self.assertEqual(assess_claim(claim, mapping)['support_status'], 'attributed_quote')
        claim['citation_ids'] = ['invented']
        self.assertEqual(assess_claim(claim, mapping)['support_status'], 'insufficient_evidence')

    def _query(self):
        citation = capture_citation(self.memory)
        result = add_claim_support({'executive_answer': 'A candidate conclusion',
                                    'supporting_evidence': [{'excerpt': citation['quote'], 'citation': citation}]})
        return DecisionQuery.objects.create(user=self.user, project=self.project, question_text='Insurance?', result=result), citation

    def test_read_only_citation_route_checks_query_owner_and_current_role(self):
        query, citation = self._query()
        url = reverse('decision_studio:citation_detail', args=[query.pk, citation['citation_id']])
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertContains(response, citation['quote'])
        self.assertContains(response, citation['document_version'])
        self.assertContains(response, 'original document version unavailable')
        from evidence_memory.services.citations import payload_digest
        exported = self.client.get(url + '?format=json')
        self.assertEqual(exported['Cache-Control'], 'private, no-store')
        self.assertEqual(payload_digest(exported.json()['snapshot']), citation['snapshot_sha256'])
        self.assertEqual(exported.json()['snapshot']['text'], self.memory.text_chunk)
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(url + '?format=json').status_code, 404)

    def test_revoke_sharing_redacts_saved_quote_and_derived_result(self):
        self.memory.project = self.other
        self.memory.visibility = 'platform_learning_verified'
        self.memory.verification_status = 'verified'
        self.memory.review_tier = 'independently_verified'
        self.memory.save()
        query, citation = self._query()
        self.client.force_login(self.user)
        result_url = reverse('decision_studio:result_detail', args=[query.pk])
        self.assertContains(self.client.get(result_url), citation['quote'])
        self.memory.visibility = 'project_private'
        self.memory.save()
        response = self.client.get(result_url)
        self.assertNotContains(response, citation['quote'])
        self.assertNotContains(response, 'A candidate conclusion')
        self.assertContains(response, 'Insufficient evidence')
        self.assertEqual(self.client.get(reverse('decision_studio:citation_detail', args=[query.pk, citation['citation_id']])).status_code, 404)

    def test_unsafe_url_never_becomes_a_link_and_metadata_is_trusted(self):
        self.memory.source_url = 'javascript:alert(1)'
        self.memory.save()
        citation = capture_citation(self.memory)
        self.assertEqual(citation['source_url'], '')
        citation['source_url'] = 'javascript:alert(2)'
        resolved = resolve_citation(citation, user=self.user, project=self.project)
        self.assertEqual(resolved['source_url'], '')

    def test_duplicate_wording_retains_distinct_sources(self):
        from decision_studio.services.decision_engine import _retrieve_evidence
        other = EvidenceMemory.objects.create(project=self.project, text_chunk=self.memory.text_chunk,
                                               source_reference='manual:other-document', embedding=self.memory.embedding,
                                               embedding_status='embedded')
        rows = _retrieve_evidence('Flood damage insurance', [], [], user=self.user, project=self.project)
        self.assertEqual({r['memory_id'] for r in rows}, {self.memory.pk, other.pk})
        self.assertEqual(len({r['citation']['citation_id'] for r in rows}), 2)

    def test_scoped_graph_captures_versioned_sources_and_marks_unproven_findings(self):
        from langgraph_orchestration.nodes import retrieve_evidence_memory, finalize
        from langgraph_orchestration.state import new_state
        state = new_state(user_request='Flood damage insurance', requesting_user_id=self.user.pk, project_id=self.project.pk)
        state = retrieve_evidence_memory(state)
        self.assertEqual(state['evidence_context']['memories'][0]['citation']['quote'], self.memory.text_chunk)
        state['agent_outputs'] = [{'output_summary': 'Unsupported approval', 'agent_name': 'Test agent'}]
        state = finalize(state)
        self.assertEqual(state['status'], 'needs_human_review')
        self.assertEqual(state['final_recommendations'][0]['citation_ids'], [])
        self.assertEqual(state['final_recommendations'][0]['support_status'], 'insufficient_evidence')

    def test_expired_source_is_explicitly_labelled(self):
        from datetime import date
        citation = capture_citation(self.memory)
        self.memory.expiry_date = date(2000, 1, 1)
        self.memory.save()
        self.assertTrue(resolve_citation(citation, user=self.user, project=self.project)['expired'])
