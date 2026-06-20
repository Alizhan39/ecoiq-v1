"""
Tests for the PUBLIC Tazkiyah 114 marketing landing page.

Confirms it is publicly reachable, contains the trust disclaimer and a CTA, and
— critically — does NOT expose any draft Surah seed / pathway / repair-engine
content (no draft reflections, Arabic surah text, ayah text, or status flags).
No auth required (public page).
"""
import json

from django.test import TestCase
from django.urls import reverse

from core.management.commands.validate_tazkiyah114_seeds import DEFAULT_SEED_PATH


class TazkiyahLandingTests(TestCase):
    def setUp(self):
        self.url = reverse('tazkiyah')  # /tazkiyah-114/

    def test_public_returns_200(self):
        resp = self.client.get(self.url, SERVER_NAME='localhost')
        self.assertEqual(resp.status_code, 200)

    def test_surah_map_alias_returns_200(self):
        resp = self.client.get(reverse('surah_map'), SERVER_NAME='localhost')
        self.assertEqual(resp.status_code, 200)

    def test_trust_disclaimer_present(self):
        html = self.client.get(self.url, SERVER_NAME='localhost').content.decode().lower()
        self.assertIn('not tafsir', html)
        self.assertIn('not fatwa', html)
        self.assertIn('scholar review required', html)
        self.assertIn('inspired by qur', html)

    def test_cta_present(self):
        html = self.client.get(self.url, SERVER_NAME='localhost').content.decode()
        self.assertIn('Request Access', html)
        self.assertIn('/request-access/', html)

    def test_does_not_expose_draft_seed_content(self):
        html = self.client.get(self.url, SERVER_NAME='localhost').content.decode()
        # No seed/review status flags should leak to the public page.
        for marker in ['draft_reflection', 'scholar_review_pending', 'translation_pending',
                       'surah_number', 'repair_engine', 'heart_wounds']:
            self.assertNotIn(marker, html)
        # No Arabic surah-name text from the seed should appear publicly.
        seeds = json.loads(DEFAULT_SEED_PATH.read_text(encoding='utf-8'))
        for s in seeds['surahs'][:30]:
            self.assertNotIn(s['surah_name_arabic'], html)
        # No specific per-surah draft theme text should appear publicly.
        self.assertNotIn(seeds['surahs'][0]['short_theme'], html)
