"""
Access + render tests for the staff-only Tazkiyah 114 internal dashboard.

Confirms staff-only gating and that all four preview links, the safety warning,
and noindex render. Read-only hub; no models, no persistence.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class TazkiyahDashboardAccessTests(TestCase):
    def setUp(self):
        self.url = reverse('tazkiyah_dashboard')

    def test_anonymous_is_redirected(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_non_staff_is_redirected(self):
        User.objects.create_user(username='plain5', password='pw12345!', is_staff=False)
        self.client.login(username='plain5', password='pw12345!')
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_staff_can_view(self):
        User.objects.create_user(username='staffer5', password='pw12345!', is_staff=True)
        self.client.login(username='staffer5', password='pw12345!')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # Safety warning + noindex
        self.assertIn('Internal preview only.', html)
        self.assertIn('not tafsir', html.lower())
        self.assertIn('not fatwa', html.lower())
        self.assertIn('scholar review', html.lower())
        self.assertIn('noindex', html.lower())
        # All four preview links render
        for path in ['/tazkiyah-114-preview/', '/tazkiyah-114-struggles-preview/',
                     '/tazkiyah-114-daily-preview/', '/tazkiyah-114-repair-engine-preview/']:
            self.assertIn(path, html)
        # Summary stats render
        for stat in ['surahs', 'pathways', 'struggles', 'heart wounds', 'internal preview tools']:
            self.assertIn(stat, html.lower())
