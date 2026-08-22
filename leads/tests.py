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

    def test_pricing_is_the_react_page(self):
        self.assertIn('id="root"', self.c.get('/pricing/').content.decode())

    def test_the_pricing_page_publishes_no_price(self):
        """
        The page this replaces published four bands — £15,000 to £400,000 —
        plus government tiers and a founding-partner price, for engagements
        that have never been sold. EcoIQ has not delivered a commercial
        engagement, so any figure would be an asking price presented as a going
        rate.

        Asserted on the served document. The React page's own copy is asserted
        in frontend/web/src/pages/Pricing.test.tsx.
        """
        import re

        content = self.c.get('/pricing/').content.decode()
        self.assertIsNone(re.search(r'[£$€]\s?\d', content))

    def test_pricing_page_never_shows_buy_now(self):
        """PART: 'Do not show Buy now' — every CTA is a proposal request."""
        content = self.c.get('/pricing/').content.decode()
        self.assertNotIn('Buy now', content)
        self.assertNotIn('Buy Now', content)

    def test_the_enterprise_enquiry_funnel_still_accepts_every_engagement(self):
        """
        The pricing CTAs still feed leads.EnterpriseEnquiry with the engagement
        pre-selected. The links live in the React bundle now, so what is
        asserted here is the half this app owns: that every key those links use
        is still one the form understands.

        A key that stopped resolving would send that segment into a generic
        enquiry with no error anywhere.
        """
        for engagement in (
            'enterprise_diagnostic', 'pilot_90day', 'enterprise_deployment',
            'annual_licence', 'government_sovereign', 'founding_partner',
        ):
            with self.subTest(engagement=engagement):
                response = self.c.get(
                    reverse('leads:enterprise_enquiry')
                    + f'?engagement={engagement}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.context['form'].initial.get(
                        'preferred_engagement'),
                    engagement)


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


# ── InvestorEnquiry (GCC investor pages) ─────────────────────────────────────

from .models import InvestorEnquiry

VALID_INVESTOR_POST = {
    'full_name':             'Fatima Al Thani',
    'organisation':          'Doha Capital Partners',
    'job_title':              'Head of Investments',
    'work_email':             'Fatima@DohaCapital.example',
    'phone_whatsapp':         '+974 5555 1234',
    'country':                'Qatar',
    'organisation_type':      'vc_fund',
    'type_of_interest':       'strategic_investment',
    'engagement_range':       '500k_2m',
    'main_area_of_interest':  'GCC market entry',
    'message':                'Keen to learn more.',
    'consent':                'on',
    'source_page':            '/qatar/investors/',
    'source_country':         'qatar',
    'utm_source':             'linkedin',
    'utm_medium':             'social',
    'utm_campaign':           'gcc-launch',
    'utm_content':            '',
    'utm_term':               '',
    'hp_field':               '',   # honeypot — must be empty on genuine submissions
}


class InvestorEnquiryFormTests(TestCase):

    def setUp(self):
        self.c = Client(SERVER_NAME='localhost')

    def test_get_form_200(self):
        r = self.c.get(reverse('leads:investor_enquiry'))
        self.assertEqual(r.status_code, 200)

    def test_interest_query_param_preselects_dropdown(self):
        r = self.c.get(reverse('leads:investor_enquiry') + '?interest=founding_partner')
        self.assertEqual(r.context['form'].initial.get('type_of_interest'), 'founding_partner')

    def test_attribution_query_params_populate_hidden_fields(self):
        r = self.c.get(
            reverse('leads:investor_enquiry')
            + '?source_country=qatar&source_page=/qatar/investors/&utm_source=linkedin&utm_campaign=gcc-launch'
        )
        initial = r.context['form'].initial
        self.assertEqual(initial.get('source_country'), 'qatar')
        self.assertEqual(initial.get('source_page'), '/qatar/investors/')
        self.assertEqual(initial.get('utm_source'), 'linkedin')
        self.assertEqual(initial.get('utm_campaign'), 'gcc-launch')

    def test_lang_ar_renders_arabic_rtl(self):
        r = self.c.get(reverse('leads:investor_enquiry') + '?lang=ar')
        content = r.content.decode()
        self.assertIn('dir="rtl"', content)
        self.assertIn('اطلب عرضاً للمستثمرين', content)

    def test_valid_submission_redirects_to_success(self):
        r = self.c.post(reverse('leads:investor_enquiry'), VALID_INVESTOR_POST)
        self.assertRedirects(r, reverse('leads:investor_enquiry_success'), fetch_redirect_response=False)

    def test_valid_submission_creates_exactly_one_record(self):
        self.c.post(reverse('leads:investor_enquiry'), VALID_INVESTOR_POST)
        self.assertEqual(InvestorEnquiry.objects.count(), 1)

    def test_saved_object_contains_all_fields_including_attribution(self):
        self.c.post(reverse('leads:investor_enquiry'), VALID_INVESTOR_POST)
        obj = InvestorEnquiry.objects.get()
        self.assertEqual(obj.full_name, 'Fatima Al Thani')
        self.assertEqual(obj.organisation, 'Doha Capital Partners')
        self.assertEqual(obj.work_email, 'fatima@dohacapital.example')  # normalised lowercase
        self.assertEqual(obj.organisation_type, 'vc_fund')
        self.assertEqual(obj.type_of_interest, 'strategic_investment')
        self.assertEqual(obj.engagement_range, '500k_2m')
        self.assertTrue(obj.consent)
        # UTM + source preserved end-to-end (spec: "preserve UTM parameters
        # and record the source page and source country").
        self.assertEqual(obj.source_page, '/qatar/investors/')
        self.assertEqual(obj.source_country, 'qatar')
        self.assertEqual(obj.utm_source, 'linkedin')
        self.assertEqual(obj.utm_medium, 'social')
        self.assertEqual(obj.utm_campaign, 'gcc-launch')
        self.assertEqual(obj.status, 'new')

    def test_honeypot_prevents_record_creation(self):
        data = {**VALID_INVESTOR_POST, 'hp_field': 'http://spam.example'}
        r = self.c.post(reverse('leads:investor_enquiry'), data)
        self.assertRedirects(r, reverse('leads:investor_enquiry_success'), fetch_redirect_response=False)
        self.assertEqual(InvestorEnquiry.objects.count(), 0)

    def test_missing_required_field_shows_form_and_saves_nothing(self):
        data = {**VALID_INVESTOR_POST, 'full_name': ''}
        r = self.c.post(reverse('leads:investor_enquiry'), data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(InvestorEnquiry.objects.count(), 0)

    def test_missing_consent_shows_form_and_saves_nothing(self):
        """PART E: consent checkbox is required."""
        data = {**VALID_INVESTOR_POST, 'consent': ''}
        r = self.c.post(reverse('leads:investor_enquiry'), data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(InvestorEnquiry.objects.count(), 0)

    def test_optional_fields_can_be_blank(self):
        data = {**VALID_INVESTOR_POST, 'job_title': '', 'phone_whatsapp': '', 'engagement_range': '',
                 'main_area_of_interest': '', 'message': ''}
        r = self.c.post(reverse('leads:investor_enquiry'), data)
        self.assertRedirects(r, reverse('leads:investor_enquiry_success'), fetch_redirect_response=False)
        self.assertEqual(InvestorEnquiry.objects.count(), 1)

    def test_success_page_200(self):
        r = self.c.get(reverse('leads:investor_enquiry_success'))
        self.assertEqual(r.status_code, 200)

    def test_no_payment_or_buy_now_language_anywhere_in_flow(self):
        """PART E/F: never accept payment, never show 'Buy now'."""
        for url in (reverse('leads:investor_enquiry'), reverse('leads:investor_enquiry_success')):
            content = self.c.get(url).content.decode()
            self.assertNotIn('Buy now', content)
            self.assertNotIn('Invest now', content)
            self.assertNotIn('checkout', content.lower())

    def test_legal_notice_present(self):
        """PART F: the investor legal notice must appear near the form."""
        content = self.c.get(reverse('leads:investor_enquiry')).content.decode()
        self.assertIn('does not constitute an offer of securities', content)

    def test_csrf_protected(self):
        """PART: server-side CSRF protection must actually be enforced (item E)."""
        csrf_client = Client(SERVER_NAME='localhost', enforce_csrf_checks=True)
        r = csrf_client.post(reverse('leads:investor_enquiry'), VALID_INVESTOR_POST)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(InvestorEnquiry.objects.count(), 0)


class InvestorEnquiryRateLimitTests(TestCase):

    def setUp(self):
        self.c = Client(SERVER_NAME='localhost', REMOTE_ADDR='10.0.0.3')

    def test_rate_limit_after_five_submissions(self):
        """Sixth submission from the same IP within 1 hour should show rate_limited."""
        for _ in range(5):
            self.c.post(reverse('leads:investor_enquiry'), VALID_INVESTOR_POST)

        r = self.c.post(reverse('leads:investor_enquiry'), VALID_INVESTOR_POST)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context.get('rate_limited', False))
        self.assertEqual(InvestorEnquiry.objects.count(), 5)


class InvestorEnquiryAdminTests(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.staff = User.objects.create_superuser('admin_investor', 'admin_investor@example.com', 'pw123456')
        self.c = Client(SERVER_NAME='localhost')
        self.c.force_login(self.staff)
        self.enquiry = InvestorEnquiry.objects.create(
            full_name='Test Investor', organisation='Test Fund', work_email='test@example.com',
            country='Kuwait', organisation_type='family_office', type_of_interest='enterprise_pilot',
            consent=True, source_country='kuwait',
        )

    def test_admin_changelist_loads(self):
        r = self.c.get('/admin/leads/investorenquiry/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('Test Fund', r.content.decode())

    def test_admin_change_page_loads(self):
        r = self.c.get(f'/admin/leads/investorenquiry/{self.enquiry.pk}/change/')
        self.assertEqual(r.status_code, 200)


# ── Analytics: investor_form_start + language switch on the enquiry form ───

import re


def _script_block(content, script_id):
    """Extract the contents of <script id="script_id">...</script>, or '' if absent."""
    m = re.search(rf'<script id="{re.escape(script_id)}"[^>]*>(.*?)</script>', content, re.S)
    return m.group(1) if m else ''


# NOTE: 'organisation' is deliberately excluded — 'organisation_type' (a safe
# enum choice, not the free-text org name) is an allowed analytics param and
# would false-positive on a bare substring check. The org NAME is instead
# checked by value in test_conversion_event_never_contains_pii.
_PII_MARKERS = ('full_name', 'work_email', 'phone_whatsapp', 'message', 'job_title')


class InvestorFormStartEventTests(TestCase):

    def setUp(self):
        self.c = Client(SERVER_NAME='localhost')

    def test_form_start_marker_present_once(self):
        content = self.c.get(reverse('leads:investor_enquiry')).content.decode()
        self.assertEqual(content.count('id="ecoiq-analytics-form-events"'), 1)
        self.assertIn('investor_form_start', content)

    def test_form_start_carries_source_country_not_pii(self):
        content = self.c.get(
            reverse('leads:investor_enquiry') + '?source_country=qatar&source_page=/qatar/investors/'
        ).content.decode()
        block = _script_block(content, 'ecoiq-analytics-form-events')
        self.assertIn('qatar', block)
        for marker in _PII_MARKERS:
            self.assertNotIn(marker, block)

    def test_language_switch_marker_present_on_both_languages(self):
        en_content = self.c.get(reverse('leads:investor_enquiry')).content.decode()
        self.assertEqual(en_content.count('data-eq-event="investor_language_switch"'), 1)
        self.assertIn('data-eq-from="en"', en_content)
        self.assertIn('data-eq-to="ar"', en_content)

        ar_content = self.c.get(reverse('leads:investor_enquiry') + '?lang=ar').content.decode()
        self.assertEqual(ar_content.count('data-eq-event="investor_language_switch"'), 1)
        self.assertIn('data-eq-from="ar"', ar_content)
        self.assertIn('data-eq-to="en"', ar_content)


# ── Analytics: investor_form_submit conversion event ───────────────────────

class InvestorConversionEventTests(TestCase):

    def setUp(self):
        self.c = Client(SERVER_NAME='localhost')

    def test_conversion_event_absent_on_direct_visit(self):
        """Bookmarking/visiting the success URL directly must never register
        as a conversion — only a real POST->redirect sets the session flag."""
        content = self.c.get(reverse('leads:investor_enquiry_success')).content.decode()
        self.assertNotIn('investor_form_submit', content)
        self.assertNotIn('id="ecoiq-analytics-conversion"', content)

    def test_conversion_event_present_once_after_real_submission(self):
        r = self.c.post(reverse('leads:investor_enquiry'), VALID_INVESTOR_POST, follow=True)
        content = r.content.decode()
        self.assertEqual(content.count('id="ecoiq-analytics-conversion"'), 1)
        self.assertEqual(content.count('investor_form_submit'), 1)

    def test_conversion_event_carries_correct_non_pii_fields(self):
        r = self.c.post(reverse('leads:investor_enquiry'), VALID_INVESTOR_POST, follow=True)
        block = _script_block(r.content.decode(), 'ecoiq-analytics-conversion')
        self.assertIn("source_country_page: 'qatar'", block)
        self.assertIn("organisation_type: 'vc_fund'", block)
        self.assertIn("type_of_interest: 'strategic_investment'", block)
        self.assertIn("utm_source: 'linkedin'", block)
        self.assertIn("utm_medium: 'social'", block)
        self.assertIn("landing_page: '/qatar/investors/'", block)
        # utm_campaign='gcc-launch' — the hyphen is escapejs-encoded, so match loosely.
        self.assertIn('utm_campaign', block)

    def test_conversion_event_never_contains_pii(self):
        r = self.c.post(reverse('leads:investor_enquiry'), VALID_INVESTOR_POST, follow=True)
        block = _script_block(r.content.decode(), 'ecoiq-analytics-conversion')
        self.assertNotIn('Fatima', block)
        self.assertNotIn('Doha Capital Partners', block)
        self.assertNotIn('DohaCapital.example', block)
        self.assertNotIn('5555', block)  # phone number fragment
        self.assertNotIn('Keen to learn more', block)  # message text
        for marker in _PII_MARKERS:
            self.assertNotIn(marker, block)

    def test_refreshing_success_page_does_not_refire_conversion(self):
        """The session key is popped on first read, so a manual reload of the
        success page must not double-count the conversion."""
        self.c.post(reverse('leads:investor_enquiry'), VALID_INVESTOR_POST, follow=True)
        second_visit = self.c.get(reverse('leads:investor_enquiry_success')).content.decode()
        self.assertNotIn('investor_form_submit', second_visit)

    def test_full_name_and_email_never_appear_anywhere_on_success_page(self):
        """Belt-and-braces: the success page template never surfaces these
        fields at all, analytics block or otherwise."""
        r = self.c.post(reverse('leads:investor_enquiry'), VALID_INVESTOR_POST, follow=True)
        content = r.content.decode()
        self.assertNotIn('Fatima Al Thani', content)
        self.assertNotIn('Fatima@DohaCapital.example', content)
        self.assertNotIn('fatima@dohacapital.example', content)


# ── Staff-only investor enquiry reporting dashboard ─────────────────────────

class InvestorEnquiryReportViewTests(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.staff = User.objects.create_user(
            username='report_staff', password='x', email='staff@ecoiq.uk', is_staff=True,
        )
        self.normal = User.objects.create_user(
            username='report_normal', password='x', email='user@example.com', is_staff=False,
        )
        self.url = reverse('leads:investor_enquiry_report')

        InvestorEnquiry.objects.create(
            full_name='A', organisation='Org A', work_email='a@example.com', country='Qatar',
            organisation_type='vc_fund', type_of_interest='strategic_investment',
            consent=True, source_country='qatar', source_page='/qatar/investors/',
            utm_campaign='gcc-launch',
        )
        InvestorEnquiry.objects.create(
            full_name='B', organisation='Org B', work_email='b@example.com', country='Kuwait',
            organisation_type='family_office', type_of_interest='enterprise_pilot',
            consent=True, source_country='kuwait', source_page='/kuwait/investors/',
        )
        InvestorEnquiry.objects.create(
            full_name='C', organisation='Org C', work_email='c@example.com', country='Qatar',
            organisation_type='vc_fund', type_of_interest='strategic_investment',
            consent=True, source_country='qatar', source_page='/qatar/investors/',
            utm_campaign='gcc-launch',
        )

    def test_staff_can_access_report(self):
        self.client.force_login(self.staff)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'leads/investor_enquiry_report.html')

    def test_non_staff_redirected_to_login(self):
        self.client.force_login(self.normal)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])

    def test_anonymous_redirected_to_login(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])

    def test_totals_correct(self):
        self.client.force_login(self.staff)
        r = self.client.get(self.url)
        self.assertEqual(r.context['total_conversions'], 3)

    def test_breakdown_by_country_correct(self):
        self.client.force_login(self.staff)
        r = self.client.get(self.url)
        by_country = {row['key']: row['total'] for row in r.context['by_country']}
        self.assertEqual(by_country['qatar'], 2)
        self.assertEqual(by_country['kuwait'], 1)

    def test_breakdown_by_utm_campaign_correct(self):
        self.client.force_login(self.staff)
        r = self.client.get(self.url)
        by_campaign = {row['utm_campaign']: row['total'] for row in r.context['by_utm_campaign']}
        self.assertEqual(by_campaign['gcc-launch'], 2)

    def test_report_page_not_indexed(self):
        self.client.force_login(self.staff)
        content = self.client.get(self.url).content.decode()
        self.assertIn('noindex', content)
