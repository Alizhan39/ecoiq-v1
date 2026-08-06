"""
Apply the proposed spam classification to existing AdminNotification records.

Dry-run by default. Nothing is ever hard-deleted: records are relabelled, and
the prior spam_status is stored in previous_status so the whole operation can be
rolled back with --rollback.
"""
import collections

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from notifications.management.commands.analyse_notification_spam import propose
from notifications.antispam.fingerprint import normalise_text, submission_fingerprint
from notifications.models import AdminNotification

DECISION_TO_STATUS = {
    'REJECT': 'rejected',
    'REVIEW': 'review',
    'ACCEPT': 'accepted',
}


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

    def handle(self, *args, **options):
        confirm = options['confirm']
        marker = options['marker'][:60]

        if options['rollback']:
            return self._rollback(confirm, marker)

        qs = AdminNotification.objects.all()
        if options['source']:
            qs = qs.filter(source_type=options['source'])

        records = list(qs.only(
            'id', 'contact_name', 'contact_email', 'message', 'metadata',
            'source_type', 'status', 'spam_status'))
        if not records:
            self.stdout.write('No notifications matched.')
            return

        name_counts = collections.Counter()
        for r in records:
            key = normalise_text(r.contact_name)
            if key:
                name_counts[key] += 1
        fingerprint_counts = collections.Counter()
        for r in records:
            fingerprint_counts[submission_fingerprint(
                email=r.contact_email, name=r.contact_name,
                subject=(r.metadata or {}).get('subject', ''),
                message=r.message, form=r.source_type or '')] += 1

        before = collections.Counter(r.spam_status for r in records)
        planned = []
        for r in records:
            decision, reasons = propose(r, name_counts=name_counts,
                                        fingerprint_counts=fingerprint_counts)
            target = DECISION_TO_STATUS[decision]
            if r.spam_status in ('legitimate',):
                continue        # never override a human decision
            if r.spam_status == target:
                continue
            planned.append((r, target, reasons))

        w = self.stdout.write
        w('')
        w(f'  records examined   {len(records)}')
        w(f'  changes planned    {len(planned)}')
        w('  before: ' + ', '.join(f'{k}={v}' for k, v in sorted(before.items())))
        planned_counts = collections.Counter(t for _, t, _ in planned)
        w('  planned: ' + (', '.join(f'{k}={v}' for k, v in sorted(planned_counts.items())) or 'none'))

        if not confirm:
            w('')
            w('  DRY RUN — nothing was written. Re-run with --confirm to apply.')
            w('')
            return

        updated = 0
        with transaction.atomic():
            for record, target, reasons in planned:
                locked = AdminNotification.objects.select_for_update().get(pk=record.pk)
                locked.previous_status = locked.spam_status
                locked.spam_status = target
                locked.risk_reasons = reasons
                locked.classified_at = timezone.now()
                locked.classified_by = marker
                if target == 'rejected' and locked.status == 'unread':
                    # Clear the unread badge without deleting anything.
                    locked.status = 'archived'
                locked.save(update_fields=[
                    'previous_status', 'spam_status', 'risk_reasons',
                    'classified_at', 'classified_by', 'status'])
                updated += 1

        after = collections.Counter(
            AdminNotification.objects.values_list('spam_status', flat=True))
        w('')
        w(f'  APPLIED — {updated} record(s) reclassified. None deleted.')
        w('  after:  ' + ', '.join(f'{k}={v}' for k, v in sorted(after.items())))
        w(f'  roll back with: python manage.py classify_notification_spam --rollback --confirm --marker {marker}')
        w('')

    def _rollback(self, confirm, marker):
        qs = AdminNotification.objects.filter(classified_by=marker).exclude(previous_status='')
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
