"""
Access + render tests for the staff-only Tazkiyah 114 seed preview page.

Confirms the page is gated to staff and renders the non-authoritative content
with its safety labels. Uses the DB (user creation) so it is a TestCase.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class TazkiyahPreviewAccessTests(TestCase):
    def setUp(self):
        self.url = reverse('tazkiyah_preview')

    def test_anonymous_is_redirected(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)  # staff_member_required → login

    def test_non_staff_is_redirected(self):
        User.objects.create_user(username='plain', password='pw12345!', is_staff=False)
        self.client.login(username='plain', password='pw12345!')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_staff_can_view_with_safety_labels(self):
        User.objects.create_user(username='staffer', password='pw12345!', is_staff=True)
        self.client.login(username='staffer', password='pw12345!')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # Internal warning + non-authoritative framing present
        self.assertIn('Internal preview only.', html)
        self.assertIn('not fatwa', html.lower())
        self.assertIn('non-authoritative', html.lower())
        # Renders seed content (first + last surah) and all 114 cards
        self.assertIn('Al-Fatihah', html)
        self.assertIn('An-Nas', html)
        self.assertEqual(html.count('class="tzp__card"'), 114)
        # Summary stats + filters present
        self.assertIn('surah records', html)
        self.assertIn('id="tzpSearch"', html)
        self.assertIn('All revelation', html)
        # noindex for safety
        self.assertIn('noindex', html.lower())
