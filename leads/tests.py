"""
Leads app tests — request access form, honeypot, rate limiting.
Run with: python manage.py test leads --verbosity=2
"""
from django.test import TestCase, Client
from django.urls import reverse

from .models import AccessRequest


VALID_POST = {
    'full_name':        'Jane Smith',
    'work_email':       'jane@acmeplc.com',
    'company':          'Acme Capital LLP',
    'country':          'United Kingdom',
    'target_entity':    'Acme Refinery Ltd',
    'sector':           'Oil & Gas',
    'role':             'investor',
    'product_interest': 'readiness_report',
    'message':          '',
    'website':          '',   # honeypot — must be empty
}


class RequestAccessFormTests(TestCase):

    def setUp(self):
        self.c = Client(SERVER_NAME='localhost')

    def test_get_form_200(self):
        r = self.c.get(reverse('leads:request_access'))
        self.assertEqual(r.status_code, 200)

    def test_valid_submission_redirects_to_thank_you(self):
        r = self.c.post(reverse('leads:request_access'), VALID_POST)
        self.assertRedirects(r, reverse('leads:thank_you'), fetch_redirect_response=False)

    def test_valid_submission_creates_record(self):
        self.c.post(reverse('leads:request_access'), VALID_POST)
        self.assertEqual(AccessRequest.objects.count(), 1)
        obj = AccessRequest.objects.first()
        self.assertEqual(obj.company, 'Acme Capital LLP')
        self.assertEqual(obj.target_entity, 'Acme Refinery Ltd')
        self.assertEqual(obj.role, 'investor')
        self.assertEqual(obj.product_interest, 'readiness_report')
        self.assertEqual(obj.status, 'new')

    def test_honeypot_prevents_record_creation(self):
        """Honeypot-triggered submissions redirect silently but save nothing."""
        data = {**VALID_POST, 'website': 'http://spam.example.com'}
        r = self.c.post(reverse('leads:request_access'), data)
        self.assertRedirects(r, reverse('leads:thank_you'), fetch_redirect_response=False)
        self.assertEqual(AccessRequest.objects.count(), 0)

    def test_missing_required_field_shows_form(self):
        """Missing full_name → form is re-shown with errors, no DB record."""
        data = {**VALID_POST, 'full_name': ''}
        r = self.c.post(reverse('leads:request_access'), data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(AccessRequest.objects.count(), 0)

    def test_missing_target_entity_shows_form(self):
        """Missing company/project to assess → form re-shown, no DB record."""
        data = {**VALID_POST, 'target_entity': ''}
        r = self.c.post(reverse('leads:request_access'), data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(AccessRequest.objects.count(), 0)

    def test_optional_fields_can_be_blank(self):
        """Country, sector, role, product_interest are optional."""
        data = {**VALID_POST, 'country': '', 'sector': '', 'role': '', 'product_interest': ''}
        r = self.c.post(reverse('leads:request_access'), data)
        self.assertRedirects(r, reverse('leads:thank_you'), fetch_redirect_response=False)
        self.assertEqual(AccessRequest.objects.count(), 1)

    def test_thank_you_page_200(self):
        r = self.c.get(reverse('leads:thank_you'))
        self.assertEqual(r.status_code, 200)

    def test_success_page_200(self):
        """Legacy success alias still resolves."""
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
