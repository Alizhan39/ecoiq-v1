"""Opt-in real weights → index → Django search integration; no provider corpus.

ISLAMIC_NEURAL_LIVE_TEST=1 with the optional dependencies and prepared cache.
The fixture is authored generic text, not religious source or accuracy evaluation.
"""
import os
from unittest import skipUnless

from django.test import TestCase, override_settings

from .models import KnowledgePassage
from .neural import DIMENSIONS, MODEL_VERSION, index_passages
from .test_integration import PublicationFixtures, export
from .imports import import_export


@skipUnless(os.environ.get('ISLAMIC_NEURAL_LIVE_TEST') == '1', 'Opt-in pinned neural weights/dependencies required.')
@override_settings(ISLAMIC_NEURAL_SEARCH_ENABLED=True)
class LiveNeuralIntegrationTests(PublicationFixtures, TestCase):
    def test_real_encoder_index_and_multilingual_django_search(self):
        texts = [('en', 'Clean water and fair access.'),
                 ('ru', 'Чистая вода и справедливый доступ.'),
                 ('ar', 'مياه نظيفة وعدالة في الوصول.'),
                 ('kk', 'Таза су және әділетті қолжетімділік.')]
        for language, text in texts:
            import_export('azan_kz', export(external_id=f'live-fixture-{language}',
                language=language, passage=text, kind='ecoiq_operationalisation'))
        for row in KnowledgePassage.objects.all():
            self.publish(row)
        self.assertEqual(index_passages(), len(texts))
        self.assertEqual(index_passages(), 0)
        for row in KnowledgePassage.objects.all():
            self.assertEqual(len(row.embedding), DIMENSIONS)
            self.assertEqual(row.embedding_model, MODEL_VERSION)
        for _, query in texts:
            response = self.client.get('/api/islamic/search/', {'q': query, 'limit': len(texts)})
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body['method'], 'neural_cosine')
            self.assertEqual(len(body['results']), len(texts))
            self.assertTrue(all(row['source_url'] and row['source_digest'] for row in body['results']))
            self.assertFalse(body['similarity_is_confidence'])

    def test_real_encoder_hybrid_fusion_retains_exact_citations(self):
        texts = [('en', 'Clean water and fair access.'),
                 ('ru', 'Чистая вода и справедливый доступ.'),
                 ('ar', 'مياه نظيفة وعدالة في الوصول.'),
                 ('kk', 'Таза су және әділетті қолжетімділік.')]
        for language, text in texts:
            import_export('azan_kz', export(external_id=f'hybrid-live-{language}',
                language=language, passage=text, kind='ecoiq_operationalisation'))
        for row in KnowledgePassage.objects.all():
            self.publish(row)
        self.assertEqual(index_passages(), len(texts))
        for language, query in texts:
            response = self.client.get('/api/islamic/search/', {
                'q': query, 'mode': 'hybrid', 'limit': len(texts)})
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body['method'], 'hybrid_rrf')
            self.assertEqual(body['neural_status'], 'used')
            self.assertEqual(body['model'], MODEL_VERSION)
            self.assertEqual(len(body['results']), len(texts))
            same_language = next(hit for hit in body['results'] if hit['language'] == language)
            self.assertEqual(same_language['passage'], query)
            self.assertEqual(same_language['matched_by'], ['lexical', 'neural'])
            self.assertTrue(all(hit['source_url'] and hit['source_digest'] for hit in body['results']))
            self.assertFalse(body['score_is_confidence'])
