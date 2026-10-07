from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from evidence_memory.models import EvidenceMemory
from evidence_memory.services.embeddings import compute_embedding
from evidence_memory.services.memory import _cosine_similarity, _rank_candidates, _similarities_for


class StreamingRankingTests(TestCase):
    def setUp(self):
        for text in ('coal heating gas', 'coal heating gas', 'coal water', 'technology markets', 'wind energy'):
            EvidenceMemory.objects.create(text_chunk=text, embedding=compute_embedding(text), embedding_status='embedded')

    def test_streaming_ranking_equals_full_stable_sort_including_ties(self):
        candidates = EvidenceMemory.objects.order_by('pk')
        query = compute_embedding('coal heating gas')
        expected = sorted(candidates, key=lambda row: _cosine_similarity(row.embedding, query), reverse=True)
        for limit in (1, 2, 3, 5, 20):
            with self.subTest(limit=limit):
                result = _rank_candidates('coal heating gas', candidates, limit)
                self.assertEqual([row.pk for row in result], [row.pk for row in expected[:limit]])

    def test_ranking_does_not_populate_queryset_result_cache(self):
        filtered = EvidenceMemory.objects.order_by('pk')
        with patch.object(filtered, 'filter', return_value=filtered):
            self.assertEqual(len(_rank_candidates('coal', filtered, 2)), 2)
        self.assertIsNone(filtered._result_cache)

    def test_nonpositive_limit_avoids_embedding_and_database_work(self):
        with patch('evidence_memory.services.memory.compute_embedding') as embed, self.assertNumQueries(0):
            for limit in (0, -1):
                self.assertEqual(_rank_candidates('coal', EvidenceMemory.objects.all(), limit), [])
        embed.assert_not_called()

    def test_blank_query_avoids_candidate_read(self):
        with self.assertNumQueries(0):
            self.assertEqual(list(_rank_candidates(' ', EvidenceMemory.objects.all(), 3)), [])


class SimilarityReuseTests(SimpleTestCase):
    def test_postgres_annotations_need_no_second_query_embedding(self):
        rows = [SimpleNamespace(pk=1, distance=0.25), SimpleNamespace(pk=2, distance=0.0)]
        with patch('evidence_memory.services.memory.compute_embedding') as embed:
            self.assertEqual(_similarities_for('coal', rows), {1: .75, 2: 1.0})
        embed.assert_not_called()

    def test_mixed_rows_compute_embedding_once(self):
        query = [1.0, 0.0]
        rows = [SimpleNamespace(pk=1, distance=.5),
                SimpleNamespace(pk=2, embedding=[1.0, 0.0]),
                SimpleNamespace(pk=3, embedding=[0.0, 1.0]),
                SimpleNamespace(pk=4, embedding=None)]
        with patch('evidence_memory.services.memory.compute_embedding', return_value=query) as embed:
            self.assertEqual(_similarities_for('coal', rows), {1: .5, 2: 1.0, 3: 0.0})
        embed.assert_called_once_with('coal')

    def test_blank_query_never_reuses_an_unrelated_annotation(self):
        self.assertEqual(_similarities_for('', [SimpleNamespace(pk=1, distance=.2)]), {})
