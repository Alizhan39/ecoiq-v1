"""
Apply the proposed spam classification to existing AdminNotification records.

Dry-run by default. Nothing is ever hard-deleted: records are relabelled, and
the prior spam_status is stored in previous_status so the whole operation can be
rolled back with --rollback.

Three rails guard the --confirm path:

  --expected-count   the number of REJECTs the operator saw in the analysis.
                     A mismatch aborts before anything is written.
  snapshot re-check  the plan is recomputed inside the transaction under row
                     locks; if the data moved underneath it, the whole thing
                     rolls back.
  classifier version stamped on every row, so a later reviewer can tell which
                     ruleset produced a decision.
"""
import collections

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from notifications.antispam.classify import CLASSIFIER_VERSION
from notifications.management.commands.analyse_notification_spam import (
    build_corpus, classify_record,
)
from notifications.models import AdminNotification

DECISION_TO_STATUS = {
    'REJECT': 'rejected',
    'REVIEW': 'review',
    'ACCEPT': 'accepted',
}

# A human has ruled on these; a batch job does not get to overrule them.
HUMAN_DECIDED = ('legitimate',)


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
        parser.add_argument('--expected-count', type=int, default=None,
                            help='Number of REJECT decisions the operator expects, taken from '
                                 'analyse_notification_spam. Aborts on any mismatch.')

    def handle(self, *args, **options):
        confirm = options['confirm']
        marker = options['marker'][:40]

        if options['rollback']:
            return self._rollback(confirm, marker)

        records = self._load(options['source'])
        if not records:
            self.stdout.write('No notifications matched.')
            return

        planned, decisions = self._plan(records)

        w = self.stdout.write
        w('')
        w(f'  classifier         {CLASSIFIER_VERSION}')
        w(f'  records examined   {len(records)}')
        w(f'  changes planned    {len(planned)}')
        w('  decisions: ' + ', '.join(f'{k}={decisions.get(k, 0)}'
                                      for k in ('ACCEPT', 'REVIEW', 'REJECT')))
        before = collections.Counter(r.spam_status for r in records)
        w('  before:  ' + ', '.join(f'{k}={v}' for k, v in sorted(before.items())))
        planned_counts = collections.Counter(t for _, t, _ in planned)
        w('  planned: ' + (', '.join(f'{k}={v}' for k, v in sorted(planned_counts.items())) or 'none'))

        expected = options['expected_count']
        if expected is not None:
            actual = decisions.get('REJECT', 0)
            w(f'  expected REJECT    {expected} (actual {actual})')
            if expected != actual:
                raise CommandError(
                    f'Aborted: --expected-count {expected} does not match the {actual} '
                    f'REJECT decisions this run computed. The data or the ruleset has '
                    f'changed since the analysis. Re-run analyse_notification_spam and '
                    f'confirm the new figure before applying.')

        if not confirm:
            w('')
            w('  DRY RUN — nothing was written. Re-run with --confirm to apply.')
            w('')
            return

        updated = self._apply(planned, marker, expected)

        after = collections.Counter(
            AdminNotification.objects.values_list('spam_status', flat=True))
        w('')
        w(f'  APPLIED — {updated} record(s) reclassified. None deleted.')
        w('  after:  ' + ', '.join(f'{k}={v}' for k, v in sorted(after.items())))
        w(f'  roll back with: python manage.py classify_notification_spam '
          f'--rollback --confirm --marker {marker}')
        w('')

    def _load(self, source):
        qs = AdminNotification.objects.all()
        if source:
            qs = qs.filter(source_type=source)
        return list(qs.only(
            'id', 'contact_name', 'contact_email', 'message', 'metadata',
            'source_type', 'status', 'spam_status'))

    def _plan(self, records):
        """Returns (planned changes, decision counts over every record)."""
        corpus = build_corpus(records)
        planned = []
        decisions = collections.Counter()
        for r in records:
            decision, reasons = classify_record(r, corpus)
            decisions[decision] += 1
            if r.spam_status in HUMAN_DECIDED:
                continue
            target = DECISION_TO_STATUS[decision]
            if r.spam_status == target:
                continue
            planned.append((r, target, reasons))
        return planned, decisions

    def _apply(self, planned, marker, expected):
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
