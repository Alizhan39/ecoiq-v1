"""
Access + render tests for the staff-only Daily Tazkiyah tracker preview.

Confirms the page is gated to staff and renders the demo daily loop, checklist,
and safety labels. Static demo — no models, no persistence. Uses the DB only to
create test users.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class TazkiyahDailyPreviewAccessTests(TestCase):
    def setUp(self):
        self.url = reverse('tazkiyah_daily_preview')

    def test_anonymous_is_redirected(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_non_staff_is_redirected(self):
        User.objects.create_user(username='plain3', password='pw12345!', is_staff=False)
        self.client.login(username='plain3', password='pw12345!')
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_staff_can_view(self):
        User.objects.create_user(username='staffer3', password='pw12345!', is_staff=True)
        self.client.login(username='staffer3', password='pw12345!')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # Internal warning + safety labels
        self.assertIn('Internal preview only.', html)
        self.assertIn('not fatwa', html.lower())
        self.assertIn('non-authoritative', html.lower())
        self.assertIn('draft reflection', html.lower())
        self.assertIn('translation pending', html.lower())
        self.assertIn('scholar review pending', html.lower())
        self.assertIn('noindex', html.lower())
        # Daily loop steps render
        for step in ['Read', 'Reflect', 'Act', 'Make Dua', 'Journal']:
            self.assertIn(step, html)
        # Checklist renders (all 5 items)
        self.assertEqual(html.count('class="tzpd__check"'), 5)
        for item in ['I read today', 'I reflected today', 'I acted on one ayah',
                     'I made dua', 'I wrote one journal note']:
            self.assertIn(item, html)
        # 7-day streak mockup + no-persistence note
        self.assertEqual(html.count('class="tzpd__day'), 7)
        self.assertIn('no user data stored', html.lower())
