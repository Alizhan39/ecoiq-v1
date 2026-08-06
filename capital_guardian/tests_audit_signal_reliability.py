"""
Regression tests for Capital Guardian audit-signal registration.

`capital_guardian/signals.py` builds its receivers as closures inside
`connect()` and registered them with Django's default `weak=True`. Nothing else
held a strong reference, so CPython collected them almost immediately and the
signal dispatcher skipped the dead weak references in silence: every governance,
milestone, equipment, CAPEX, red-flag, evidence and capital-trace change went
unaudited.

It was invisible for two reasons. The audit path raises nothing when a receiver
is missing — it simply never runs — and under `DEBUG=True` Django retains
`connection.queries_log`, which perturbs allocation enough that the closures
usually survive, so the test suite passed. A production process
(`DEBUG=False`) wrote no audit rows at all.

`notifications/signals.py` already used `weak=False` for the same closure
pattern; this module simply omitted it.

These tests assert the registration property directly, so they hold regardless
of GC timing rather than depending on it.
"""
import gc
import weakref

from django.db.models.signals import post_save, pre_save
from django.test import TestCase

from capital_guardian import signals as cg_signals
from capital_guardian.models import AuditLogEntry, ProjectGovernance, RedFlag
from gold_intelligence.models import CapitalBudgetLine, GoldProject, MineTimelineMilestone

# Every sender capital_guardian audits, and the signals it registers for.
AUDITED_SENDERS = (
    ProjectGovernance,
    MineTimelineMilestone,
    CapitalBudgetLine,
    RedFlag,
    GoldProject,
)


def dead_weak_receivers(signal, sender):
    """Receivers registered for `sender` whose weak reference has died."""
    dead = []
    for entry in signal.receivers:
        key, receiver = entry[0], entry[1]
        uid = key[0]
        if not (isinstance(uid, str) and uid.startswith('cg_audit_')):
            continue
        if isinstance(receiver, weakref.ReferenceType) and receiver() is None:
            dead.append(uid)
    return dead


class SignalRegistrationTests(TestCase):
    """The registration must survive garbage collection."""

    def test_no_capital_guardian_receiver_is_registered_weakly(self):
        """
        A closure receiver registered with weak=True has no owner and can be
        collected at any moment. This is the defect, asserted directly.
        """
        offenders = []
        for signal, name in ((pre_save, 'pre_save'), (post_save, 'post_save')):
            for entry in signal.receivers:
                key, receiver = entry[0], entry[1]
                uid = key[0]
                if isinstance(uid, str) and uid.startswith('cg_audit_'):
                    if isinstance(receiver, weakref.ReferenceType):
                        offenders.append(f'{name}:{uid}')
        self.assertEqual(
            offenders, [],
            'capital_guardian audit receivers must be registered with '
            'weak=False; these are weakly referenced and can be collected '
            'silently, disabling the audit trail: ' + ', '.join(offenders))

    def test_no_receiver_has_already_been_collected(self):
        gc.collect()
        for signal, name in ((pre_save, 'pre_save'), (post_save, 'post_save')):
            with self.subTest(signal=name):
                self.assertEqual(dead_weak_receivers(signal, None), [])

    def test_receivers_are_registered_for_every_audited_sender(self):
        for sender in AUDITED_SENDERS:
            with self.subTest(sender=sender.__name__):
                self.assertTrue(
                    pre_save._live_receivers(sender),
                    f'no live pre_save receiver for {sender.__name__}')
                self.assertTrue(
                    post_save._live_receivers(sender),
                    f'no live post_save receiver for {sender.__name__}')

    def test_connect_uses_weak_false_for_every_connection(self):
        """Source-level guard so a new connection cannot omit it."""
        import inspect
        import re
        source = inspect.getsource(cg_signals.connect)
        calls = re.findall(r'(?:pre_save|post_save)\.connect\((?:[^()]|\([^()]*\))*\)',
                           source, re.S)
        self.assertTrue(calls, 'no connect() calls found — test needs updating')
        missing = [c.split('dispatch_uid=')[-1].split(',')[0]
                   for c in calls if 'weak=False' not in c]
        self.assertEqual(missing, [], f'connect() calls missing weak=False: {missing}')


class AuditTrailSurvivesGarbageCollectionTests(TestCase):
    """
    End-to-end: force collection, then confirm the audit trail still records.
    Before the fix this produced zero rows.
    """

    def setUp(self):
        self.project = GoldProject.objects.create(
            name='GC Audit Probe', slug='gc-audit-probe')

    def test_creation_is_audited_after_forced_collection(self):
        gc.collect()
        ProjectGovernance.objects.create(project=self.project)
        entries = AuditLogEntry.objects.filter(
            project=self.project, event_type='governance')
        self.assertEqual(entries.count(), 1)
        self.assertEqual(entries.first().field_name, '(created)')

    def test_field_change_is_audited_after_forced_collection(self):
        governance = ProjectGovernance.objects.create(
            project=self.project, escrow_account_active=False)
        gc.collect()
        governance.escrow_account_active = True
        governance.save()
        entry = AuditLogEntry.objects.filter(
            project=self.project, field_name='escrow_account_active').first()
        self.assertIsNotNone(
            entry, 'field change was not audited after garbage collection')
        self.assertEqual(entry.previous_value, 'False')
        self.assertEqual(entry.new_value, 'True')

    def test_repeated_collection_does_not_disable_auditing(self):
        for i in range(3):
            gc.collect()
            milestone = MineTimelineMilestone.objects.create(
                project=self.project, phase='exploration')
            gc.collect()
            milestone.save()
        self.assertTrue(
            AuditLogEntry.objects.filter(
                project=self.project, event_type='milestone').exists(),
            'milestone auditing stopped after repeated collection')

    def test_auditing_does_not_duplicate_entries(self):
        """weak=False must not cause double registration on repeated connect()."""
        cg_signals.connect()   # idempotent via dispatch_uid
        cg_signals.connect()
        ProjectGovernance.objects.create(project=self.project)
        self.assertEqual(
            AuditLogEntry.objects.filter(
                project=self.project, event_type='governance').count(), 1,
            'repeated connect() must not create duplicate audit entries')
