"""
api/tests_v2_contact.py — the JSON contact endpoint is not a second, unguarded
door into the same room.

`core.views.contact_submit` produced 100% of the 937 admin notifications in the
June–August abuse incident because it had no captcha, no rate limit, no
honeypot and no email validation while the leads/ forms had all four. Adding a
JSON endpoint for the same form is the obvious way to reintroduce exactly that.

So these tests assert the SCREENING, not just the happy path: that a filled
honeypot creates nothing, that a missing form token creates nothing, that a
rejected submission is indistinguishable from an accepted one, and that no
email leaves the process in either case.
"""
from __future__ import annotations

import time
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings

from notifications.antispam import timing as _timing

URL = '/api/v2/contact/'


def valid_token() -> str:
    """
    A token issued ten seconds ago.

    Back-dated deliberately: the engine rejects anything submitted within three
    seconds of the form rendering, and a test that issues and posts in the same
    millisecond is testing the timing check rather than the endpoint.
    """
    return _timing.issue(now=time.time() - 10)


def payload(**overrides) -> dict:
    body = {
        'name': 'Ada Lovelace',
        'email': 'ada@example.com',
        'subject': 'Assessment enquiry',
        'company': 'Analytical Engines',
        'message': 'We would like to discuss an assessment of our estate.',
        'website': '',
        'form_token': valid_token(),
        'turnstile_token': '',
    }
    body.update(overrides)
    return body


def notifications_count() -> int:
    from notifications.models import AdminNotification
    return AdminNotification.objects.count()


class ContactFormContextTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_get_returns_the_antiabuse_context(self):
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form_token', response.json())
        self.assertIn('turnstile_site_key', response.json())

    def test_each_request_gets_a_fresh_token(self):
        """
        Issued per request, not baked into the shell.

        A token embedded in the served document would be the same age for every
        visitor who received that copy of it — which is precisely the signal it
        exists to measure.
        """
        first = self.client.get(URL).json()['form_token']
        second = self.client.get(URL, HTTP_X_TEST='2').json()['form_token']
        self.assertTrue(first and second)
        # Signed payloads differ per issue even at the same second.
        self.assertEqual(_timing.check(first)[1], 'too_fast')

    @override_settings(TURNSTILE_SITE_KEY='0xTESTKEY')
    def test_the_site_key_is_the_public_one(self):
        response = self.client.get(URL)
        self.assertEqual(response.json()['turnstile_site_key'], '0xTESTKEY')

    def test_the_secret_key_is_never_returned(self):
        with override_settings(TURNSTILE_SECRET_KEY='super-secret-value'):
            body = self.client.get(URL).content.decode()
        self.assertNotIn('super-secret-value', body)


class ContactValidationTests(TestCase):
    def setUp(self):
        cache.clear()

    def post(self, **overrides):
        return self.client.post(URL, data=payload(**overrides),
                                content_type='application/json')

    def test_a_valid_enquiry_is_accepted(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'received')

    def test_missing_name_is_reported_against_the_field(self):
        response = self.post(name='')
        self.assertEqual(response.status_code, 400)
        self.assertIn('name', response.json()['errors'])

    def test_invalid_email_is_reported_against_the_field(self):
        response = self.post(email='not-an-address')
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json()['errors'])

    def test_a_too_short_message_is_rejected(self):
        response = self.post(message='hi')
        self.assertEqual(response.status_code, 400)
        self.assertIn('message', response.json()['errors'])

    def test_validation_failure_creates_nothing(self):
        before = notifications_count()
        self.post(message='hi')
        self.assertEqual(notifications_count(), before)
        self.assertEqual(len(mail.outbox), 0)

    def test_oversized_fields_are_truncated_not_rejected(self):
        """
        A message one character over the limit is a real enquiry. Bouncing it
        teaches the sender nothing.
        """
        response = self.post(message='x' * 6000)
        self.assertEqual(response.status_code, 200)


class ContactScreeningTests(TestCase):
    """The part that must never regress."""

    def setUp(self):
        cache.clear()
        mail.outbox = []

    def post(self, **overrides):
        return self.client.post(URL, data=payload(**overrides),
                                content_type='application/json')

    def test_a_filled_honeypot_creates_nothing(self):
        before = notifications_count()
        response = self.post(website='http://spam.example')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(notifications_count(), before,
                         'A rejected submission wrote to the notification '
                         'table. The screening must run BEFORE any side effect.')
        self.assertEqual(len(mail.outbox), 0)

    def test_a_filled_honeypot_is_told_it_succeeded(self):
        """
        Identical wording to the accepted path. A bot that can tell it was
        caught can iterate until it isn't.
        """
        rejected = self.post(website='http://spam.example').json()
        cache.clear()
        accepted = self.post(email='someone-else@example.com').json()
        self.assertEqual(rejected['detail'], accepted['detail'])
        self.assertEqual(rejected['status'], accepted['status'])

    def test_a_missing_form_token_creates_nothing(self):
        before = notifications_count()
        self.post(form_token='')
        self.assertEqual(notifications_count(), before)
        self.assertEqual(len(mail.outbox), 0)

    def test_a_forged_form_token_creates_nothing(self):
        before = notifications_count()
        self.post(form_token='not.a.signed.token')
        self.assertEqual(notifications_count(), before)

    def test_a_submission_that_arrives_too_fast_is_quarantined_not_dropped(self):
        """
        FORM_TOO_FAST is a SOFT signal, deliberately — a real person using a
        password manager and a saved snippet can trip it. So the submission is
        recorded for review rather than discarded, and never alerts the
        commercial team.

        Asserted here because the JSON endpoint must reproduce the same
        judgement as the form it replaces, not a stricter or looser one.
        """
        from notifications.models import AdminNotification

        before = notifications_count()
        self.post(form_token=_timing.issue())     # issued right now
        self.assertEqual(notifications_count(), before + 1)
        self.assertEqual(
            AdminNotification.objects.latest('id').spam_status, 'review')
        self.assertEqual(len(mail.outbox), 0)

    def test_the_screening_receives_every_signal(self):
        """
        The endpoint must pass the honeypot, the form token AND the Turnstile
        token through. Omitting any one of them leaves the form looking correct
        and behaving as though that control were switched off.
        """
        with patch('api.v2_contact.evaluate') as evaluate:
            from notifications.antispam import Decision
            evaluate.return_value.decision = Decision.REJECT
            evaluate.return_value.http_status = 200
            self.post(website='x', turnstile_token='tt', form_token='ft')

        kwargs = evaluate.call_args.kwargs
        self.assertEqual(kwargs['honeypot'], 'x')
        self.assertEqual(kwargs['form_token'], 'ft')
        self.assertEqual(kwargs['turnstile_token'], 'tt')
        self.assertEqual(kwargs['form'], 'contact')

    def test_a_rate_limited_sender_is_told_the_truth(self):
        """
        The one rejection that is NOT disguised. A throttle is a condition the
        sender can act on, and saying "received" would be a lie with no
        security value.
        """
        with patch('api.v2_contact.evaluate') as evaluate:
            from notifications.antispam import Decision
            evaluate.return_value.decision = Decision.REJECT
            evaluate.return_value.http_status = 429
            response = self.post()

        self.assertEqual(response.status_code, 429)
        self.assertIn('detail', response.json()['errors'])

    def test_a_quarantined_submission_is_recorded_but_never_emailed(self):
        with patch('api.v2_contact.evaluate') as evaluate:
            from notifications.antispam import Decision
            evaluate.return_value.decision = Decision.REVIEW
            evaluate.return_value.http_status = 200
            evaluate.return_value.reason_codes = ['low_content_quality']
            evaluate.return_value.fingerprint = 'abc123'
            before = notifications_count()
            self.post()

        self.assertEqual(notifications_count(), before + 1)
        self.assertEqual(len(mail.outbox), 0,
                         'A quarantined submission alerted the commercial '
                         'team, which is the whole point of the review tier.')


class ContactPrivacyTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_the_response_echoes_no_submitted_content(self):
        """
        The reply carries a fixed confirmation. Echoing the message back would
        make the endpoint a reflector for anything posted to it.
        """
        response = self.client.post(
            URL,
            data=payload(message='SECRET-CANARY-VALUE that is long enough.'),
            content_type='application/json')
        self.assertNotIn('SECRET-CANARY-VALUE', response.content.decode())
