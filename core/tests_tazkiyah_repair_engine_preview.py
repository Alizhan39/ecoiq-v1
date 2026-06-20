"""
Access + render tests for the staff-only Qur'an Repair Engine preview.

Confirms staff-only gating and that the repair flow, heart wound cards, sin
cycle, and safety labels render. Read-only preview; no models, no persistence.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class TazkiyahRepairEnginePreviewAccessTests(TestCase):
    def setUp(self):
        self.url = reverse('tazkiyah_repair_engine_preview')

    def test_anonymous_is_redirected(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_non_staff_is_redirected(self):
        User.objects.create_user(username='plain4', password='pw12345!', is_staff=False)
        self.client.login(username='plain4', password='pw12345!')
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_staff_can_view(self):
        User.objects.create_user(username='staffer4', password='pw12345!', is_staff=True)
        self.client.login(username='staffer4', password='pw12345!')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # Safety warning + labels + noindex
        self.assertIn('Internal preview only.', html)
        self.assertIn('not fatwa', html.lower())
        self.assertIn('not tafsir', html.lower())
        self.assertIn('draft architecture', html.lower())
        self.assertIn('non-authoritative', html.lower())
        self.assertIn('scholar review pending', html.lower())
        self.assertIn('noindex', html.lower())
        # Repair flow renders (first + last step)
        self.assertIn('Choose struggle', html)
        self.assertIn('Track 7 day consistency', html)
        # Heart wound cards render (12)
        self.assertEqual(html.count('class="tzpr__wound"'), 12)
        self.assertIn('Fear of poverty', html)
        # Sin cycle + repair cycle render
        self.assertIn('The sin cycle', html)
        self.assertIn('The repair cycle', html)
        self.assertIn('Tawbah', html)
        # Consistency model
        self.assertIn('30-day transformation', html)
