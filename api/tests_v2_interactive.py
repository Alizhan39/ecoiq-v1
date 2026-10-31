import json
from pathlib import Path
import struct

from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase


class InteractiveAPI(SimpleTestCase):
    """A public demo must never query or expose customer records."""

    def setUp(self):
        cache.clear()

    def test_catalog_has_ten_per_category_and_truthful_status(self):
        for category in ('ui', 'ar'):
            response = self.client.get('/api/v2/interactive/libraries/', {'category': category})
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body['count'], 10)
            self.assertEqual(len({row['id'] for row in body['results']}), 10)
            self.assertTrue(all(row['category'] == category for row in body['results']))
            self.assertTrue(all(row['documentation_url'].startswith('https://')
                                for row in body['results']))
            self.assertEqual(sum(row['status'] == 'INTEGRATED' for row in body['results']), 1)

    def test_invalid_filters_are_json_errors(self):
        for path, params in [('/api/v2/interactive/libraries/', {'category': 'nope'}),
                             ('/api/v2/interactive/scenes/stewardship-demo/', {'lang': 'xx'})]:
            response = self.client.get(path, params)
            self.assertEqual(response.status_code, 400)
            self.assertIn('detail', response.json())

    def test_scene_is_demo_and_has_no_invented_measurements(self):
        index = self.client.get('/api/v2/interactive/scenes/').json()
        self.assertEqual(index['count'], 1)
        body = self.client.get(index['results'][0]['detail_url']).json()
        self.assertTrue(body['is_demo'])
        self.assertFalse(body['verified'])
        self.assertFalse(body['scale_is_measured'])
        self.assertTrue(body['model_url'].startswith('/static/'))
        for part in body['hotspots']:
            self.assertIsNone(part['measurement'])
            self.assertIsNone(part['evidence_url'])

    def test_four_languages_and_arabic_direction(self):
        for lang in ('en', 'ru', 'kk', 'ar'):
            body = self.client.get('/api/v2/interactive/scenes/stewardship-demo/', {'lang': lang}).json()
            self.assertEqual(body['language'], lang)
            self.assertEqual(body['direction'], 'rtl' if lang == 'ar' else 'ltr')
            self.assertEqual(len(body['hotspots']), 3)
            self.assertTrue(all(part['label'] for part in body['hotspots']))

    def test_unknown_scene_cannot_resolve_a_private_asset(self):
        response = self.client.get('/api/v2/interactive/scenes/private-asset/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'detail': 'Not found.'})

    def test_read_only(self):
        for path in ('libraries/', 'scenes/', 'scenes/stewardship-demo/'):
            self.assertEqual(self.client.post('/api/v2/interactive/' + path).status_code, 405)

    def test_interactive_route_has_the_spa_shell_and_title(self):
        response = self.client.get('/labs/interactive/')
        self.assertContains(response, 'id="root"')
        self.assertContains(response, '<title>Interactive 3D and AR')

    def test_local_glb_is_self_contained(self):
        data = (Path(settings.BASE_DIR) / 'static/models/stewardship-demo.glb').read_bytes()
        magic, version, length = struct.unpack('<III', data[:12])
        self.assertEqual((magic, version, length), (0x46546c67, 2, len(data)))
        json_length, chunk_type = struct.unpack('<II', data[12:20])
        self.assertEqual(chunk_type, 0x4e4f534a)
        model = json.loads(data[20:20 + json_length])
        self.assertEqual(len(model['nodes']), 3)
        self.assertNotIn('uri', model['buffers'][0])
