"""Tests for the Admin Notification Hub: signal wiring, helper, admin, badge."""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from notifications.models import AdminNotification, create_notification


class CreateNotificationTests(TestCase):
    def test_helper_creates_unread_with_admin_url(self):
        from leads.models import AccessRequest
        ar = AccessRequest.objects.create(full_name='Jane', work_email='j@f.com', company='Acme')
        n = create_notification('Test', source_type='access_request', instance=ar)
        self.assertIsNotNone(n)
        self.assertEqual(n.status, 'unread')
        self.assertEqual(n.source_model, 'leads.accessrequest')
        self.assertIn(str(ar.pk), n.admin_url)

    def test_unread_count(self):
        AdminNotification.objects.create(title='a', status='unread')
        AdminNotification.objects.create(title='b', status='read')
        self.assertEqual(AdminNotification.unread_count(), 1)


class SignalWiringTests(TestCase):
    """Creating a lead auto-creates exactly one notification."""

    def test_access_request_creates_notification(self):
        from leads.models import AccessRequest
        AccessRequest.objects.create(full_name='Jane', work_email='j@f.com', company='Acme')
        self.assertEqual(AdminNotification.objects.filter(source_type='access_request').count(), 1)

    def test_heating_household_vs_akimat_routing(self):
        from heating.models import HeatingApplication
        HeatingApplication.objects.create(full_name='H', lead_type='household')
        HeatingApplication.objects.create(full_name='A', lead_type='akimat', organisation='Akimat')
        self.assertEqual(AdminNotification.objects.filter(source_type='heating_household').count(), 1)
        self.assertEqual(AdminNotification.objects.filter(source_type='heating_akimat').count(), 1)

    def test_company_sponsorship_creates_notification(self):
        from heating.models import CompanySponsorshipLead
        CompanySponsorshipLead.objects.create(company_name='C', contact_name='X', email='x@c.com')
        self.assertEqual(AdminNotification.objects.filter(source_type='heating_company').count(), 1)

    def test_home_assessment_creates_notification(self):
        from heating.models import HomeAssessment
        HomeAssessment.objects.create(area_m2=100, recommended_kw=10)
        self.assertEqual(AdminNotification.objects.filter(source_type='home_assessment').count(), 1)

    def test_update_does_not_create_second_notification(self):
        from leads.models import AccessRequest
        ar = AccessRequest.objects.create(full_name='Jane', work_email='j@f.com', company='Acme')
        ar.status = 'reviewed'
        ar.save()
        self.assertEqual(AdminNotification.objects.filter(source_type='access_request').count(), 1)


class AdminAccessTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('s', password='x', is_staff=True, is_superuser=True)
        self.client.force_login(self.staff)

    def test_notifications_changelist_loads(self):
        AdminNotification.objects.create(title='hello', status='unread')
        r = self.client.get(reverse('admin:notifications_adminnotification_changelist'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'hello')

    def test_header_badge_shows_unread_count(self):
        AdminNotification.objects.create(title='x', status='unread')
        r = self.client.get(reverse('admin:index'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '🔔 Notifications')

    def test_mark_read_action(self):
        n = AdminNotification.objects.create(title='x', status='unread')
        url = reverse('admin:notifications_adminnotification_changelist')
        self.client.post(url, {'action': 'mark_read', '_selected_action': [n.pk]})
        n.refresh_from_db()
        self.assertEqual(n.status, 'read')

    def test_archive_action(self):
        n = AdminNotification.objects.create(title='x', status='unread')
        url = reverse('admin:notifications_adminnotification_changelist')
        self.client.post(url, {'action': 'archive', '_selected_action': [n.pk]})
        n.refresh_from_db()
        self.assertEqual(n.status, 'archived')

    def test_opening_detail_marks_read(self):
        n = AdminNotification.objects.create(title='x', status='unread')
        self.client.get(reverse('admin:notifications_adminnotification_change', args=[n.pk]))
        n.refresh_from_db()
        self.assertEqual(n.status, 'read')

    def test_non_staff_cannot_access(self):
        self.client.logout()
        User.objects.create_user('u', password='x', is_staff=False)
        self.client.login(username='u', password='x')
        r = self.client.get(reverse('admin:notifications_adminnotification_changelist'))
        self.assertEqual(r.status_code, 302)  # admin redirects non-staff to login


class FormSubmissionNotificationTests(TestCase):
    """
    End-to-end guarantee: every public lead/form submission creates EXACTLY ONE
    unread AdminNotification. Hits the real view endpoints (not just model.save).
    """

    def setUp(self):
        self.c = Client(SERVER_NAME='localhost')

    def _assert_one(self, source_type, path, data):
        before = AdminNotification.objects.count()
        self.c.post(path, data)
        created = AdminNotification.objects.count() - before
        self.assertEqual(created, 1, msg=f'{path} should create exactly 1 notification, got {created}')
        n = AdminNotification.objects.order_by('-id').first()
        self.assertEqual(n.source_type, source_type)
        self.assertEqual(n.status, 'unread')

    def test_request_access_form(self):
        self._assert_one('access_request', '/request-access/', dict(
            full_name='Jane Investor', work_email='j@f.com', company='Acme Capital',
            target_entity='KazMunayGas', sector='Oil', role='investor',
            product_interest='readiness_report', message=''))

    def test_heating_household_form(self):
        self._assert_one('heating_household', '/heating/pilot-application/', {
            'form_type': 'household', 'hh-full_name': 'Bauyrzhan',
            'hh-phone': '+77001112233', 'hh-location': 'Almaty', 'hh-message': 'Need heating'})

    def test_heating_akimat_partnership_form(self):
        self._assert_one('heating_akimat', '/heating/pilot-application/', {
            'form_type': 'akimat', 'ak-organisation': 'Almaty Akimat',
            'ak-full_name': 'Official', 'ak-email': 'gov@akimat.kz', 'ak-location': 'Almaty'})

    def test_company_sponsorship_form(self):
        self._assert_one('heating_company', '/heating/company-sponsorship/', dict(
            company_name='GreenCorp', contact_name='CSR Lead', email='csr@green.com',
            package='sponsor_10', message='Interested'))

    def test_home_assessment_form(self):
        self._assert_one('home_assessment', '/heating/calculator/', dict(
            area_m2=100, insulation='medium', rooms=4, has_radiators='yes',
            electricity='220', available_kw='8', package='assisted', install_type='assisted'))

    def test_contact_form(self):
        self._assert_one('contact', '/contact/submit/', dict(
            name='Visitor', email='v@x.com', subject='Partnership', company='X',
            message='This is a message longer than twenty chars.'))
