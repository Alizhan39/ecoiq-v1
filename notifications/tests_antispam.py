"""
Tests for public-form abuse protection.

The incident these guard against: /contact/submit/ produced 937 AdminNotification
records between June and August, 924 of them from a single repeated contact name
with randomised free-mail addresses, because the endpoint had no captcha, no rate
limit, no honeypot and no email validation.

Cloudflare is always mocked — no test makes a network call.
"""
import time
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from notifications.antispam import Decision, evaluate, timing
from notifications.models import AdminNotification

VALID_MESSAGE = (
    'We are a UK manufacturer looking at ESG scoring for our supply chain '
    'and would like to discuss the methodology behind your company profiles.'
)


def turnstile_ok():
    return mock.patch('notifications.antispam.turnstile.verify',
                      return_value=mock.Mock(ok=True, code='ok', detail=''))


def turnstile_fail(code='invalid'):
    return mock.patch('notifications.antispam.turnstile.verify',
                      return_value=mock.Mock(ok=False, code=code, detail=''))


class AntispamTestCase(TestCase):
    """Each test gets clean rate-limit and duplicate counters."""

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        super().setUp()

    def post(self, **overrides):
        payload = {
            'name': 'Jane Smith',
            'email': 'jane@example.com',
            'subject': 'Methodology',
            'company': 'Acme Energy',
            'message': VALID_MESSAGE,
            'website': '',                       # honeypot, must stay empty
            'form_token': timing.issue(now=time.time() - 30),
            'cf-turnstile-response': 'test-token',
        }
        payload.update(overrides)
        return self.client.post(reverse('contact_submit'), payload)


class LegitimateSubmissionTests(AntispamTestCase):

    def test_valid_submission_creates_exactly_one_notification(self):
        with turnstile_ok():
            self.post()
        self.assertEqual(AdminNotification.objects.count(), 1)
        n = AdminNotification.objects.get()
        self.assertEqual(n.spam_status, 'accepted')
        self.assertEqual(n.source_endpoint, 'contact')
        self.assertEqual(n.risk_reasons, [])

    def test_free_mail_users_are_accepted(self):
        """gmail/outlook/yahoo carry no risk signal — real enquiries use them."""
        for i, domain in enumerate(('gmail.com', 'outlook.com', 'yahoo.com', 'hotmail.com')):
            cache.clear()
            with turnstile_ok():
                self.post(email=f'real.person{i}@{domain}',
                          message=VALID_MESSAGE + f' Reference {i}.')
        self.assertEqual(AdminNotification.objects.count(), 4)
        self.assertEqual(
            set(AdminNotification.objects.values_list('spam_status', flat=True)),
            {'accepted'})

    def test_accepted_submission_sends_the_team_email(self):
        with turnstile_ok():
            self.post()
        self.assertEqual(len(mail.outbox), 1)


class TurnstileTests(AntispamTestCase):

    def test_missing_token_creates_nothing(self):
        with turnstile_fail('missing'):
            self.post(**{'cf-turnstile-response': ''})
        self.assertEqual(AdminNotification.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_token_creates_nothing(self):
        with turnstile_fail('invalid'):
            self.post()
        self.assertEqual(AdminNotification.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_timeout_fails_closed(self):
        with turnstile_fail('unavailable'):
            self.post()
        self.assertEqual(AdminNotification.objects.count(), 0)

    @override_settings(TURNSTILE_SITE_KEY='', TURNSTILE_SECRET_KEY='', IS_PRODUCTION=True)
    def test_unconfigured_in_production_fails_closed(self):
        self.post()
        self.assertEqual(AdminNotification.objects.count(), 0)

    @override_settings(TURNSTILE_SITE_KEY='', TURNSTILE_SECRET_KEY='', IS_PRODUCTION=False)
    def test_unconfigured_in_development_passes_through(self):
        self.post()
        self.assertEqual(AdminNotification.objects.count(), 1)

    def test_verify_never_calls_the_network_without_configuration(self):
        from notifications.antispam import turnstile
        with mock.patch('requests.post') as posted:
            with override_settings(TURNSTILE_SITE_KEY='', TURNSTILE_SECRET_KEY='',
                                   IS_PRODUCTION=False):
                turnstile.verify('token')
        posted.assert_not_called()


class HoneypotAndTimingTests(AntispamTestCase):

    def test_filled_honeypot_creates_nothing(self):
        with turnstile_ok():
            self.post(website='http://spam.example')
        self.assertEqual(AdminNotification.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_submission_faster_than_a_human_is_not_accepted(self):
        with turnstile_ok():
            self.post(form_token=timing.issue(now=time.time()))
        self.assertFalse(
            AdminNotification.objects.filter(spam_status='accepted').exists())

    def test_forged_form_token_creates_nothing(self):
        with turnstile_ok():
            self.post(form_token='not-a-signed-token')
        self.assertEqual(AdminNotification.objects.count(), 0)

    def test_expired_form_is_not_accepted(self):
        ok, code = timing.check(timing.issue(now=time.time() - 60 * 60 * 24), max_seconds=60)
        self.assertFalse(ok)
        self.assertEqual(code, 'expired')


class RateLimitTests(AntispamTestCase):

    @override_settings(ANTISPAM_LIMITS={'ip': (2, 3600), 'email': (99, 86400),
                                        'message': (99, 86400), 'global': (999, 3600)})
    def test_ip_limit_returns_429(self):
        with turnstile_ok():
            for i in range(2):
                self.post(email=f'a{i}@example.com', message=VALID_MESSAGE + str(i))
            response = self.post(email='c@example.com', message=VALID_MESSAGE + 'z')
        self.assertEqual(response.status_code, 429)

    @override_settings(ANTISPAM_LIMITS={'ip': (99, 3600), 'email': (2, 86400),
                                        'message': (99, 86400), 'global': (999, 3600)})
    def test_same_email_limit_blocks_further_submissions(self):
        with turnstile_ok():
            for i in range(2):
                self.post(message=VALID_MESSAGE + f' variation {i}')
            self.post(message=VALID_MESSAGE + ' variation 3')
        self.assertEqual(AdminNotification.objects.filter(spam_status='accepted').count(), 2)

    @override_settings(ANTISPAM_LIMITS={'ip': (99, 3600), 'email': (99, 86400),
                                        'message': (99, 86400), 'global': (2, 3600)})
    def test_global_ceiling_applies(self):
        with turnstile_ok():
            for i in range(2):
                self.post(email=f'p{i}@example.com', message=VALID_MESSAGE + str(i))
            response = self.post(email='q@example.com', message=VALID_MESSAGE + 'q')
        self.assertEqual(response.status_code, 429)


class DuplicateTests(AntispamTestCase):

    def test_identical_resubmission_creates_only_one_notification(self):
        with turnstile_ok():
            self.post()
            self.post()
        self.assertEqual(AdminNotification.objects.count(), 1)

    def test_concurrent_duplicates_cannot_both_win(self):
        """
        cache.add is atomic, so only the first of two identical evaluations
        gets a clean verdict even when they interleave.
        """
        kwargs = dict(form='contact', name='Jane Smith', email='jane@example.com',
                      subject='Methodology', message=VALID_MESSAGE,
                      form_token=timing.issue(now=time.time() - 30),
                      turnstile_token='t')
        with turnstile_ok():
            first = evaluate(**kwargs)
            second = evaluate(**kwargs)
        self.assertIs(first.decision, Decision.ACCEPT)
        self.assertIsNot(second.decision, Decision.ACCEPT)
        self.assertIn('duplicate_submission', second.reason_codes)

    def test_fingerprint_excludes_the_raw_message(self):
        from notifications.antispam import submission_fingerprint
        secret_text = 'commercially confidential project codename'
        fp = submission_fingerprint(email='a@b.com', name='A', subject='S',
                                    message=secret_text, form='contact')
        self.assertNotIn(secret_text, fp)
        self.assertNotIn('confidential', fp)


class RejectedSubmissionsHaveNoSideEffectsTests(AntispamTestCase):

    def test_rejected_sends_no_email(self):
        with turnstile_fail():
            self.post()
        self.assertEqual(len(mail.outbox), 0)

    def test_rejected_dispatches_no_celery_task(self):
        with turnstile_fail(), mock.patch('celery.app.task.Task.delay') as delay:
            self.post()
        delay.assert_not_called()

    def test_rejected_makes_no_outbound_http_call(self):
        """No AI provider, no external API — nothing leaves the process."""
        with turnstile_fail(), mock.patch('requests.post') as post, \
                mock.patch('requests.get') as get:
            self.post()
        post.assert_not_called()
        get.assert_not_called()

    def test_rejected_response_does_not_reveal_detection(self):
        with turnstile_fail():
            response = self.post()
        self.assertEqual(response.status_code, 302)   # same redirect as success


class QuarantineTests(AntispamTestCase):

    def test_review_submission_is_quarantined_and_does_not_alert_the_team(self):
        with turnstile_ok():
            self.post(message='spam spam spam spam spam spam spam spam')
        notification = AdminNotification.objects.first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.spam_status, 'review')
        self.assertTrue(notification.is_quarantined)
        self.assertEqual(notification.priority, 'low')
        self.assertEqual(len(mail.outbox), 0)


class NoProtectedAttributeSignalsTests(TestCase):
    """The classifier must never key on identity characteristics."""

    def test_heuristics_module_has_no_identity_signals(self):
        """
        Scans executable code only. The module docstring states that these
        attributes are deliberately not used, so a raw text search would match
        that promise rather than a violation of it.
        """
        import ast
        import inspect

        from notifications.antispam import heuristics

        tree = ast.parse(inspect.getsource(heuristics))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                node.body = [n for n in node.body
                             if not (isinstance(n, ast.Expr)
                                     and isinstance(n.value, ast.Constant)
                                     and isinstance(n.value.value, str))]
        code = ast.unparse(tree).lower()
        for term in ('nationality', 'ethnic', 'religion', 'race', 'country_of_origin'):
            self.assertNotIn(term, code)

    def test_mainstream_providers_are_not_disposable(self):
        from notifications.antispam.heuristics import DISPOSABLE_DOMAINS
        for domain in ('gmail.com', 'outlook.com', 'hotmail.com', 'yahoo.com',
                       'aol.com', 'web.de', 'icloud.com'):
            self.assertNotIn(domain, DISPOSABLE_DOMAINS)


class LoggingHygieneTests(AntispamTestCase):

    def test_logs_contain_no_message_token_or_full_ip(self):
        secret_text = 'uniquephrasethatmustnotbelogged'
        with turnstile_fail(), self.assertLogs('notifications.antispam', level='INFO') as logs:
            self.post(message=secret_text * 3,
                      **{'cf-turnstile-response': 'supersecrettokenvalue'})
        blob = '\n'.join(logs.output)
        self.assertNotIn(secret_text, blob)
        self.assertNotIn('supersecrettokenvalue', blob)
        self.assertNotIn('127.0.0.1', blob)


class ManagementCommandTests(TestCase):

    def setUp(self):
        for i in range(6):
            AdminNotification.objects.create(
                title='Contact form — Offer', message='cheap deals http://a.example http://b.example http://c.example',
                source_type='contact', contact_name='Repeatedbot',
                contact_email=f'random{i}@example.com')
        AdminNotification.objects.create(
            title='Contact form — Methodology', message=VALID_MESSAGE,
            source_type='contact', contact_name='Real Person',
            contact_email='real@company.co.uk')

    def test_analysis_is_read_only(self):
        from io import StringIO

        from django.core.management import call_command
        before = list(AdminNotification.objects.values_list('id', 'spam_status', 'status'))
        out = StringIO()
        call_command('analyse_notification_spam', '--dry-run', stdout=out)
        after = list(AdminNotification.objects.values_list('id', 'spam_status', 'status'))
        self.assertEqual(before, after)
        self.assertIn('PROPOSED CLASSIFICATION', out.getvalue())

    def test_analysis_prints_no_message_bodies(self):
        from io import StringIO

        from django.core.management import call_command
        out = StringIO()
        call_command('analyse_notification_spam', stdout=out)
        self.assertNotIn('cheap deals', out.getvalue())
        self.assertNotIn(VALID_MESSAGE[:30], out.getvalue())

    def test_classification_requires_confirmation(self):
        from io import StringIO

        from django.core.management import call_command
        out = StringIO()
        call_command('classify_notification_spam', stdout=out)
        self.assertIn('DRY RUN', out.getvalue())
        self.assertEqual(
            AdminNotification.objects.exclude(spam_status='unclassified').count(), 0)

    def test_classification_with_confirm_never_deletes_and_is_reversible(self):
        from io import StringIO

        from django.core.management import call_command
        total_before = AdminNotification.objects.count()
        call_command('classify_notification_spam', '--confirm', stdout=StringIO())
        self.assertEqual(AdminNotification.objects.count(), total_before)
        self.assertTrue(AdminNotification.objects.filter(spam_status='rejected').exists())
        # The legitimate record must survive classification.
        legit = AdminNotification.objects.get(contact_name='Real Person')
        self.assertNotEqual(legit.spam_status, 'rejected')

        call_command('classify_notification_spam', '--rollback', '--confirm', stdout=StringIO())
        self.assertEqual(AdminNotification.objects.count(), total_before)
        self.assertEqual(
            AdminNotification.objects.filter(spam_status='rejected').count(), 0)
