"""
Leads app tests — request access form, honeypot, rate limiting.
Run with: python manage.py test leads --verbosity=2
"""
from django.test import TestCase, Client
from django.urls import reverse

from .models import AccessRequest


VALID_POST = {
    'full_name':     'Jane Smith',
    'company':       'Acme Refinery Ltd',
    'work_email':    'jane@acmeplc.com',
    'industry':      'oil_gas',
    'facility_type': 'Continuous process refinery',
    'company_size':  '201_1000',
    'challenge':     'We have significant energy losses in our distillation units and no visibility into root causes.',
    'message':       '',
    'website':       '',   # honeypot — must be empty
}


class RequestAccessFormTests(TestCase):

    def setUp(self):
        self.c = Client(SERVER_NAME='localhost')

    def test_get_form_200(self):
        r = self.c.get(reverse('leads:request_access'))
        self.assertEqual(r.status_code, 200)

    def test_valid_submission_redirects_to_success(self):
        r = self.c.post(reverse('leads:request_access'), VALID_POST)
        self.assertRedirects(r, reverse('leads:success'), fetch_redirect_response=False)

    def test_valid_submission_creates_record(self):
        self.c.post(reverse('leads:request_access'), VALID_POST)
        self.assertEqual(AccessRequest.objects.count(), 1)
        obj = AccessRequest.objects.first()
        self.assertEqual(obj.company, 'Acme Refinery Ltd')
        self.assertEqual(obj.status, 'new')

    def test_honeypot_prevents_record_creation(self):
        """Honeypot-triggered submissions redirect silently but save nothing."""
        data = {**VALID_POST, 'website': 'http://spam.example.com'}
        r = self.c.post(reverse('leads:request_access'), data)
        self.assertRedirects(r, reverse('leads:success'), fetch_redirect_response=False)
        self.assertEqual(AccessRequest.objects.count(), 0)

    def test_missing_required_field_shows_form(self):
        """Missing full_name → form is re-shown with errors, no DB record."""
        data = {**VALID_POST, 'full_name': ''}
        r = self.c.post(reverse('leads:request_access'), data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(AccessRequest.objects.count(), 0)

    def test_challenge_too_short_shows_form(self):
        """Challenge under 30 chars should fail validation."""
        data = {**VALID_POST, 'challenge': 'Too short'}
        r = self.c.post(reverse('leads:request_access'), data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(AccessRequest.objects.count(), 0)

    def test_success_page_200(self):
        r = self.c.get(reverse('leads:success'))
        self.assertEqual(r.status_code, 200)


class RateLimitTests(TestCase):

    def setUp(self):
        self.c = Client(SERVER_NAME='localhost', REMOTE_ADDR='10.0.0.1')

    def test_rate_limit_after_three_submissions(self):
        """Fourth submission from same IP within 1 hour should show rate_limited."""
        for _ in range(3):
            self.c.post(reverse('leads:request_access'), VALID_POST)

        r = self.c.post(reverse('leads:request_access'), VALID_POST)
        # Rate-limited response re-renders the form page
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context.get('rate_limited', False))
