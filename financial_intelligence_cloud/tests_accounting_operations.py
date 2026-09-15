from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from financial_intelligence_cloud.models import (
    AccountingActivity, AccountingService, ClientPayment, ClientReminder, ClientService,
    PaymentReceipt,
)
from financial_intelligence_cloud.services.accounts import (
    add_portfolio_entity, create_institutional_account, create_portfolio,
)


class AccountingOperationsTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username='case.manager', password='test-pass', is_staff=True,
        )
        self.regular_user = get_user_model().objects.create_user(
            username='client.user', password='test-pass',
        )
        self.account = create_institutional_account(
            'northstar-ops', 'Northstar Ops', 'accounting_firm', is_demo=False,
        )
        portfolio = create_portfolio(self.account, 'Client book', 'client_book')
        self.client_entity = add_portfolio_entity(portfolio, 'Client One Ltd', 'sme_client')
        self.service = AccountingService.objects.create(
            institutional_account=self.account, name='Annual Accounts', code='annual-accounts',
            default_fee=Decimal('1200.00'), frequency='annual',
        )
        self.engagement = ClientService.objects.create(
            client=self.client_entity, service=self.service, assigned_to=self.staff,
            agreed_fee=Decimal('1200.00'), next_due_date=timezone.localdate() + timedelta(days=14),
        )

    def test_dashboard_is_staff_only(self):
        url = reverse('financial_intelligence_cloud:accounting_operations')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.regular_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_dashboard_shows_due_reminders_and_overdue_balance(self):
        ClientReminder.objects.create(
            client_service=self.engagement, owner=self.staff, title='Request bank statements',
            due_at=timezone.now() - timedelta(hours=1), priority='urgent',
        )
        ClientPayment.objects.create(
            client_service=self.engagement, amount_due=Decimal('1200.00'),
            amount_paid=Decimal('200.00'), due_date=timezone.localdate() - timedelta(days=2),
            status='part_paid',
        )
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse('financial_intelligence_cloud:accounting_operations'),
            {'account': self.account.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Request bank statements')
        self.assertContains(response, '1,000.00')
        self.assertContains(response, 'Client One Ltd')
        self.assertContains(response, 'Accounting Ops')

    def test_record_partial_then_full_payment_and_append_activity(self):
        payment = ClientPayment.objects.create(
            client_service=self.engagement, amount_due=Decimal('1000.00'),
            due_date=timezone.localdate(),
        )
        self.client.force_login(self.staff)
        url = reverse('financial_intelligence_cloud:record_client_payment', args=[payment.pk])
        self.client.post(url, {'amount_received': '250.00', 'reference': 'BANK-1'})
        payment.refresh_from_db()
        self.assertEqual(payment.amount_paid, Decimal('250.00'))
        self.assertEqual(payment.status, 'part_paid')

        self.client.post(url, {'amount_received': '750.00', 'reference': 'BANK-2'})
        payment.refresh_from_db()
        self.assertEqual(payment.amount_paid, Decimal('1000.00'))
        self.assertEqual(payment.status, 'paid')
        self.assertIsNotNone(payment.paid_at)
        self.assertEqual(list(payment.receipts.values_list('amount', flat=True)), [Decimal('750.00'), Decimal('250.00')])
        self.assertEqual(
            AccountingActivity.objects.filter(event_type='payment_received', client=self.client_entity).count(), 2,
        )

    def test_overpayment_is_rejected(self):
        payment = ClientPayment.objects.create(
            client_service=self.engagement, amount_due=Decimal('100.00'),
            due_date=timezone.localdate(),
        )
        self.client.force_login(self.staff)
        self.client.post(
            reverse('financial_intelligence_cloud:record_client_payment', args=[payment.pk]),
            {'amount_received': '101.00'},
        )
        payment.refresh_from_db()
        self.assertEqual(payment.amount_paid, Decimal('0.00'))
        self.assertEqual(payment.status, 'due')

    def test_reminder_can_be_completed_without_background_worker(self):
        reminder = ClientReminder.objects.create(
            client=self.client_entity, owner=self.staff, title='Call client',
            due_at=timezone.now(),
        )
        self.client.force_login(self.staff)
        self.client.post(
            reverse('financial_intelligence_cloud:update_accounting_reminder', args=[reminder.pk]),
            {'action': 'done'},
        )
        reminder.refresh_from_db()
        self.assertEqual(reminder.status, 'done')
        self.assertIsNotNone(reminder.completed_at)

    def test_forms_cannot_cross_account_boundaries(self):
        other = create_institutional_account('other-firm', 'Other Firm', 'accounting_firm', is_demo=False)
        other_portfolio = create_portfolio(other, 'Other clients', 'client_book')
        other_client = add_portfolio_entity(other_portfolio, 'Other Client Ltd', 'sme_client')
        self.client.force_login(self.staff)
        self.client.post(reverse('financial_intelligence_cloud:add_client_service'), {
            'account': self.account.pk,
            'client': other_client.pk,
            'service': self.service.pk,
            'status': 'active',
            'start_date': str(timezone.localdate()),
            'currency': 'GBP',
        })
        self.assertFalse(ClientService.objects.filter(client=other_client, service=self.service).exists())

    def test_activity_history_cannot_be_edited_or_deleted(self):
        activity = AccountingActivity.objects.create(
            institutional_account=self.account, client=self.client_entity,
            actor=self.staff, event_type='note', summary='Original event',
        )
        activity.summary = 'Rewritten event'
        with self.assertRaises(ValidationError):
            activity.save()
        with self.assertRaises(ValidationError):
            activity.delete()
