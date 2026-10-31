"""Synthetic retrieval regressions, not evaluation of religious accuracy."""
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from .imports import import_export
from .models import KnowledgePassage
from .neural import MODEL_VERSION, NeuralUnavailable
from .retrieval import RetrievalUnavailable, hybrid_search, lexical_search, tokens
from .test_integration import PublicationFixtures, export, unit


@override_settings(ISLAMIC_NEURAL_SEARCH_ENABLED=False)
class HybridRetrievalTests(PublicationFixtures, TestCase):
    def source(self, external_id, passage, *, provider='azan_kz', publish=True, indexed=False, **changes):
        import_export(provider, export(provider, external_id, passage=passage, **changes))
        row = KnowledgePassage.objects.get(provider=provider, external_id=external_id)
        if publish:
            self.publish(row)
        if indexed:
            KnowledgePassage.objects.filter(pk=row.pk).update(embedding=unit(0),
                embedding_model=MODEL_VERSION, embedding_digest=row.digest)
            row.refresh_from_db()
        return row

    def test_unicode_words_support_ru_kk_ar_en_without_substring_matches(self):
        self.assertEqual(tokens('ҚАЗАҚ Әділеттілік'), {'қазақ', 'әділеттілік'})
        self.assertEqual(tokens('عَدْل'), tokens('عدل'))
        for text, query in [('Чистая вода', 'ВОДА'), ('Таза су', 'су'),
                            ('عَدْل ومياه', 'عدل'), ('Clean water', 'WATER')]:
            with self.subTest(query=query):
                row = self.source(query, text)
                self.assertEqual(lexical_search(query)[0][1].pk, row.pk)
        self.assertEqual(lexical_search('wat'), [])

    def test_disabled_encoder_keeps_cited_lexical_results_and_strict_api(self):
        row = self.source('water', 'Clean water and fair access.')
        with patch('islamic_knowledge.retrieval.semantic_search') as neural:
            response = self.client.get('/api/islamic/search/', {'q': 'water', 'mode': 'hybrid'})
        neural.assert_not_called()
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body['method'], 'lexical_overlap')
        self.assertEqual(body['neural_status'], 'disabled')
        self.assertIsNone(body['model'])
        self.assertFalse(body['score_is_confidence'])
        hit = body['results'][0]
        self.assertEqual(hit['source_digest'], row.digest)
        self.assertEqual(hit['source_url'], row.source_url)
        self.assertEqual(hit['matched_by'], ['lexical'])
        self.assertIsNone(hit['similarity'])
        self.assertFalse(hit['religious_ruling'])
        self.assertEqual(self.client.get('/api/islamic/search/', {'q': 'water'}).status_code, 503)

    @override_settings(ISLAMIC_NEURAL_SEARCH_ENABLED=True)
    def test_unavailable_weights_return_explicit_lexical_fallback(self):
        self.source('water', 'Clean water.')
        with patch('islamic_knowledge.retrieval.semantic_search', side_effect=NeuralUnavailable('fixture')):
            body = self.client.get('/api/islamic/search/', {'q': 'water', 'mode': 'hybrid'}).json()
        self.assertEqual(body['neural_status'], 'unavailable')
        self.assertEqual(body['method'], 'lexical_overlap')
        self.assertEqual(len(body['results']), 1)

    @override_settings(ISLAMIC_NEURAL_SEARCH_ENABLED=True)
    def test_fusion_prefers_dual_match_deduplicates_and_keeps_neural_only_match(self):
        lexical = self.source('a', 'Clean water.')
        both = self.source('b', 'Clean water.', indexed=True)
        neural = self.source('c', 'Чистая вода.', indexed=True)
        with patch('islamic_knowledge.retrieval.semantic_search', return_value=[(0.99, neural), (0.9, both)]):
            result = hybrid_search('water', limit=3)
        self.assertEqual(result.method, 'hybrid_rrf')
        self.assertEqual([hit.row.pk for hit in result.results], [both.pk, lexical.pk, neural.pk])
        self.assertEqual(result.results[0].matched_by, ['lexical', 'neural'])
        self.assertAlmostEqual(result.results[0].fusion_score, 2 / 62)
        self.assertEqual(result.results[0].similarity, 0.9)
        self.assertEqual(result.results[2].matched_by, ['neural'])

    @override_settings(ISLAMIC_NEURAL_SEARCH_ENABLED=True)
    def test_actual_semantic_service_is_used_and_response_retains_model(self):
        self.source('a', 'Clean water.', indexed=True)
        with patch('islamic_knowledge.neural.encode', return_value=[unit(0)]) as encoder:
            body = self.client.get('/api/islamic/search/', {'q': 'water', 'mode': 'hybrid'}).json()
        encoder.assert_called_once_with(['water'])
        self.assertEqual(body['method'], 'hybrid_rrf')
        self.assertEqual(body['model'], MODEL_VERSION)
        self.assertEqual(body['neural_status'], 'used')

    def test_provider_language_filters_and_stable_ties(self):
        self.source('b', 'Таза су', language='kk')
        first = self.source('a', 'Таза су', language='kk')
        self.source('other-provider', 'Таза су', language='kk', provider='sajda')
        self.source('other-language', 'Таза су', language='ru')
        result = hybrid_search('су', provider='azan_kz', language='kk', limit=1)
        self.assertEqual([hit.row.pk for hit in result.results], [first.pk])

    def test_pending_rights_unreviewed_stale_and_revoked_sources_are_hidden(self):
        self.source('unreviewed', 'Clean water', publish=False)
        self.source('pending', 'Clean water', rights='permission_pending', rights_evidence='')
        revoked = self.source('revoked', 'Clean water')
        KnowledgePassage.objects.filter(pk=revoked.pk).update(revoked=True)
        stale = self.source('stale', 'Clean water')
        stale.passage = 'Water after edit'
        stale.save()
        self.assertEqual(hybrid_search('water').results, [])

    @override_settings(ISLAMIC_NEURAL_SEARCH_ENABLED=True)
    def test_withdrawal_during_fusion_hides_old_cursor(self):
        row = self.source('a', 'Clean water', indexed=True)

        def withdraw(*args, **kwargs):
            KnowledgePassage.objects.filter(pk=row.pk).update(revoked=True)
            return [(1.0, row)]

        with patch('islamic_knowledge.retrieval.semantic_search', side_effect=withdraw):
            self.assertEqual(hybrid_search('water').results, [])

    @override_settings(ISLAMIC_NEURAL_SEARCH_ENABLED=True)
    def test_changed_source_is_not_returned_from_either_ranking(self):
        row = self.source('a', 'Clean water', indexed=True)

        def edit(*args, **kwargs):
            changed = KnowledgePassage.objects.get(pk=row.pk)
            changed.passage = 'Edited water'
            changed.save()
            self.publish(changed)
            return [(1.0, row)]

        with patch('islamic_knowledge.retrieval.semantic_search', side_effect=edit):
            self.assertEqual(hybrid_search('water').results, [])

    @override_settings(ISLAMIC_NEURAL_SEARCH_ENABLED=True)
    def test_stale_embedding_loses_neural_contribution_but_keeps_lexical_match(self):
        row = self.source('a', 'Clean water', indexed=True)

        def invalidate(*args, **kwargs):
            KnowledgePassage.objects.filter(pk=row.pk).update(embedding_model='old-model')
            return [(1.0, row)]

        with patch('islamic_knowledge.retrieval.semantic_search', side_effect=invalidate):
            result = hybrid_search('water')
        self.assertEqual(result.results[0].matched_by, ['lexical'])
        self.assertAlmostEqual(result.results[0].fusion_score, 1 / 61)
        self.assertEqual(result.method, 'lexical_overlap')

    def test_no_index_or_no_match_is_an_empty_result_not_invented_content(self):
        self.source('a', 'Clean water')
        with override_settings(ISLAMIC_NEURAL_SEARCH_ENABLED=True):
            result = hybrid_search('unrelated')
        self.assertEqual(result.results, [])
        self.assertEqual(result.neural_status, 'no_results')

    def test_oversized_corpus_is_not_silently_truncated(self):
        self.source('a', 'Clean water')
        with patch('islamic_knowledge.retrieval.MAX_LEXICAL_PASSAGES', 0):
            with self.assertRaises(RetrievalUnavailable):
                hybrid_search('water')
            self.assertEqual(self.client.get('/api/islamic/search/', {
                'q': 'water', 'mode': 'hybrid'}).status_code, 503)

    def test_query_validation_happens_before_scans_or_encoder_calls(self):
        for query in ('', ' ', 'x' * 1001, '!!!', ' '.join(f'word{i}' for i in range(33))):
            with self.subTest(query=query), self.assertNumQueries(0), self.assertRaises(ValueError):
                hybrid_search(query)
        for limit in (0, 21, True, '5'):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                hybrid_search('water', limit=limit)
        for params in ({'mode': 'unknown'}, {'mode': 'hybrid', 'provider': 'unknown'},
                       {'mode': 'hybrid', 'language': '../../'}, {'mode': 'hybrid', 'limit': 'bad'}):
            cache.clear()
            self.assertEqual(self.client.get('/api/islamic/search/', {'q': 'water', **params}).status_code, 400)

    def test_hybrid_and_neural_share_the_same_throttle_and_reject_writes(self):
        for i in range(5):
            self.client.get('/api/islamic/search/', {'q': 'water', 'mode': 'hybrid' if i % 2 else 'neural'})
        self.assertEqual(self.client.get('/api/islamic/search/', {'q': 'water', 'mode': 'hybrid'}).status_code, 429)
        self.assertEqual(self.client.post('/api/islamic/search/', {}).status_code, 405)
