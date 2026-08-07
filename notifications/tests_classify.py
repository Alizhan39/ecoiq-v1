"""
Regression tests for notifications.antispam.classify.

The scenarios in notifications/testdata/spam_regression_scenarios.json are
entirely synthetic — they reproduce the *shapes* seen in the August 2026
contact-form incident, never its contents. See the _readme key in that file.
"""
import json
import pathlib

from django.test import SimpleTestCase, TestCase

from notifications.antispam import classify as C
from notifications.antispam.fingerprint import submission_fingerprint

SCENARIO_PATH = (pathlib.Path(__file__).resolve().parent
                 / 'testdata' / 'spam_regression_scenarios.json')


def load_scenarios():
    with SCENARIO_PATH.open(encoding='utf-8') as handle:
        return json.load(handle)['scenarios']


def fingerprint(entry):
    return submission_fingerprint(
        email=entry.get('email', ''), name=entry.get('name', ''),
        subject=entry.get('subject', ''), message=entry.get('message', ''),
        form='contact')


def corpus_for(scenario):
    """Build the corpus a scenario says its record should be scored against."""
    corpus = C.Corpus()
    record = scenario['record']

    def add(entry):
        corpus.add(name=entry.get('name', ''), email=entry.get('email', ''),
                   subject=entry.get('subject', ''), message=entry.get('message', ''),
                   fingerprint=fingerprint(entry))

    add(record)
    for entry in scenario.get('corpus', []):
        add(entry)

    gen = scenario.get('corpus_generator')
    if gen:
        kind = gen['kind']
        # `start` skips the index the record under test already occupies, so a
        # scenario isolates the one signal it is written to prove instead of
        # also tripping duplicate_submission against itself.
        indices = range(gen.get('start', 0), gen.get('start', 0) + gen['count'])
        if kind == 'name_across_addresses':
            for i in indices:
                add({'name': gen['name'],
                     'email': gen['email_template'].format(i=i),
                     'subject': gen['subject'],
                     'message': gen['message_template'].format(i=i)})
        elif kind == 'template_across_addresses':
            for i in indices:
                add({'name': gen['name_template'].format(i=i),
                     'email': gen['email_template'].format(i=i),
                     'subject': gen['subject'], 'message': gen['message']})
        elif kind == 'repeat_self':
            for _ in range(gen['count'] - 1):
                add(record)
        else:                                   # pragma: no cover - guard
            raise AssertionError(f'unknown corpus_generator kind {kind!r}')
    return corpus


def run_scenario(scenario):
    record = scenario['record']
    return C.classify(
        name=record.get('name', ''), email=record.get('email', ''),
        subject=record.get('subject', ''), message=record.get('message', ''),
        fingerprint=fingerprint(record), corpus=corpus_for(scenario))


class ScenarioRegressionTests(SimpleTestCase):
    """1–3: the fixture drives the classifier end to end."""

    def test_every_scenario_reaches_its_expected_decision(self):
        for scenario in load_scenarios():
            with self.subTest(scenario['id']):
                decision, _ = run_scenario(scenario)
                self.assertEqual(decision, scenario['expect'], scenario['why'])

    def test_every_scenario_produces_its_expected_signals(self):
        for scenario in load_scenarios():
            with self.subTest(scenario['id']):
                _, signals = run_scenario(scenario)
                self.assertEqual(signals, scenario['expect_signals'], scenario['why'])

    def test_fixture_covers_all_three_decisions(self):
        expected = {s['expect'] for s in load_scenarios()}
        self.assertEqual(expected, {'ACCEPT', 'REVIEW', 'REJECT'})


class SignalTableTests(SimpleTestCase):
    """4–6: the signal table itself stays coherent."""

    def test_every_signal_has_a_strength_and_an_explanation(self):
        for code, (strength, explanation) in C.SIGNALS.items():
            with self.subTest(code):
                self.assertIsInstance(strength, C.Strength)
                self.assertTrue(explanation.strip())

    def test_signals_for_only_emits_known_codes(self):
        _, signals = C.classify(
            name='Anyone', email='not-valid', message='a b',
            corpus=C.Corpus())
        self.assertTrue(set(signals) <= set(C.SIGNALS))

    def test_classifier_version_is_recorded_and_non_empty(self):
        self.assertTrue(C.CLASSIFIER_VERSION.strip())


class DecisionFoldingTests(SimpleTestCase):
    """7–10: the strength arithmetic, tested directly."""

    def test_one_strong_signal_rejects(self):
        self.assertEqual(C.decide(['name_on_many_distinct_emails']), 'REJECT')

    def test_two_medium_signals_reject_but_one_only_reviews(self):
        self.assertEqual(C.decide(['excessive_urls']), 'REVIEW')
        self.assertEqual(C.decide(['excessive_urls', 'invalid_email_format']), 'REJECT')

    def test_weak_signals_never_reject(self):
        every_weak = [c for c, (s, _) in C.SIGNALS.items() if s is C.Strength.WEAK]
        self.assertNotEqual(C.decide(every_weak), 'REJECT')
        self.assertEqual(C.decide(every_weak[:1]), 'ACCEPT')
        self.assertEqual(C.decide(every_weak[:2]), 'REVIEW')

    def test_no_signals_accepts(self):
        self.assertEqual(C.decide([]), 'ACCEPT')


class NonSignalTests(SimpleTestCase):
    """11–13: things that must never, on their own, count against a sender."""

    BASE = {
        'subject': 'Enquiry about the platform',
        'message': ('Hello, I would like to understand how the reporting module '
                    'handles multi-site organisations. Could someone get in touch?'),
    }

    def test_mailbox_provider_is_not_a_signal(self):
        for domain in ('gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com',
                       'aol.com', 'web.de', 'proton.me'):
            with self.subTest(domain):
                decision, signals = C.classify(
                    name='Robin Clarke', email=f'robin.clarke@{domain}',
                    corpus=C.Corpus(), **self.BASE)
                self.assertEqual(decision, 'ACCEPT')
                self.assertEqual(signals, [])

    def test_unusual_or_non_english_names_are_not_a_signal(self):
        for name in ('Nguyễn Thị Hương', 'Åsa Lindqvist', 'Οδυσσέας',
                     'Muhammad', 'X', 'Jean-Luc de la Fontaine-Bouchard'):
            with self.subTest(name):
                decision, _ = C.classify(
                    name=name, email='someone@example.com',
                    corpus=C.Corpus(), **self.BASE)
                self.assertEqual(decision, 'ACCEPT')

    def test_country_code_domains_are_not_a_signal(self):
        for domain in ('example.co.uk', 'example.de', 'example.kz',
                       'example.cn', 'example.ru', 'example.ng'):
            with self.subTest(domain):
                decision, _ = C.classify(
                    name='Robin Clarke', email=f'robin@{domain}',
                    corpus=C.Corpus(), **self.BASE)
                self.assertEqual(decision, 'ACCEPT')


class ThresholdBoundaryTests(SimpleTestCase):
    """14–15: the thresholds fire exactly where they are documented to."""

    def _corpus_with(self, n_addresses):
        corpus = C.Corpus()
        for i in range(n_addresses):
            corpus.add(name='Repeat Sender', email=f'addr{i}@example.net',
                       subject='Proposal', message='A proposal for your team to consider today.')
        return corpus

    def test_name_signal_switches_strength_at_the_documented_boundary(self):
        just_below = C.NAME_DISTINCT_EMAILS_STRONG - 1
        _, weak = C.classify(name='Repeat Sender', email='addr0@example.net',
                             subject='Proposal',
                             message='A proposal for your team to consider today.',
                             corpus=self._corpus_with(just_below))
        self.assertIn('name_on_several_distinct_emails', weak)
        self.assertNotIn('name_on_many_distinct_emails', weak)

        _, strong = C.classify(name='Repeat Sender', email='addr0@example.net',
                               subject='Proposal',
                               message='A proposal for your team to consider today.',
                               corpus=self._corpus_with(C.NAME_DISTINCT_EMAILS_STRONG))
        self.assertIn('name_on_many_distinct_emails', strong)
        self.assertNotIn('name_on_several_distinct_emails', strong)

    def test_message_skeleton_collapses_variable_substitutions(self):
        a = C.message_skeleton('Order 12345 is ready for collection now')
        b = C.message_skeleton('Order 98765 is ready for collection now')
        self.assertEqual(a, b)
        c = C.message_skeleton('Entirely different wording about something else')
        self.assertNotEqual(a, c)


class LiveEngineAlignmentTests(TestCase):
    """The live path and the batch classifier agree on the decisive rule."""

    def test_strong_name_signal_is_a_hard_reject_on_the_live_path(self):
        from notifications.antispam.verdict import HARD_REJECT, Reason
        self.assertIn(Reason.NAME_ON_MANY_DISTINCT_EMAILS, HARD_REJECT)
        self.assertEqual(Reason.NAME_ON_MANY_DISTINCT_EMAILS.value,
                         'name_on_many_distinct_emails')
        self.assertIs(C.SIGNALS[Reason.NAME_ON_MANY_DISTINCT_EMAILS.value][0],
                      C.Strength.STRONG)

    # ── bulk-job guards ────────────────────────────────────────────────────
    def _spray(self, n=30, name='Sprayer'):
        from notifications.models import AdminNotification
        return [AdminNotification.objects.create(
            title='t', message='cheap deals for your business today',
            source_type='contact', contact_name=name,
            contact_email=f'a{i}@example.net') for i in range(n)]

    def test_an_existing_accept_is_never_downgraded_to_reject(self):
        from io import StringIO

        from django.core.management import call_command

        records = self._spray()
        protected = records[0]
        protected.spam_status = 'accepted'
        protected.save(update_fields=['spam_status'])

        out = StringIO()
        call_command('classify_notification_spam', '--confirm', stdout=out)
        protected.refresh_from_db()
        self.assertEqual(protected.spam_status, 'accepted')
        self.assertIn('never automatic', out.getvalue())

    def test_review_is_not_promoted_to_reject_without_a_strong_signal(self):
        from io import StringIO

        from django.core.management import call_command

        from notifications.models import AdminNotification

        # Two MEDIUM signals: enough to reject a live submission, not enough to
        # relabel a row already sitting in the review queue.
        rec = AdminNotification.objects.create(
            title='t', source_type='contact', contact_name='Marketing',
            contact_email='not-an-address',
            message=('Visit https://example.net/a and https://example.net/b and '
                     'https://example.net/c and https://example.net/d today'),
            spam_status='review')
        AdminNotification.objects.create(
            title='t', source_type='contact', contact_name='Marketing',
            contact_email='not-an-address',
            message=('Visit https://example.net/a and https://example.net/b and '
                     'https://example.net/c and https://example.net/d today'))

        out = StringIO()
        call_command('classify_notification_spam', '--confirm', stdout=out)
        rec.refresh_from_db()
        self.assertEqual(rec.spam_status, 'review')
        self.assertIn('without a strong signal', out.getvalue())

    def test_rows_already_at_the_target_are_not_counted_as_transitions(self):
        from io import StringIO

        from django.core.management import call_command

        from notifications.models import AdminNotification

        self._spray()
        AdminNotification.objects.all().update(spam_status='rejected')

        out = StringIO()
        call_command('classify_notification_spam', stdout=out)
        self.assertIn('changes planned    0', out.getvalue())

    def test_the_three_expectation_flags_each_mean_one_thing(self):
        from io import StringIO

        from django.core.management import call_command
        from django.core.management.base import CommandError

        self._spray(30)
        # 30 rows, 30 REJECT decisions, 30 transitions — distinct concepts that
        # happen to coincide here; each flag is checked independently.
        for flag, wrong in (('--expected-total', '29'),
                            ('--expected-reject-count', '31'),
                            ('--expected-transitions', '1')):
            with self.subTest(flag):
                with self.assertRaises(CommandError) as ctx:
                    call_command('classify_notification_spam', '--confirm',
                                 flag, wrong, stdout=StringIO())
                self.assertIn(flag, str(ctx.exception))
                from notifications.models import AdminNotification
                self.assertEqual(
                    AdminNotification.objects.filter(spam_status='unclassified').count(), 30)

    def test_snapshot_hash_mismatch_aborts_before_writing(self):
        from io import StringIO

        from django.core.management import call_command
        from django.core.management.base import CommandError

        from notifications.models import AdminNotification

        self._spray()
        with self.assertRaises(CommandError) as ctx:
            call_command('classify_notification_spam', '--confirm',
                         '--snapshot-hash', 'deadbeef' * 8, stdout=StringIO())
        self.assertIn('snapshot hash', str(ctx.exception))
        self.assertEqual(
            AdminNotification.objects.exclude(spam_status='unclassified').count(), 0)

    def test_snapshot_hash_changes_when_a_single_status_changes(self):
        from notifications.management.commands.analyse_notification_spam import (
            build_corpus, snapshot_hash,
        )
        from notifications.models import AdminNotification

        records = self._spray()
        loaded = list(AdminNotification.objects.order_by('id'))
        before = snapshot_hash(loaded, build_corpus(loaded))

        records[0].spam_status = 'legitimate'
        records[0].save(update_fields=['spam_status'])
        loaded = list(AdminNotification.objects.order_by('id'))
        after = snapshot_hash(loaded, build_corpus(loaded))
        self.assertNotEqual(before, after)

    def test_the_ambiguous_old_flag_is_refused_with_an_explanation(self):
        from io import StringIO

        from django.core.management import call_command
        from django.core.management.base import CommandError

        self._spray()
        with self.assertRaises(CommandError) as ctx:
            call_command('classify_notification_spam', '--confirm',
                         '--expected-count', '30', stdout=StringIO())
        message = str(ctx.exception)
        self.assertIn('ambiguous', message)
        self.assertIn('--expected-reject-count', message)

    def test_analysis_and_mutation_agree_on_the_transition_count(self):
        from io import StringIO

        from django.core.management import call_command

        self._spray()
        analysis = StringIO()
        call_command('analyse_notification_spam', stdout=analysis)
        mutation = StringIO()
        call_command('classify_notification_spam', stdout=mutation)

        import re
        a = re.search(r'ROWS THAT WOULD ACTUALLY CHANGE: (\d+)', analysis.getvalue())
        m = re.search(r'changes planned\s+(\d+)', mutation.getvalue())
        self.assertIsNotNone(a)
        self.assertIsNotNone(m)
        self.assertEqual(a.group(1), m.group(1))

    def test_expected_reject_count_mismatch_aborts_before_writing(self):
        from io import StringIO

        from django.core.management import call_command
        from django.core.management.base import CommandError

        from notifications.models import AdminNotification

        self._spray()
        with self.assertRaises(CommandError) as ctx:
            call_command('classify_notification_spam', '--confirm',
                         '--expected-reject-count', '1', stdout=StringIO())
        self.assertIn('does not match', str(ctx.exception))
        self.assertEqual(
            AdminNotification.objects.exclude(spam_status='unclassified').count(), 0)

    def test_human_decided_records_are_never_overruled(self):
        from io import StringIO

        from django.core.management import call_command

        from notifications.models import AdminNotification

        for i in range(30):
            AdminNotification.objects.create(
                title='t', message='cheap deals for you today',
                source_type='contact', contact_name='Sprayer',
                contact_email=f'a{i}@example.net')
        marked = AdminNotification.objects.first()
        marked.spam_status = 'legitimate'
        marked.save(update_fields=['spam_status'])

        call_command('classify_notification_spam', '--confirm', stdout=StringIO())
        marked.refresh_from_db()
        self.assertEqual(marked.spam_status, 'legitimate')

    def test_distinct_emails_for_name_counts_addresses_not_records(self):
        from notifications.antispam.heuristics import distinct_emails_for_name
        from notifications.models import AdminNotification

        for _ in range(8):
            AdminNotification.objects.create(
                title='t', message='m', contact_name='Same Person',
                contact_email='same.person@example.com')
        self.assertEqual(distinct_emails_for_name('Same Person'), 1)

        for i in range(8):
            AdminNotification.objects.create(
                title='t', message='m', contact_name='Sprayer',
                contact_email=f'sprayer{i}@example.net')
        self.assertEqual(distinct_emails_for_name('Sprayer'), 8)
