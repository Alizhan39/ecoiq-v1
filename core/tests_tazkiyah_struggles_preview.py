"""
Access + render tests for the staff-only "Choose Your Struggle" journey preview.

Confirms the page is gated to staff and renders the non-authoritative
struggle → pathway → surah journey with its safety labels. Uses the DB.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class TazkiyahStrugglesPreviewAccessTests(TestCase):
    def setUp(self):
        self.url = reverse('tazkiyah_struggles_preview')

    def test_anonymous_is_redirected(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_non_staff_is_redirected(self):
        User.objects.create_user(username='plain2', password='pw12345!', is_staff=False)
        self.client.login(username='plain2', password='pw12345!')
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_staff_can_view_journey(self):
        User.objects.create_user(username='staffer2', password='pw12345!', is_staff=True)
        self.client.login(username='staffer2', password='pw12345!')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # Internal warning + non-authoritative framing
        self.assertIn('Internal preview only.', html)
        self.assertIn('not fatwa', html.lower())
        self.assertIn('non-authoritative', html.lower())
        self.assertIn('suggested pathway', html.lower())
        self.assertIn('noindex', html.lower())
        # 12 struggle cards render
        self.assertEqual(html.count('class="tzps__struggle"'), 12)
        # A known struggle + a known pathway title + a suggested surah render
        self.assertIn('I feel anxious', html)
        self.assertIn('Healing Anxiety and Fear', html)
        self.assertIn('Ar-Ra', html)  # Ar-Ra'd appears in a pathway
