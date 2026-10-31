"""Provider transport failures use a safe, consistent adapter contract."""
import json
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase, override_settings

from .providers import ProviderUnavailable, fetch_feed


@override_settings(ISLAMIC_KNOWLEDGE_FEEDS={'azan_kz': 'https://azan.kz/agreed-feed.json'})
class FeedTransportTests(SimpleTestCase):
    def response(self, content_type='application/json'):
        response = Mock(status_code=200, headers={'Content-Type': content_type})
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.iter_content.return_value = [json.dumps({'passages': []}).encode()]
        return response

    def test_connection_and_timeout_errors_use_safe_unavailability_message(self):
        for error in (requests.ConnectionError('private transport details'),
                      requests.Timeout('private transport details')):
            with self.subTest(error=type(error).__name__), patch(
                    'islamic_knowledge.providers.requests.get', side_effect=error):
                with self.assertRaises(ProviderUnavailable) as raised:
                    fetch_feed('azan_kz')
                self.assertNotIn('private transport details', str(raised.exception))
                self.assertIs(raised.exception.__cause__, error)

    def test_interrupted_stream_is_unavailable_and_closes_response(self):
        response = self.response()
        error = requests.exceptions.ChunkedEncodingError('private transport details')
        def interrupted():
            yield b'{"passages":'
            raise error

        response.iter_content.return_value = interrupted()
        with patch('islamic_knowledge.providers.requests.get', return_value=response):
            with self.assertRaises(ProviderUnavailable) as raised:
                fetch_feed('azan_kz')
        self.assertIs(raised.exception.__cause__, error)
        response.__exit__.assert_called_once()

    def test_misleading_media_types_are_rejected_without_reading_body(self):
        for media_type in ('application/jsonp', 'text/html; note=application/json',
                           'application/json-malformed', ''):
            response = self.response(media_type)
            with self.subTest(media_type=media_type), patch(
                    'islamic_knowledge.providers.requests.get', return_value=response):
                with self.assertRaisesMessage(ProviderUnavailable, 'Provider feed must return JSON.'):
                    fetch_feed('azan_kz')
            response.iter_content.assert_not_called()
            response.__exit__.assert_called_once()

    def test_json_media_type_accepts_parameters_and_case(self):
        for media_type in ('application/json; charset=utf-8', 'Application/JSON', ' application/json '):
            with self.subTest(media_type=media_type), patch(
                    'islamic_knowledge.providers.requests.get', return_value=self.response(media_type)):
                self.assertEqual(fetch_feed('azan_kz'), {'passages': []})

    def test_status_and_invalid_json_keep_existing_unavailability_errors(self):
        response = self.response()
        response.status_code = 503
        with patch('islamic_knowledge.providers.requests.get', return_value=response):
            with self.assertRaisesMessage(ProviderUnavailable, 'Provider feed did not return HTTP 200.'):
                fetch_feed('azan_kz')
        response.status_code = 200
        response.iter_content.return_value = [b'not JSON']
        with patch('islamic_knowledge.providers.requests.get', return_value=response):
            with self.assertRaisesMessage(ProviderUnavailable, 'Provider feed contains invalid JSON.'):
                fetch_feed('azan_kz')
