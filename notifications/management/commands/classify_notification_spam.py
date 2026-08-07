"""
Apply the proposed spam classification to existing AdminNotification records.

Dry-run by default. Nothing is ever hard-deleted: records are relabelled, and
the prior spam_status is stored in previous_status so the whole operation can be
rolled back with --rollback.

Why there are three separate expectation flags
----------------------------------------------
There used to be one, `--expected-count`, and it was ambiguous. Its value (965)
was the number of REJECT *decisions*, which is neither the number of rows in the
table (979) nor the number of rows that would actually change (which differs
again, because rows already carrying the target status do not move). An operator
reading a runbook could not tell which of the three a given number meant, and
every one of them looks plausible at a glance.

They are now separate and each means exactly one thing:

  --expected-total N          rows the command may consider
  --expected-reject-count N   rows the classifier decides are REJECT
  --expected-transitions N    rows whose stored status would actually change
  --snapshot-hash HASH        digest of (id, current status, decision) for every
                              row, so any drift at all aborts

`analyse_notification_spam` prints all four. Supply the ones you checked; each
is verified before a single row is written, and any mismatch aborts.
"""
import argparse
import collections

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from notifications.antispam.classify import CLASSIFIER_VERSION
from notifications.management.commands.analyse_notification_spam import (
    DECISION_TO_STATUS, HUMAN_DECIDED, build_corpus, plan_transitions, snapshot_hash,
)
from notifications.models import AdminNotification

class Command(BaseCommand):
    help = ('Classify existing notifications as accepted/review/rejected. '
            'Dry-run unless --confirm is given. Never deletes.')

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true',
                            help='Actually write the classification. Without it, this is a dry run.')
        parser.add_argument('--rollback', action='store_true',
                            help='Restore previous_status for records this command previously changed.')
        parser.add_argument('--source', default='', help='Limit to one source_type.')
        parser.add_argument('--marker', default='classify_notification_spam',
                            help='Value written to classified_by; also selects rows for --rollback.')
        parser.add_argument('--expected-total', type=int, default=None,
                            help='Rows the command may consider. Aborts on mismatch.')
        parser.add_argument('--expected-reject-count', type=int, default=None,
                            help='Rows the classifier decides are REJECT. Aborts on mismatch.')
        parser.add_argument('--expected-transitions', type=int, default=None,
                            help='Rows whose stored status would actually change. Aborts on mismatch.')
        parser.add_argument('--snapshot-hash', default='',
                            help='Digest from analyse_notification_spam. Aborts if anything drifted.')
        parser.add_argument('--expected-count', type=int, default=None,
                            help=argparse.SUPPRESS)

    def handle(self, *args, **options):
        if options['expected_count'] is not None:
            raise CommandError(
                '--expected-count was ambiguous and has been split. Its old value was '
                'the REJECT decision count, not the row total and not the number of '
                'rows that change. Use --expected-reject-count, and additionally '
                '--expected-total / --expected-transitions / --snapshot-hash. Take all '
                'four from analyse_notification_spam.')

        confirm = options['confirm']
        marker = options['marker'][:40]

        if options['rollback']:
            return self._rollback(confirm, marker)

        records = self._load(options['source'])
        if not records:
            self.stdout.write('No notifications matched.')
            return

        planned, decisions, refused = self._plan(records)
        digest = snapshot_hash(records, build_corpus(records))

        w = self.stdout.write
        w('')
        w(f'  classifier         {CLASSIFIER_VERSION}')
        w(f'  records examined   {len(records)}')
        w(f'  changes planned    {len(planned)}')
        w(f'  snapshot hash      {digest}')
        w('  decisions: ' + ', '.join(f'{k}={decisions.get(k, 0)}'
                                      for k in ('ACCEPT', 'REVIEW', 'REJECT')))
        before = collections.Counter(r.spam_status for r in records)
        w('  before:  ' + ', '.join(f'{k}={v}' for k, v in sorted(before.items())))
        planned_counts = collections.Counter(t for _, t, _ in planned)
        w('  planned: ' + (', '.join(f'{k}={v}' for k, v in sorted(planned_counts.items())) or 'none'))
        if refused:
            w('  refused (guard):')
            for reason, n in sorted(refused.items()):
                w(f'    {n:>5}  {reason}')

        self._check_expectations(options, records, decisions, planned, digest, w)

        if not confirm:
            w('')
            w('  DRY RUN — nothing was written. Re-run with --confirm to apply.')
            w('')
            return

        updated = self._apply(planned, marker, digest, options['source'])

        after = collections.Counter(
            AdminNotification.objects.values_list('spam_status', flat=True))
        w('')
        w(f'  APPLIED — {updated} record(s) reclassified. None deleted.')
        w('  after:  ' + ', '.join(f'{k}={v}' for k, v in sorted(after.items())))
        w(f'  roll back with: python manage.py classify_notification_spam '
          f'--rollback --confirm --marker {marker}')
        w('')

    def _check_expectations(self, options, records, decisions, planned, digest, w):
        checks = (
            ('--expected-total', options['expected_total'], len(records),
             'rows considered'),
            ('--expected-reject-count', options['expected_reject_count'],
             decisions.get('REJECT', 0), 'REJECT decisions'),
            ('--expected-transitions', options['expected_transitions'],
             len(planned), 'rows that would change'),
        )
        for flag, expected, actual, label in checks:
            if expected is None:
                continue
            w(f'  {flag} {expected} (actual {actual})')
            if expected != actual:
                raise CommandError(
                    f'Aborted: {flag} {expected} does not match the {actual} {label} '
                    f'this run computed. The data or the ruleset changed since the '
                    f'analysis. Nothing was written. Re-run analyse_notification_spam.')

        supplied = options['snapshot_hash'].strip()
        if supplied:
            w(f'  --snapshot-hash {supplied[:16]}… (actual {digest[:16]}…)')
            if supplied != digest:
                raise CommandError(
                    'Aborted: the snapshot hash does not match. At least one record '
                    'changed status, was added or was removed since the analysis. '
                    'Nothing was written. Re-run analyse_notification_spam.')

    def _load(self, source):
        qs = AdminNotification.objects.all()
        if source:
            qs = qs.filter(source_type=source)
        return list(qs.only(
            'id', 'contact_name', 'contact_email', 'message', 'metadata',
            'source_type', 'status', 'spam_status').order_by('id'))

    def _plan(self, records):
        """Delegates to the shared planner so both commands agree by construction."""
        return plan_transitions(records, build_corpus(records))

    def _apply(self, planned, marker, digest, source):
        stamp = f'{marker}@{CLASSIFIER_VERSION}'[:60]
        updated = 0
        with transaction.atomic():
            # Re-read every target under a row lock and re-check it still wants
            # the same change. If anything moved between the plan and here — a
            # human reclassified a record, a new submission landed — the whole
            # transaction is abandoned rather than half-applied.
            ids = [r.pk for r, _, _ in planned]
            locked = {
                obj.pk: obj for obj in
                AdminNotification.objects.select_for_update().filter(pk__in=ids)
            }
            if len(locked) != len(ids):
                raise CommandError(
                    f'Aborted: {len(ids) - len(locked)} planned record(s) no longer exist. '
                    f'Nothing was written.')

            # The snapshot is recomputed inside the lock as well: a row outside
            # the planned set could have changed, and that still invalidates the
            # figures the operator approved.
            current = self._load(source)
            if snapshot_hash(current, build_corpus(current)) != digest:
                raise CommandError(
                    'Aborted: the table changed between planning and writing. '
                    'Nothing was written.')

            for record, target, reasons in planned:
                obj = locked[record.pk]
                if obj.spam_status != record.spam_status:
                    raise CommandError(
                        f'Aborted: record {obj.pk} changed status between the plan and '
                        f'the write. Nothing was written; re-run the analysis.')
                if obj.spam_status in HUMAN_DECIDED:
                    raise CommandError(
                        f'Aborted: record {obj.pk} carries a human decision. '
                        f'Nothing was written.')
                if obj.spam_status == 'accepted' and target == 'rejected':
                    raise CommandError(
                        f'Aborted: record {obj.pk} would be downgraded from accepted '
                        f'to rejected. Nothing was written.')
                obj.previous_status = obj.spam_status
                obj.spam_status = target
                obj.risk_reasons = reasons
                obj.classified_at = timezone.now()
                obj.classified_by = stamp
                if target == 'rejected' and obj.status == 'unread':
                    # Clear the unread badge without deleting anything.
                    obj.status = 'archived'
                obj.save(update_fields=[
                    'previous_status', 'spam_status', 'risk_reasons',
                    'classified_at', 'classified_by', 'status'])
                updated += 1
        return updated

    def _rollback(self, confirm, marker):
        qs = (AdminNotification.objects
              .filter(classified_by__startswith=marker)
              .exclude(classified_by__endswith=':rollback')
              .exclude(previous_status=''))
        count = qs.count()
        self.stdout.write(f'  rollback candidates: {count}')
        if not confirm:
            self.stdout.write('  DRY RUN — nothing was written. Add --confirm to apply.')
            return
        restored = 0
        with transaction.atomic():
            for record in qs.select_for_update():
                record.spam_status, record.previous_status = record.previous_status, ''
                record.classified_at = timezone.now()
                record.classified_by = f'{marker}:rollback'[:60]
                record.save(update_fields=['spam_status', 'previous_status',
                                           'classified_at', 'classified_by'])
                restored += 1
        self.stdout.write(f'  ROLLED BACK — {restored} record(s) restored.')
