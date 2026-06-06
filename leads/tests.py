"""
Leads app tests — request access form, honeypot, rate limiting.
Run with: python manage.py test leads --verbosity=2
"""
from django.test import TestCase, Client
from django.urls import reverse

from .models import AccessRequest


VALID_POST = {
    'full_name':        'Jane Smith',
    'work_email':       'Jane@AcmePLC.com',
    'company':          'Acme Capital LLP',
    'country':          'United Kingdom',
    'target_entity':    'Acme Refinery Ltd',
    'sector':           'Oil & Gas',
    'role':             'investor',
    'product_interest': 'readiness_report',
    'message':          'Please assess our transition readiness.',
    'hp_field':         '',   # honeypot — must be empty on genuine submissions
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

    def test_valid_submission_creates_exactly_one_record(self):
        self.c.post(reverse('leads:request_access'), VALID_POST)
        self.assertEqual(AccessRequest.objects.count(), 1)

    def test_saved_object_contains_all_fields(self):
        """A valid POST persists every submitted field to the AccessRequest."""
        self.c.post(reverse('leads:request_access'), VALID_POST)
        obj = AccessRequest.objects.get()
        self.assertEqual(obj.full_name, 'Jane Smith')                 # name
        self.assertEqual(obj.work_email, 'jane@acmeplc.com')          # email (normalised)
        self.assertEqual(obj.company, 'Acme Capital LLP')             # organisation
        self.assertEqual(obj.country, 'United Kingdom')               # country
        self.assertEqual(obj.target_entity, 'Acme Refinery Ltd')      # company/project
        self.assertEqual(obj.sector, 'Oil & Gas')                     # sector
        self.assertEqual(obj.role, 'investor')                        # role
        self.assertEqual(obj.product_interest, 'readiness_report')    # product_interest
        self.assertEqual(obj.message, 'Please assess our transition readiness.')  # message
        self.assertEqual(obj.status, 'new')

    def test_honeypot_prevents_record_creation(self):
        """A filled honeypot (hp_field) redirects silently but saves nothing."""
        data = {**VALID_POST, 'hp_field': 'http://spam.example.com'}
        r = self.c.post(reverse('leads:request_access'), data)
        self.assertRedirects(r, reverse('leads:thank_you'), fetch_redirect_response=False)
        self.assertEqual(AccessRequest.objects.count(), 0)

    def test_autofilled_website_does_not_drop_submission(self):
        """
        Regression: the honeypot must NOT be named 'website' (or any autofill
        token). A browser/password-manager that autofills a 'website' field must
        not cause a genuine submission to be silently dropped.
        """
        data = {**VALID_POST, 'website': 'https://acmecapital.com'}
        r = self.c.post(reverse('leads:request_access'), data)
        self.assertRedirects(r, reverse('leads:thank_you'), fetch_redirect_response=False)
        self.assertEqual(AccessRequest.objects.count(), 1)

    def test_invalid_post_shows_errors_and_saves_nothing(self):
        """Missing required fields → 200 re-render with visible errors, no record."""
        data = {**VALID_POST, 'full_name': '', 'work_email': '', 'company': '', 'target_entity': ''}
        r = self.c.post(reverse('leads:request_access'), data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(AccessRequest.objects.count(), 0)
        self.assertTrue(r.context['form'].errors)
        self.assertContains(r, 'This field is required.')

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
