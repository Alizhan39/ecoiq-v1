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


class ReportPreviewTests(TestCase):
    """Staff-only internal draft + client-facing report preview pages."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        U = get_user_model()
        self.staff = U.objects.create_user(
            username='staff_user', password='x', email='staff@ecoiq.uk', is_staff=True,
        )
        self.normal = U.objects.create_user(
            username='normal_user', password='x', email='user@example.com', is_staff=False,
        )
        self.ar = AccessRequest.objects.create(
            full_name='Jane Investor', work_email='jane@fund.com', company='Green Fund LLP',
            country='United Kingdom', target_entity='KazMunayGas', sector='Oil & Gas',
            role='investor', product_interest='readiness_report',
            draft_score_summary='EcoIQ 84.2 / Maqasid 92 — strong readiness.',
            draft_risk_summary='Medium scope-3 exposure; governance improving.',
            draft_recommendations='Publish scope-3 baseline; formalise ESG committee.',
            draft_roadmap='30/60/90-day plan: stabilise, align, package.',
            internal_notes='SECRET-INTERNAL-NOTE call client Tuesday.',
        )
        self.client_url = reverse('client_report_preview', args=[self.ar.pk])
        self.draft_url  = reverse('admin_report_preview', args=[self.ar.pk])

    # ── Client report preview ──────────────────────────────────────────────
    def test_staff_can_access_client_preview(self):
        self.client.force_login(self.staff)
        r = self.client.get(self.client_url)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'leads/client_report_preview.html')

    def test_non_staff_cannot_access_client_preview(self):
        self.client.force_login(self.normal)
        r = self.client.get(self.client_url)
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])

    def test_anonymous_cannot_access_client_preview(self):
        r = self.client.get(self.client_url)
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])

    def test_client_preview_hides_internal_notes(self):
        self.client.force_login(self.staff)
        body = self.client.get(self.client_url).content.decode()
        self.assertNotIn('SECRET-INTERNAL-NOTE', body)
        self.assertNotIn('internal draft', body.lower())
        self.assertNotIn('Internal analyst notes', body)

    def test_client_preview_renders_core_fields(self):
        self.client.force_login(self.staff)
        body = self.client.get(self.client_url).content.decode()
        self.assertIn('EcoIQ Investor Readiness Report', body)   # title
        self.assertIn('Green Fund LLP', body)                    # organisation (subtitle)
        self.assertIn('KazMunayGas', body)                       # company/project
        self.assertIn('United Kingdom', body)                    # country
        self.assertIn('Oil &amp; Gas', body)                     # sector (HTML-escaped)
        self.assertIn('EcoIQ 84.2 / Maqasid 92', body)           # draft score content
        self.assertIn('formalise ESG committee', body)           # draft recommendation content

    def test_client_preview_placeholder_when_empty(self):
        self.ar.draft_score_summary = ''
        self.ar.save(update_fields=['draft_score_summary'])
        self.client.force_login(self.staff)
        body = self.client.get(self.client_url).content.decode()
        self.assertIn('Pending final analyst review.', body)

    def test_missing_access_request_returns_404(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse('client_report_preview', args=[999999]))
        self.assertEqual(r.status_code, 404)

    # ── Existing internal draft preview still works ────────────────────────
    def test_draft_preview_still_works_for_staff(self):
        self.client.force_login(self.staff)
        r = self.client.get(self.draft_url)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'leads/admin_report_preview.html')

    def test_draft_preview_blocks_non_staff(self):
        self.client.force_login(self.normal)
        r = self.client.get(self.draft_url)
        self.assertEqual(r.status_code, 302)


class GenerateStarterDraftActionTests(TestCase):
    """Admin action: 'Generate starter draft'."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        U = get_user_model()
        self.admin = U.objects.create_superuser(
            username='su', password='x', email='su@ecoiq.uk',
        )
        self.client.force_login(self.admin)
        self.changelist = reverse('admin:leads_accessrequest_changelist')

    def _run_action(self, *pks):
        return self.client.post(self.changelist, {
            'action': 'generate_starter_draft',
            '_selected_action': [str(pk) for pk in pks],
        }, follow=True)

    def test_action_fills_empty_draft_fields(self):
        obj = AccessRequest.objects.create(
            full_name='Jane', work_email='j@f.com', company='Green Fund LLP',
            country='United Kingdom', target_entity='KazMunayGas', sector='Oil & Gas',
            role='investor', product_interest='readiness_report',
            report_status='not_started',
        )
        self._run_action(obj.pk)
        obj.refresh_from_db()
        # All four draft fields are now populated...
        self.assertTrue(obj.draft_score_summary.strip())
        self.assertTrue(obj.draft_risk_summary.strip())
        self.assertTrue(obj.draft_recommendations.strip())
        self.assertTrue(obj.draft_roadmap.strip())
        # ...and tailored to the lead's data
        self.assertIn('KazMunayGas', obj.draft_score_summary)
        self.assertIn('United Kingdom', obj.draft_risk_summary)
        self.assertIn('Oil & Gas', obj.draft_recommendations)

    def test_action_does_not_overwrite_existing_fields(self):
        obj = AccessRequest.objects.create(
            full_name='Jane', work_email='j2@f.com', company='Acme',
            target_entity='Acme Refinery', sector='Chemicals',
            draft_score_summary='ANALYST WRITTEN SCORE',
            draft_roadmap='ANALYST WRITTEN ROADMAP',
            report_status='draft_needed',
        )
        self._run_action(obj.pk)
        obj.refresh_from_db()
        # Pre-filled fields are preserved verbatim
        self.assertEqual(obj.draft_score_summary, 'ANALYST WRITTEN SCORE')
        self.assertEqual(obj.draft_roadmap, 'ANALYST WRITTEN ROADMAP')
        # Empty fields get populated
        self.assertTrue(obj.draft_risk_summary.strip())
        self.assertTrue(obj.draft_recommendations.strip())

    def test_action_sets_report_status_when_appropriate(self):
        for start in ('not_started', 'draft_needed'):
            obj = AccessRequest.objects.create(
                full_name='X', work_email=f'{start}@f.com', company='C',
                target_entity='T', report_status=start,
            )
            self._run_action(obj.pk)
            obj.refresh_from_db()
            self.assertEqual(obj.report_status, 'draft_ready')

    def test_action_does_not_change_report_status_when_already_advanced(self):
        obj = AccessRequest.objects.create(
            full_name='X', work_email='sent@f.com', company='C',
            target_entity='T', report_status='sent',
        )
        self._run_action(obj.pk)
        obj.refresh_from_db()
        self.assertEqual(obj.report_status, 'sent')

    def test_action_success_message(self):
        objs = [
            AccessRequest.objects.create(
                full_name='X', work_email=f'm{i}@f.com', company='C', target_entity='T',
            )
            for i in range(2)
        ]
        r = self._run_action(*[o.pk for o in objs])
        self.assertContains(r, 'Starter draft generated for 2 access request(s).')


# ── EnterpriseEnquiry (EcoIQ Enterprise Pricing page) ───────────────────────────

from .models import EnterpriseEnquiry

VALID_ENTERPRISE_POST = {
    'full_name':            'Sara Al Qasimi',
    'organisation':         'Gulf Horizon Investments',
    'work_email':           'Sara@GulfHorizon.example',
    'country':              'United Arab Emirates',
    'organisation_type':    'sovereign_wealth_fund',
    'preferred_engagement': 'pilot_90day',
    'estimated_assets':     '35 portfolio companies',
    'use_case':             'Portfolio-wide ethical screening',
    'message':              'Keen to move quickly on this.',
    'hp_field':              '',   # honeypot — must be empty on genuine submissions
}


class PricingPageTests(TestCase):

    def setUp(self):
        self.c = Client(SERVER_NAME='localhost')

    def test_pricing_page_200(self):
        r = self.c.get('/pricing/')
        self.assertEqual(r.status_code, 200)

    def test_pricing_page_shows_all_four_engagement_cards(self):
        r = self.c.get('/pricing/')
        content = r.content.decode()
        for title in ('Enterprise Diagnostic', '90-Day Enterprise Pilot', 'Enterprise Deployment', 'Annual Platform Licence'):
            self.assertIn(title, content)

    def test_pricing_page_shows_government_tiers(self):
        r = self.c.get('/pricing/')
        content = r.content.decode()
        for title in ('Government Pilot', 'First-Year Deployment', 'Multi-Year National'):
            self.assertIn(title, content)

    def test_pricing_page_shows_founding_partner_prices(self):
        r = self.c.get('/pricing/')
        content = r.content.decode()
        self.assertIn('£125,000', content)
        self.assertIn('From £85,000', content)

    def test_pricing_page_never_shows_buy_now(self):
        """PART: 'Do not show Buy now' — every CTA must be a proposal/discovery request."""
        r = self.c.get('/pricing/')
        self.assertNotIn('Buy now', r.content.decode())
        self.assertNotIn('Buy Now', r.content.decode())

    def test_pricing_page_addons_all_marked_custom_scope(self):
        r = self.c.get('/pricing/')
        content = r.content.decode()
        self.assertGreaterEqual(content.count('Custom scope'), 12)

    def test_pricing_page_ctas_link_to_enterprise_enquiry_with_engagement(self):
        r = self.c.get('/pricing/')
        content = r.content.decode()
        for engagement in (
            'enterprise_diagnostic', 'pilot_90day', 'enterprise_deployment',
            'annual_licence', 'government_sovereign', 'founding_partner',
        ):
            self.assertIn(f'/request-access/enterprise/?engagement={engagement}', content)


class EnterpriseEnquiryFormTests(TestCase):

    def setUp(self):
        self.c = Client(SERVER_NAME='localhost')

    def test_get_form_200(self):
        r = self.c.get(reverse('leads:enterprise_enquiry'))
        self.assertEqual(r.status_code, 200)

    def test_engagement_query_param_preselects_dropdown(self):
        r = self.c.get(reverse('leads:enterprise_enquiry') + '?engagement=founding_partner')
        self.assertEqual(r.context['form'].initial.get('preferred_engagement'), 'founding_partner')

    def test_valid_submission_redirects_to_success(self):
        r = self.c.post(reverse('leads:enterprise_enquiry'), VALID_ENTERPRISE_POST)
        self.assertRedirects(r, reverse('leads:enterprise_enquiry_success'), fetch_redirect_response=False)

    def test_valid_submission_creates_exactly_one_record(self):
        self.c.post(reverse('leads:enterprise_enquiry'), VALID_ENTERPRISE_POST)
        self.assertEqual(EnterpriseEnquiry.objects.count(), 1)

    def test_saved_object_contains_all_fields(self):
        self.c.post(reverse('leads:enterprise_enquiry'), VALID_ENTERPRISE_POST)
        obj = EnterpriseEnquiry.objects.get()
        self.assertEqual(obj.full_name, 'Sara Al Qasimi')
        self.assertEqual(obj.organisation, 'Gulf Horizon Investments')
        self.assertEqual(obj.work_email, 'sara@gulfhorizon.example')  # normalised lowercase
        self.assertEqual(obj.country, 'United Arab Emirates')
        self.assertEqual(obj.organisation_type, 'sovereign_wealth_fund')
        self.assertEqual(obj.preferred_engagement, 'pilot_90day')
        self.assertEqual(obj.estimated_assets, '35 portfolio companies')
        self.assertEqual(obj.status, 'new')

    def test_honeypot_prevents_record_creation(self):
        data = {**VALID_ENTERPRISE_POST, 'hp_field': 'http://spam.example'}
        r = self.c.post(reverse('leads:enterprise_enquiry'), data)
        self.assertRedirects(r, reverse('leads:enterprise_enquiry_success'), fetch_redirect_response=False)
        self.assertEqual(EnterpriseEnquiry.objects.count(), 0)

    def test_missing_required_field_shows_form_and_saves_nothing(self):
        data = {**VALID_ENTERPRISE_POST, 'full_name': ''}
        r = self.c.post(reverse('leads:enterprise_enquiry'), data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(EnterpriseEnquiry.objects.count(), 0)

    def test_missing_organisation_type_shows_form_and_saves_nothing(self):
        data = {**VALID_ENTERPRISE_POST, 'organisation_type': ''}
        r = self.c.post(reverse('leads:enterprise_enquiry'), data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(EnterpriseEnquiry.objects.count(), 0)

    def test_optional_fields_can_be_blank(self):
        data = {**VALID_ENTERPRISE_POST, 'estimated_assets': '', 'use_case': '', 'message': ''}
        r = self.c.post(reverse('leads:enterprise_enquiry'), data)
        self.assertRedirects(r, reverse('leads:enterprise_enquiry_success'), fetch_redirect_response=False)
        self.assertEqual(EnterpriseEnquiry.objects.count(), 1)

    def test_success_page_200(self):
        r = self.c.get(reverse('leads:enterprise_enquiry_success'))
        self.assertEqual(r.status_code, 200)

    def test_no_payment_language_anywhere_in_flow(self):
        """PART: never accept payment on the website."""
        for url in (reverse('leads:enterprise_enquiry'), reverse('leads:enterprise_enquiry_success')):
            content = self.c.get(url).content.decode()
            self.assertNotIn('Buy now', content)
            self.assertNotIn('checkout', content.lower())


class EnterpriseEnquiryRateLimitTests(TestCase):

    def setUp(self):
        self.c = Client(SERVER_NAME='localhost', REMOTE_ADDR='10.0.0.2')

    def test_rate_limit_after_five_submissions(self):
        """Sixth submission from the same IP within 1 hour should show rate_limited."""
        for _ in range(5):
            self.c.post(reverse('leads:enterprise_enquiry'), VALID_ENTERPRISE_POST)

        r = self.c.post(reverse('leads:enterprise_enquiry'), VALID_ENTERPRISE_POST)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context.get('rate_limited', False))
        # The 6th (blocked) attempt must not have created a 6th record.
        self.assertEqual(EnterpriseEnquiry.objects.count(), 5)


class EnterpriseEnquiryAdminTests(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.staff = User.objects.create_superuser('admin_enterprise', 'admin@example.com', 'pw123456')
        self.c = Client(SERVER_NAME='localhost')
        self.c.force_login(self.staff)
        self.enquiry = EnterpriseEnquiry.objects.create(
            full_name='Test Person', organisation='Test Org', work_email='test@example.com',
            country='United Kingdom', organisation_type='bank', preferred_engagement='enterprise_diagnostic',
        )

    def test_admin_changelist_loads(self):
        r = self.c.get('/admin/leads/enterpriseenquiry/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('Test Org', r.content.decode())

    def test_admin_change_page_loads(self):
        r = self.c.get(f'/admin/leads/enterpriseenquiry/{self.enquiry.pk}/change/')
        self.assertEqual(r.status_code, 200)
