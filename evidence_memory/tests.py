from django.test import TestCase

from evidence_memory.models import EMBEDDING_DIMENSIONS, EvidenceMemory
from evidence_memory.services import embeddings, memory


class EmbeddingServiceTests(TestCase):
    def test_returns_correct_dimensions(self):
        vector = embeddings.compute_embedding('district heating coal to gas transition')
        self.assertEqual(len(vector), EMBEDDING_DIMENSIONS)

    def test_deterministic_same_text_same_vector(self):
        text = 'quarterly emissions report scope 1 and scope 2'
        self.assertEqual(embeddings.compute_embedding(text), embeddings.compute_embedding(text))

    def test_blank_text_returns_none(self):
        self.assertIsNone(embeddings.compute_embedding(''))
        self.assertIsNone(embeddings.compute_embedding('   '))
        self.assertIsNone(embeddings.compute_embedding(None))

    def test_similar_texts_are_more_similar_than_unrelated(self):
        import numpy as np

        def cosine(a, b):
            a, b = np.asarray(a), np.asarray(b)
            return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

        a = embeddings.compute_embedding('Coal-fired district heating operator plans transition to gas')
        b = embeddings.compute_embedding('District heating company will transition from coal to natural gas')
        c = embeddings.compute_embedding('Quarterly stock market report shows tech sector gains')
        self.assertGreater(cosine(a, b), cosine(a, c))


class EvidenceMemoryModelTests(TestCase):
    def test_defaults_are_honest(self):
        m = EvidenceMemory.objects.create(text_chunk='Some real finding.')
        self.assertFalse(m.is_demo)  # never assume demo for a bare real entry
        self.assertEqual(m.embedding_status, 'pending')  # never assume embedded until computed
        self.assertIsNone(m.confidence)  # never fabricated

    def test_str_includes_source_type_and_preview(self):
        m = EvidenceMemory.objects.create(text_chunk='A' * 100, source_type='company_report')
        s = str(m)
        self.assertIn('Company Report', s)
        self.assertIn('…', s)


class CreateMemoryFromEvidenceTests(TestCase):
    def _make_evidence(self, **kwargs):
        from harvester.models import Evidence
        defaults = {
            'title': 'Test evidence', 'excerpt': 'Company reported 500 employees in 2025.',
            'company_slug': 'test-co', 'category': 'workforce',
        }
        defaults.update(kwargs)
        return Evidence.objects.create(**defaults)

    def test_creates_embedded_memory_from_real_evidence(self):
        evidence = self._make_evidence()
        m = memory.create_memory_from_evidence(evidence)
        self.assertEqual(m.source_type, 'harvester_evidence')
        self.assertEqual(m.source_reference, f'harvester.Evidence:{evidence.pk}')
        self.assertEqual(m.embedding_status, 'embedded')
        self.assertFalse(m.is_demo)  # real harvested evidence is never demo
        self.assertIn('500 employees', m.text_chunk)

    def test_idempotent_does_not_duplicate(self):
        evidence = self._make_evidence()
        m1 = memory.create_memory_from_evidence(evidence)
        m2 = memory.create_memory_from_evidence(evidence)
        self.assertEqual(m1.pk, m2.pk)
        self.assertEqual(EvidenceMemory.objects.filter(source_reference=f'harvester.Evidence:{evidence.pk}').count(), 1)

    def test_links_real_company_when_present(self):
        from companies.models import CompanyProfile
        from django.core.management import call_command
        call_command('seed_global_companies')
        profile = CompanyProfile.objects.first()
        evidence = self._make_evidence(company=profile)
        m = memory.create_memory_from_evidence(evidence)
        self.assertEqual(m.company_id, profile.pk)

    def test_falls_back_to_full_text_when_no_excerpt(self):
        evidence = self._make_evidence(excerpt='', full_text='The full document text goes here.')
        m = memory.create_memory_from_evidence(evidence)
        self.assertIn('full document text', m.text_chunk)


class CreateMemoryFromAgentRunTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command
        call_command('seed_agent_runtime_demo')

    def test_creates_memory_from_completed_run(self):
        from agent_runtime_model_router.services.execution import create_agent_run, execute_agent
        run = create_agent_run('Waste & Leakage Agent', 'test_task', execution_mode='deterministic_test')
        run = execute_agent(run)
        m = memory.create_memory_from_agent_run(run)
        self.assertEqual(m.source_type, 'agent_output')
        self.assertEqual(m.agent_name, 'Waste & Leakage Agent')
        self.assertEqual(m.source_reference, f'agent_runtime_model_router.AgentRun:{run.pk}')
        self.assertTrue(m.is_demo)  # deterministic_test runs are marked demo, never presented as real

    def test_idempotent_does_not_duplicate(self):
        from agent_runtime_model_router.services.execution import create_agent_run, execute_agent
        run = create_agent_run('Waste & Leakage Agent', 'test_task2', execution_mode='deterministic_test')
        run = execute_agent(run)
        m1 = memory.create_memory_from_agent_run(run)
        m2 = memory.create_memory_from_agent_run(run)
        self.assertEqual(m1.pk, m2.pk)


class SearchTests(TestCase):
    def setUp(self):
        self.heating_a = EvidenceMemory.objects.create(
            text_chunk='Coal-fired district heating operator plans transition to gas by 2030', source_type='other',
        )
        self.heating_b = EvidenceMemory.objects.create(
            text_chunk='District heating company will transition from coal to natural gas', source_type='other',
        )
        self.unrelated = EvidenceMemory.objects.create(
            text_chunk='Quarterly stock market report shows tech sector gains', source_type='other',
        )
        for m in (self.heating_a, self.heating_b, self.unrelated):
            m.embedding = embeddings.compute_embedding(m.text_chunk)
            m.embedding_status = 'embedded'
            m.save()

    def test_search_similar_ranks_related_text_first(self):
        results = memory.search_similar('coal to gas heating transition', top_k=3)
        result_ids = [r.pk for r in results]
        self.assertIn(self.heating_a.pk, result_ids[:2])
        self.assertIn(self.heating_b.pk, result_ids[:2])

    def test_never_returns_unembedded_rows(self):
        pending = EvidenceMemory.objects.create(text_chunk='not yet embedded', source_type='other')
        results = memory.search_similar('not yet embedded')
        self.assertNotIn(pending.pk, [r.pk for r in results])

    def test_blank_query_returns_empty(self):
        self.assertEqual(list(memory.search_similar('')), [])

    def test_search_company_memory_scopes_by_company(self):
        from companies.models import CompanyProfile
        from django.core.management import call_command
        call_command('seed_global_companies')
        profile = CompanyProfile.objects.first()
        other_profile = CompanyProfile.objects.exclude(pk=profile.pk).first()

        scoped = EvidenceMemory.objects.create(
            text_chunk='Coal-fired heating transition plan for this company', company=profile,
        )
        scoped.embedding = embeddings.compute_embedding(scoped.text_chunk)
        scoped.embedding_status = 'embedded'
        scoped.save()

        results = memory.search_company_memory(profile, 'heating transition')
        self.assertIn(scoped.pk, [r.pk for r in results])
        results_other = memory.search_company_memory(other_profile, 'heating transition')
        self.assertNotIn(scoped.pk, [r.pk for r in results_other])

    def test_search_country_memory_scopes_by_country(self):
        from django.core.management import call_command
        from countries.models import CountryProfile
        call_command('seed_countries')
        country = CountryProfile.objects.filter(name__icontains='Kazakh').first()
        self.assertIsNotNone(country)

        scoped = EvidenceMemory.objects.create(
            text_chunk='Coal-fired heating transition plan for this country', country=country,
        )
        scoped.embedding = embeddings.compute_embedding(scoped.text_chunk)
        scoped.embedding_status = 'embedded'
        scoped.save()

        results = memory.search_country_memory(country, 'heating transition')
        self.assertIn(scoped.pk, [r.pk for r in results])


class BackendIntelligenceEngineIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command
        call_command('seed_agent_runtime_demo')
        call_command('seed_global_companies')

    def test_run_ai_analysis_retrieves_and_saves_memory(self):
        from backend_intelligence_engine.tasks import run_ai_analysis
        from companies.models import CompanyProfile

        profile = CompanyProfile.objects.first()
        EvidenceMemory.objects.create(
            text_chunk='This company reported strong emissions reduction progress in its latest filing.',
            source_type='company_report', company=profile,
            embedding=embeddings.compute_embedding('This company reported strong emissions reduction progress in its latest filing.'),
            embedding_status='embedded',
        )

        result = run_ai_analysis.apply(
            args=['waste-leakage-agent'],
            kwargs={
                'execution_mode': 'deterministic_test', 'company_profile_id': profile.pk,
                'input_summary': 'What emissions progress has this company made?',
            },
        ).get()

        self.assertEqual(result['status'], 'completed')
        self.assertGreater(len(result['memories_retrieved']), 0)
        self.assertIsNotNone(result['memory_saved_id'])
        self.assertTrue(EvidenceMemory.objects.filter(pk=result['memory_saved_id']).exists())

    def test_refresh_evidence_memory_processes_company_evidence(self):
        from backend_intelligence_engine.tasks import refresh_evidence_memory
        from companies.models import CompanyProfile
        from harvester.models import Evidence

        profile = CompanyProfile.objects.first()
        Evidence.objects.create(
            title='Test', excerpt='Real evidence text for memory refresh.',
            company=profile, company_slug='test', category='other',
        )

        result = refresh_evidence_memory.apply(args=[profile.pk]).get()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['embedded'], 1)
        self.assertTrue(EvidenceMemory.objects.filter(company=profile, source_type='harvester_evidence').exists())

    def test_refresh_evidence_memory_respects_limit(self):
        from backend_intelligence_engine.tasks import refresh_evidence_memory
        from companies.models import CompanyProfile
        from harvester.models import Evidence

        profile = CompanyProfile.objects.first()
        for i in range(5):
            Evidence.objects.create(
                title=f'Test {i}', excerpt=f'Evidence chunk number {i}.',
                company=profile, company_slug='test', category='other',
            )

        result = refresh_evidence_memory.apply(args=[profile.pk], kwargs={'limit': 2}).get()
        self.assertEqual(result['evidence_processed'], 2)

    def test_refresh_evidence_memory_unknown_company_fails_honestly(self):
        from backend_intelligence_engine.tasks import refresh_evidence_memory
        result = refresh_evidence_memory.apply(args=[999999999]).get()
        self.assertEqual(result['status'], 'failed')


class AdminVisibilityTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.admin_user = User.objects.create_superuser('memadmin', 'mem@example.com', 'password123')
        self.client.force_login(self.admin_user)

    def test_memory_list_shows_source_confidence_and_embedding_status(self):
        EvidenceMemory.objects.create(
            text_chunk='Visible in admin test', source_type='manual', confidence=72.0, embedding_status='embedded',
        )
        response = self.client.get('/admin/evidence_memory/evidencememory/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Visible in admin test')
        self.assertContains(response, 'embedded')
