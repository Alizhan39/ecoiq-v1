from unittest import mock

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


class HarvesterSyncCharacterizationTests(TestCase):
    """
    Phase 1A, Task 1 — locks in the CURRENT behaviour of
    create_memory_from_evidence() before Tasks 2/3 extend the same service
    layer to hikma.Evidence and league.Evidence. Every assertion here
    describes what the sync already does today; none of it is new behaviour.
    """

    def _make_evidence(self, **kwargs):
        from harvester.models import Evidence
        defaults = {
            'title': 'Characterization evidence', 'excerpt': 'Reported 42 tonnes CO2 reduction.',
            'company_slug': 'char-co', 'category': 'emissions',
        }
        defaults.update(kwargs)
        return Evidence.objects.create(**defaults)

    def test_source_reference_and_source_type(self):
        evidence = self._make_evidence()
        m = memory.create_memory_from_evidence(evidence)
        self.assertEqual(m.source_reference, f'harvester.Evidence:{evidence.pk}')
        self.assertEqual(m.source_type, 'harvester_evidence')

    def test_verification_workflow_fields_are_untouched_defaults(self):
        """
        The harvester sync has never set verification_status/review_tier/
        document_category — they stay at the model's own defaults. This is
        the baseline Tasks 2/3 must not silently change for harvester-sourced
        memories.
        """
        evidence = self._make_evidence()
        m = memory.create_memory_from_evidence(evidence)
        self.assertEqual(m.verification_status, 'pending')
        self.assertEqual(m.review_tier, 'uploaded')
        self.assertEqual(m.document_category, 'other')

    def test_integrity_reference_is_sha256_of_text_chunk(self):
        import hashlib
        evidence = self._make_evidence()
        m = memory.create_memory_from_evidence(evidence)
        expected = hashlib.sha256(m.text_chunk.encode('utf-8')).hexdigest()
        self.assertEqual(m.integrity_reference, expected)
        self.assertEqual(len(m.integrity_reference), 64)

    def test_embedding_populated_with_correct_dimensions(self):
        from evidence_memory.models import EMBEDDING_DIMENSIONS
        evidence = self._make_evidence()
        m = memory.create_memory_from_evidence(evidence)
        self.assertEqual(m.embedding_status, 'embedded')
        self.assertEqual(len(m.embedding), EMBEDDING_DIMENSIONS)

    def test_idempotent_same_pk_no_duplicate_row(self):
        evidence = self._make_evidence()
        m1 = memory.create_memory_from_evidence(evidence)
        m2 = memory.create_memory_from_evidence(evidence)
        m3 = memory.create_memory_from_evidence(evidence)
        self.assertEqual(m1.pk, m2.pk)
        self.assertEqual(m2.pk, m3.pk)
        self.assertEqual(
            EvidenceMemory.objects.filter(source_reference=f'harvester.Evidence:{evidence.pk}').count(), 1,
        )

    def test_resync_updates_text_chunk_in_place(self):
        """Re-running the sync after the underlying Evidence changes updates the
        existing memory row rather than leaving stale text or creating a second row."""
        evidence = self._make_evidence(excerpt='Original excerpt text.')
        m1 = memory.create_memory_from_evidence(evidence)
        self.assertIn('Original excerpt', m1.text_chunk)

        evidence.excerpt = 'Updated excerpt text after re-harvest.'
        evidence.save(update_fields=['excerpt'])
        m2 = memory.create_memory_from_evidence(evidence)

        self.assertEqual(m1.pk, m2.pk)
        self.assertIn('Updated excerpt', m2.text_chunk)
        self.assertEqual(EvidenceMemory.objects.filter(source_reference=f'harvester.Evidence:{evidence.pk}').count(), 1)

    def test_two_different_evidence_rows_never_collide(self):
        e1 = self._make_evidence(company_slug='co-a')
        e2 = self._make_evidence(company_slug='co-b')
        m1 = memory.create_memory_from_evidence(e1)
        m2 = memory.create_memory_from_evidence(e2)
        self.assertNotEqual(m1.pk, m2.pk)
        self.assertNotEqual(m1.source_reference, m2.source_reference)

    def test_embedding_failure_is_contained_not_propagated(self):
        """
        If embedding computation raises, the sync must still save the memory
        row (marked embedding_status='failed') rather than losing the write
        or propagating the exception up into the caller's ingestion pipeline.
        """
        evidence = self._make_evidence()
        with mock.patch('evidence_memory.services.memory.compute_embedding', side_effect=RuntimeError('boom')):
            m = memory.create_memory_from_evidence(evidence)
        self.assertEqual(m.embedding_status, 'failed')
        self.assertTrue(EvidenceMemory.objects.filter(pk=m.pk).exists())

    def test_blank_excerpt_and_full_text_falls_back_to_title(self):
        evidence = self._make_evidence(excerpt='', full_text='', title='Title-only evidence record')
        m = memory.create_memory_from_evidence(evidence)
        self.assertEqual(m.text_chunk, 'Title-only evidence record')

    def test_is_demo_always_false_for_harvester_sourced_memory(self):
        evidence = self._make_evidence()
        m = memory.create_memory_from_evidence(evidence)
        self.assertFalse(m.is_demo)


class CreateMemoryFromHikmaEvidenceTests(TestCase):
    """Phase 1A, Task 2 — hikma.Evidence -> EvidenceMemory."""

    def _make_hikma_evidence(self, **kwargs):
        from hikma.models import Evidence
        from companies.models import CompanyProfile
        from django.core.management import call_command
        call_command('seed_global_companies')
        profile = CompanyProfile.objects.first()
        defaults = {
            'company': profile, 'subject_type': 'company', 'subject_ref': profile.company.slug,
            'kind': 'say', 'statement': 'Stated a 40% emissions-reduction target by 2030.',
            'confidence_tier': 'analyst-reviewed', 'confidence_score': 0.8,
            'scholar_review_required': True,
        }
        defaults.update(kwargs)
        return Evidence.objects.create(**defaults)

    def test_source_reference_and_source_type(self):
        evidence = self._make_hikma_evidence()
        m = memory.create_memory_from_hikma_evidence(evidence)
        self.assertEqual(m.source_reference, f'hikma.Evidence:{evidence.pk}')
        self.assertEqual(m.source_type, 'company_report')

    def test_non_company_subject_uses_other_source_type(self):
        evidence = self._make_hikma_evidence(subject_type='country', subject_ref='KZ')
        m = memory.create_memory_from_hikma_evidence(evidence)
        self.assertEqual(m.source_type, 'other')

    def test_text_chunk_is_the_statement(self):
        evidence = self._make_hikma_evidence(statement='A specific SAY statement.')
        m = memory.create_memory_from_hikma_evidence(evidence)
        self.assertEqual(m.text_chunk, 'A specific SAY statement.')

    def test_company_link_preserved(self):
        evidence = self._make_hikma_evidence()
        m = memory.create_memory_from_hikma_evidence(evidence)
        self.assertEqual(m.company_id, evidence.company_id)

    def test_confidence_carried_from_confidence_score(self):
        evidence = self._make_hikma_evidence(confidence_score=0.73)
        m = memory.create_memory_from_hikma_evidence(evidence)
        self.assertEqual(m.confidence, 0.73)

    def test_scholar_review_required_forces_requires_review(self):
        evidence = self._make_hikma_evidence(confidence_tier='verified', scholar_review_required=True)
        m = memory.create_memory_from_hikma_evidence(evidence)
        self.assertEqual(m.verification_status, 'requires_review')
        self.assertEqual(m.review_tier, 'independently_verified')

    def test_reviewed_and_cleared_flag_yields_verified(self):
        evidence = self._make_hikma_evidence(confidence_tier='analyst-reviewed', scholar_review_required=False)
        m = memory.create_memory_from_hikma_evidence(evidence)
        self.assertEqual(m.verification_status, 'verified')
        self.assertEqual(m.review_tier, 'human_reviewed')

    def test_ai_seeded_and_cleared_flag_yields_pending(self):
        evidence = self._make_hikma_evidence(confidence_tier='ai-seeded', scholar_review_required=False)
        m = memory.create_memory_from_hikma_evidence(evidence)
        self.assertEqual(m.verification_status, 'pending')
        self.assertEqual(m.review_tier, 'system_checked')

    def test_is_demo_always_false(self):
        evidence = self._make_hikma_evidence()
        m = memory.create_memory_from_hikma_evidence(evidence)
        self.assertFalse(m.is_demo)

    def test_idempotent_no_duplicate(self):
        evidence = self._make_hikma_evidence()
        m1 = memory.create_memory_from_hikma_evidence(evidence)
        m2 = memory.create_memory_from_hikma_evidence(evidence)
        self.assertEqual(m1.pk, m2.pk)
        self.assertEqual(
            EvidenceMemory.objects.filter(source_reference=f'hikma.Evidence:{evidence.pk}').count(), 1,
        )

    def test_embedded_and_hikma_evidence_still_a_separate_store(self):
        """hikma.Evidence itself is untouched by the sync — it's not consumed/deleted."""
        from hikma.models import Evidence
        evidence = self._make_hikma_evidence()
        memory.create_memory_from_hikma_evidence(evidence)
        self.assertTrue(Evidence.objects.filter(pk=evidence.pk).exists())

    def test_wired_into_real_ingest_pipeline(self):
        from hikma.ingest import ingest_for_profile
        from hikma.models import Evidence as HikmaEvidence
        from companies.models import CompanyProfile
        from django.core.management import call_command
        call_command('seed_global_companies')
        profile = CompanyProfile.objects.exclude(ai_summary='').first()
        self.assertIsNotNone(profile)

        result = ingest_for_profile(profile)
        self.assertGreater(result['created'], 0)

        created_refs = {
            f'hikma.Evidence:{ev.pk}' for ev in HikmaEvidence.objects.filter(company=profile)
        }
        synced_refs = set(
            EvidenceMemory.objects.filter(source_reference__in=created_refs).values_list('source_reference', flat=True)
        )
        self.assertEqual(created_refs, synced_refs)


class CreateMemoryFromLeagueEvidenceTests(TestCase):
    """Phase 1A, Task 3 — league.Evidence -> EvidenceMemory."""

    def _make_league_evidence(self, **kwargs):
        from league.models import Company, Evidence
        company = Company.objects.create(name='Char League Corp', sector='oil_gas')
        defaults = {
            'company': company, 'doc_type': 'permit', 'title': 'Environmental Permit 2026',
            'url': 'https://example.com/permit.pdf', 'verification_status': 'pending',
            'notes': 'Real permit document verifying project compliance.',
        }
        defaults.update(kwargs)
        return Evidence.objects.create(**defaults)

    def test_source_reference_and_source_type(self):
        evidence = self._make_league_evidence()
        m = memory.create_memory_from_league_evidence(evidence)
        self.assertEqual(m.source_reference, f'league.Evidence:{evidence.pk}')
        self.assertEqual(m.source_type, 'company_report')

    def test_text_chunk_prefers_notes_falls_back_to_title(self):
        evidence = self._make_league_evidence(notes='', title='Fallback title used here')
        m = memory.create_memory_from_league_evidence(evidence)
        self.assertEqual(m.text_chunk, 'Fallback title used here')

    def test_no_cross_app_company_fk_is_set(self):
        """
        league.Company and companies.CompanyProfile are different models —
        memory.company must stay None rather than pointing at the wrong table's
        row via a coincidentally-matching pk.
        """
        evidence = self._make_league_evidence()
        m = memory.create_memory_from_league_evidence(evidence)
        self.assertIsNone(m.company)

    def test_verification_status_propagated_verified(self):
        evidence = self._make_league_evidence(verification_status='verified')
        m = memory.create_memory_from_league_evidence(evidence)
        self.assertEqual(m.verification_status, 'verified')
        self.assertEqual(m.review_tier, 'human_reviewed')

    def test_verification_status_propagated_rejected(self):
        evidence = self._make_league_evidence(verification_status='rejected')
        m = memory.create_memory_from_league_evidence(evidence)
        self.assertEqual(m.verification_status, 'rejected')
        self.assertEqual(m.review_tier, 'uploaded')

    def test_is_demo_always_false(self):
        evidence = self._make_league_evidence()
        m = memory.create_memory_from_league_evidence(evidence)
        self.assertFalse(m.is_demo)

    def test_idempotent_no_duplicate(self):
        evidence = self._make_league_evidence()
        m1 = memory.create_memory_from_league_evidence(evidence)
        m2 = memory.create_memory_from_league_evidence(evidence)
        self.assertEqual(m1.pk, m2.pk)
        self.assertEqual(
            EvidenceMemory.objects.filter(source_reference=f'league.Evidence:{evidence.pk}').count(), 1,
        )

    def test_wired_into_audit_ai_engine_apply_approved_findings(self):
        from audit.ai_engine import apply_approved_findings
        from audit.models import AIAnalysisJob
        from league.models import Company, Evidence as LeagueEvidence
        from django.utils import timezone

        company = Company.objects.create(name='Audit Sync Corp', sector='mining')
        job = AIAnalysisJob.objects.create(
            company=company, original_filename='report.pdf', status='completed',
            model_used='test-model', pages_analyzed=3, input_tokens=100, output_tokens=50,
            executive_summary='Summary of findings.', completed_at=timezone.now(),
        )
        apply_approved_findings(job, company)

        evidence = LeagueEvidence.objects.filter(company=company).first()
        self.assertIsNotNone(evidence)
        self.assertTrue(
            EvidenceMemory.objects.filter(source_reference=f'league.Evidence:{evidence.pk}').exists()
        )

    def test_wired_into_ingestion_pipeline_project_and_report_evidence(self):
        from ingestion.pipeline import IngestionPipeline
        from ingestion.models import IngestionJob
        from league.models import Evidence as LeagueEvidence

        job = IngestionJob.objects.create(company_name='Pipeline Sync Corp')
        pipeline = IngestionPipeline(job.pk)
        pipeline._search_data = {'canonical_name': 'Pipeline Sync Corp', 'sector': 'energy'}
        pipeline._extraction = {
            'projects': [{'name': 'Sync Project', 'source_url': 'https://example.com/project-source'}],
        }
        pipeline._scores = {
            'pollution_footprint': 60, 'reduction_progress': 55, 'investment': 50,
            'transparency': 65, 'community_impact': 70, 'ecoiq_score': 58.2, 'reasoning': {},
        }
        pipeline._sources = [
            {'url': 'https://example.com/report.pdf', 'downloaded': True, 'source_type': 'esg_report',
             'title': 'ESG Report', 'snippet': 'Snippet text.'},
        ]
        pipeline._step_save()

        refs = list(LeagueEvidence.objects.filter(company__name='Pipeline Sync Corp').values_list('pk', flat=True))
        self.assertEqual(len(refs), 2)
        for pk in refs:
            self.assertTrue(EvidenceMemory.objects.filter(source_reference=f'league.Evidence:{pk}').exists())


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
