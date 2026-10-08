"""Provider/export, editorial publication and neural plumbing regressions.

Synthetic texts/vectors test contracts, never theological or model accuracy.
"""
from heapq import nlargest
from io import StringIO
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from .admin import KnowledgePassageAdmin
from .imports import import_export
from .models import KnowledgePassage
from .neural import DIMENSIONS, MODEL_REVISION, MODEL_VERSION, NeuralUnavailable, encode, index_passages, load_encoder, semantic_search
from .providers import ProviderUnavailable, fetch_feed, provider_catalog, validate_source_url


def export(provider='azan_kz', external_id='fixture-1', **changes):
    row = {'external_id': external_id,
           'source_url': 'https://azan.kz/durus/dars/99-imyon-Allaha-97' if provider == 'azan_kz' else 'https://sajda.com/en',
           'kind': 'tafsir', 'work': 'Synthetic test work', 'edition': 'test-only',
           'source_version': 'fixture-v1', 'language': 'ru', 'attribution': 'Test fixture author',
           'passage': 'Synthetic source fixture, not Quran or religious instruction.',
           'rights': 'licensed', 'rights_evidence': 'Synthetic test permission record'}
    row.update(changes)
    return {'schema_version': 1, 'provider': provider, 'passages': [row]}


def unit(axis):
    return [1.0 if i == axis else 0.0 for i in range(DIMENSIONS)]


class ProviderTests(SimpleTestCase):
    def test_unconfigured_provider_does_not_make_network_request(self):
        with override_settings(ISLAMIC_KNOWLEDGE_FEEDS={}), patch('islamic_knowledge.providers.requests.get') as get:
            with self.assertRaises(ProviderUnavailable):
                fetch_feed('sajda')
        get.assert_not_called()
        self.assertTrue(all(not row['public_content_api_verified'] for row in provider_catalog()))

    def test_source_urls_reject_other_hosts_credentials_ports_and_http(self):
        for url in ('http://azan.kz/x', 'https://evil.example/x', 'https://azan.kz.evil.example/x',
                    'https://user:secret@azan.kz/x', 'https://azan.kz:8443/x', 'https://sajda.com/x'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_source_url('azan_kz', url)
        self.assertEqual(validate_source_url('azan_kz', 'https://azan.kz/x'), 'https://azan.kz/x')

    @override_settings(ISLAMIC_KNOWLEDGE_FEEDS={'azan_kz': 'https://azan.kz/agreed-feed.json'})
    def test_feed_is_bounded_json_and_does_not_follow_redirects(self):
        response = Mock(status_code=200, headers={'Content-Type': 'application/json'})
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.iter_content.return_value = [json.dumps(export()).encode()]
        with patch('islamic_knowledge.providers.requests.get', return_value=response) as get:
            self.assertEqual(fetch_feed('azan_kz'), export())
        self.assertFalse(get.call_args.kwargs['allow_redirects'])
        response.iter_content.return_value = [b'12345']
        with patch('islamic_knowledge.providers.requests.get', return_value=response), patch('islamic_knowledge.providers.MAX_FEED_BYTES', 4):
            with self.assertRaises(ProviderUnavailable):
                fetch_feed('azan_kz')
        for status, content_type in ((302, 'application/json'), (200, 'text/html')):
            response.status_code = status
            response.headers['Content-Type'] = content_type
            with patch('islamic_knowledge.providers.requests.get', return_value=response), self.assertRaises(ProviderUnavailable):
                fetch_feed('azan_kz')


class PublicationFixtures:
    def setUp(self):
        cache.clear()
        self.reviewer = get_user_model().objects.create_user('source-reviewer', is_staff=True)

    def publish(self, row):
        KnowledgePassage.objects.filter(pk=row.pk).update(reviewed_digest=row.digest,
            reviewed_by=self.reviewer, reviewed_at=timezone.now())
        row.refresh_from_db()


class ImportPublicationTests(PublicationFixtures, TestCase):
    def test_import_is_idempotent_and_cannot_import_review_or_vectors(self):
        self.assertEqual(import_export('azan_kz', export()), {'created': 1, 'updated': 0, 'unchanged': 0})
        row = KnowledgePassage.objects.get()
        self.publish(row)
        self.assertEqual(import_export('azan_kz', export())['unchanged'], 1)
        self.assertEqual(KnowledgePassage.published().count(), 1)
        for key in ('reviewed_digest', 'embedding', 'revoked'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                import_export('azan_kz', export(**{key: 'untrusted'}))

    def test_changed_source_invalidates_review_and_embedding(self):
        import_export('azan_kz', export())
        row = KnowledgePassage.objects.get()
        self.publish(row)
        KnowledgePassage.objects.filter(pk=row.pk).update(embedding=unit(0), embedding_model=MODEL_VERSION, embedding_digest=row.digest)
        self.assertEqual(import_export('azan_kz', export(source_version='fixture-v2'))['updated'], 1)
        row.refresh_from_db()
        self.assertEqual(row.reviewed_digest, '')
        self.assertEqual(row.embedding, [])
        self.assertFalse(KnowledgePassage.published().exists())

    def test_validation_failure_writes_nothing(self):
        data = export()
        data['passages'].append({**data['passages'][0], 'external_id': 'invalid', 'source_url': 'https://evil.example/'})
        with self.assertRaises(ValidationError):
            import_export('azan_kz', data)
        self.assertEqual(KnowledgePassage.objects.count(), 0)

    def test_schema_provider_duplicates_and_reference_types_are_checked(self):
        for data in ({**export(), 'provider': 'sajda'}, {**export(), 'schema_version': 2},
                     {**export(), 'passages': []}, export(surah=True, ayah_start=1)):
            with self.subTest(data=data), self.assertRaises(ValueError):
                import_export('azan_kz', data)
        duplicate = export()
        duplicate['passages'] *= 2
        with self.assertRaises(ValueError):
            import_export('azan_kz', duplicate)

    def test_quran_locator_and_provider_enumeration_are_required(self):
        for changes in ({'kind': 'quran_text'}, {'kind': 'translation', 'surah': 114, 'ayah_start': 7},
                        {'name_key': 'ar-rahman'}, {'name_key': 'invented', 'enumeration': 'provider-v1'},
                        {'kind': 'ai_inference'}, {'rights_evidence': ''}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                import_export('azan_kz', export(**changes))
        import_export('sajda', export('sajda', name_key='ar-rahman', enumeration='explicit-sajda-variant'))
        self.assertEqual(KnowledgePassage.objects.get().enumeration, 'explicit-sajda-variant')

    def test_source_edit_and_partial_save_cannot_keep_approval(self):
        import_export('azan_kz', export())
        row = KnowledgePassage.objects.get()
        self.publish(row)
        row.attribution = 'Changed fixture attribution'
        with self.assertRaises(ValueError):
            row.save(update_fields=['attribution'])
        row.save()
        self.assertIsNone(row.reviewed_by)
        self.assertFalse(KnowledgePassage.published().exists())

    def test_api_catalogs_report_reference_origin_and_pending_provider_access(self):
        surah_response = self.client.get('/api/islamic/surahs/').json()
        names_response = self.client.get('/api/islamic/names/').json()
        self.assertEqual(len(surah_response['results']), 114)
        self.assertEqual(len(names_response['results']), 99)
        self.assertFalse(names_response['authoritative'])
        self.assertEqual({row['review_status'] for row in names_response['results']}, {'scholar_review_pending'})
        self.assertEqual(len(self.client.get('/api/islamic/sources/').json()['providers']), 2)
        self.assertEqual(self.client.post('/api/islamic/passages/', data={}).status_code, 405)

    def test_public_api_hides_unreviewed_pending_rights_and_revoked_content(self):
        import_export('azan_kz', export())
        row = KnowledgePassage.objects.get()
        self.assertEqual(self.client.get('/api/islamic/passages/').json()['results'], [])
        self.publish(row)
        result = self.client.get('/api/islamic/passages/').json()['results'][0]
        self.assertEqual(result['source_digest'], row.digest)
        self.assertFalse(result['religious_ruling'])
        row.revoked = True
        row.save()
        self.assertEqual(self.client.get('/api/islamic/passages/').json()['results'], [])
        row.revoked = False
        row.rights = 'permission_pending'
        row.save()
        self.publish(row)
        self.assertEqual(self.client.get('/api/islamic/passages/').json()['results'], [])

    def test_api_filters_and_pagination_validate_inputs(self):
        for query in ('provider=unknown', 'limit=0', 'offset=-1', 'surah=115', 'name=unknown', 'language=../../'):
            with self.subTest(query=query):
                self.assertEqual(self.client.get('/api/islamic/passages/?' + query).status_code, 400)
        for i in range(3):
            import_export('azan_kz', export(external_id=f'fixture-{i}'))
        for row in KnowledgePassage.objects.all():
            self.publish(row)
        first = self.client.get('/api/islamic/passages/?limit=2').json()
        second = self.client.get('/api/islamic/passages/?limit=2&offset=2').json()
        self.assertEqual(len(first['results']), 2)
        self.assertEqual(first['next_offset'], 2)
        self.assertEqual(len(second['results']), 1)
        self.assertIsNone(second['next_offset'])

    def test_admin_review_respects_rights_and_withdrawal(self):
        import_export('azan_kz', export())
        import_export('azan_kz', export(external_id='pending', rights='permission_pending', rights_evidence=''))
        model_admin = KnowledgePassageAdmin(KnowledgePassage, AdminSite())
        request = SimpleNamespace(user=self.reviewer)
        with patch.object(model_admin, 'message_user'):
            model_admin.publish_reviewed(request, KnowledgePassage.objects.all())
            self.assertEqual(KnowledgePassage.published().count(), 1)
            model_admin.withdraw(request, KnowledgePassage.objects.all())
        self.assertFalse(KnowledgePassage.published().exists())

    def test_unconfigured_command_fails_without_creating_content(self):
        with override_settings(ISLAMIC_KNOWLEDGE_FEEDS={}), self.assertRaises(CommandError):
            call_command('sync_islamic_provider', provider='azan_kz', stdout=StringIO())
        self.assertFalse(KnowledgePassage.objects.exists())


@override_settings(ISLAMIC_NEURAL_SEARCH_ENABLED=True)
class NeuralRetrievalTests(PublicationFixtures, TestCase):
    def indexed(self, external_id, axis=0, **changes):
        import_export('azan_kz', export(external_id=external_id, **changes))
        row = KnowledgePassage.objects.get(external_id=external_id)
        self.publish(row)
        KnowledgePassage.objects.filter(pk=row.pk).update(embedding=unit(axis),
            embedding_model=MODEL_VERSION, embedding_digest=row.digest)
        return row

    def test_semantic_rank_is_stable_and_returns_source_attribution(self):
        self.indexed('a', 0)
        self.indexed('b', 0)
        self.indexed('c', 1)
        with patch('islamic_knowledge.neural.encode', return_value=[unit(0)]) as embed:
            response = self.client.get('/api/islamic/search/?q=fixture&limit=2')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([row['external_id'] for row in body['results']], ['a', 'b'])
        self.assertEqual(body['results'][0]['similarity'], 1.0)
        self.assertFalse(body['similarity_is_confidence'])
        self.assertEqual(body['model'], MODEL_VERSION)
        embed.assert_called_once_with(['fixture'])

    def test_search_excludes_unknown_stale_models_unreviewed_and_revoked(self):
        valid = self.indexed('valid')
        stale = self.indexed('stale')
        revoked = self.indexed('revoked')
        wrong = self.indexed('wrong-model')
        import_export('azan_kz', export(external_id='unreviewed'))
        KnowledgePassage.objects.filter(pk=stale.pk).update(embedding_digest='old')
        KnowledgePassage.objects.filter(pk=revoked.pk).update(revoked=True)
        KnowledgePassage.objects.filter(pk=wrong.pk).update(embedding_model='other')
        with patch('islamic_knowledge.neural.encode', return_value=[unit(0)]):
            self.assertEqual([row.pk for _, row in semantic_search('fixture')], [valid.pk])

    def test_empty_corpus_does_not_load_a_model(self):
        with patch('islamic_knowledge.neural.encode') as embed:
            self.assertEqual(semantic_search('fixture'), [])
        embed.assert_not_called()

    def test_disabled_and_missing_encoder_are_explicit_503(self):
        with override_settings(ISLAMIC_NEURAL_SEARCH_ENABLED=False):
            self.assertEqual(self.client.get('/api/islamic/search/?q=fixture').status_code, 503)
        self.indexed('a')
        with patch('islamic_knowledge.neural.encode', side_effect=NeuralUnavailable('fixture unavailable')):
            self.assertEqual(self.client.get('/api/islamic/search/?q=fixture').status_code, 503)

    def test_bad_query_limit_and_corpus_capacity_are_explicit(self):
        for query in ('', ' ', 'x' * 1001):
            with self.assertRaises(ValueError):
                semantic_search(query)
        for limit in (0, 21, True):
            with self.assertRaises(ValueError):
                semantic_search('fixture', limit=limit)
        self.indexed('a')
        with patch('islamic_knowledge.neural.MAX_INDEXED_PASSAGES', 0), self.assertRaises(NeuralUnavailable):
            semantic_search('fixture')

    def test_mid_search_revocation_is_rechecked(self):
        row = self.indexed('withdraw-me')
        def withdraw(limit, iterable, key):
            ranked = nlargest(limit, iterable, key=key)
            KnowledgePassage.objects.filter(pk=row.pk).update(revoked=True)
            return ranked
        with patch('islamic_knowledge.neural.encode', return_value=[unit(0)]), patch('islamic_knowledge.neural.nlargest', side_effect=withdraw):
            self.assertEqual(semantic_search('fixture'), [])

    def test_indexing_is_idempotent_and_refuses_a_concurrent_edit(self):
        import_export('azan_kz', export())
        row = KnowledgePassage.objects.get()
        self.publish(row)
        with patch('islamic_knowledge.neural.encode', return_value=[unit(0)]) as embed:
            self.assertEqual(index_passages(), 1)
            self.assertEqual(index_passages(), 0)
        embed.assert_called_once()
        row.refresh_from_db()
        row.passage = 'Changed synthetic fixture.'
        row.save()
        self.publish(row)
        def change_again(texts):
            row.passage = 'Another changed fixture.'
            row.save()
            return [unit(0)]
        with patch('islamic_knowledge.neural.encode', side_effect=change_again):
            self.assertEqual(index_passages(), 0)
        row.refresh_from_db()
        self.assertEqual(row.embedding, [])

    def test_public_neural_endpoint_is_throttled(self):
        with override_settings(ISLAMIC_NEURAL_SEARCH_ENABLED=False):
            for _ in range(5):
                self.assertEqual(self.client.get('/api/islamic/search/?q=fixture').status_code, 503)
            self.assertEqual(self.client.get('/api/islamic/search/?q=fixture').status_code, 429)


@override_settings(ISLAMIC_NEURAL_SEARCH_ENABLED=True)
class NeuralEncoderContractTests(SimpleTestCase):
    def test_loader_pins_revision_disables_remote_code_and_downloads(self):
        factory = Mock()
        module = SimpleNamespace(SentenceTransformer=factory)
        with patch.dict('sys.modules', {'sentence_transformers': module}):
            load_encoder()
        self.assertEqual(factory.call_args.kwargs['revision'], MODEL_REVISION)
        self.assertTrue(factory.call_args.kwargs['local_files_only'])
        self.assertFalse(factory.call_args.kwargs['trust_remote_code'])

    def test_encoder_normalises_vectors_and_refuses_silent_truncation(self):
        model = SimpleNamespace(max_seq_length=128,
            tokenizer=Mock(return_value={'input_ids': [[1, 2]]}),
            encode=Mock(return_value=np.ones((1, DIMENSIONS))))
        with patch('islamic_knowledge.neural._encoder', return_value=model):
            result = encode(['fixture'])[0]
            self.assertAlmostEqual(float(np.linalg.norm(result)), 1.0)
            model.tokenizer.return_value = {'input_ids': [list(range(129))]}
            with self.assertRaises(ValueError):
                encode(['long fixture'])
        self.assertEqual(model.encode.call_count, 1)

    def test_wrong_dimension_nonfinite_and_zero_outputs_fail_closed(self):
        for vector in (np.zeros((1, DIMENSIONS)), np.full((1, DIMENSIONS), np.nan), np.ones((1, 5))):
            model = SimpleNamespace(max_seq_length=128,
                tokenizer=Mock(return_value={'input_ids': [[1]]}), encode=Mock(return_value=vector))
            with self.subTest(shape=vector.shape), patch('islamic_knowledge.neural._encoder', return_value=model), self.assertRaises(NeuralUnavailable):
                encode(['fixture'])
