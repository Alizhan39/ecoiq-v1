"""
Read-only analysis of existing AdminNotification records.

Writes nothing. Prints aggregate statistics and a proposed ACCEPT / REVIEW /
REJECT split so the classification can be reviewed before anything is changed.

Never prints message bodies, full email addresses or any other personal
content — only counts, domains and truncated fingerprints.
"""
import collections
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.antispam.fingerprint import normalise_text, submission_fingerprint
from notifications.antispam.heuristics import count_urls, email_is_valid, is_disposable, low_content_quality
from notifications.models import AdminNotification


def propose(record, *, name_counts, fingerprint_counts):
    """Deterministic proposal for one existing record. Returns (decision, reasons)."""
    reasons = []
    if record.contact_email and not email_is_valid(record.contact_email):
        reasons.append('invalid_email_format')
    if is_disposable(record.contact_email):
        reasons.append('disposable_email_domain')
    if count_urls(record.message) > 2:
        reasons.append('excessive_urls')
    if low_content_quality(record.message):
        reasons.append('low_content_quality')
    name_key = normalise_text(record.contact_name)
    if name_key and name_counts.get(name_key, 0) >= 5:
        reasons.append('name_reused_across_emails')
    fp = submission_fingerprint(
        email=record.contact_email, name=record.contact_name,
        subject=(record.metadata or {}).get('subject', ''),
        message=record.message, form=record.source_type or '')
    if fingerprint_counts.get(fp, 0) > 1:
        reasons.append('duplicate_submission')

    if 'name_reused_across_emails' in reasons and len(reasons) >= 2:
        return 'REJECT', reasons
    if len(reasons) >= 3:
        return 'REJECT', reasons
    if reasons:
        return 'REVIEW', reasons
    return 'ACCEPT', reasons


class Command(BaseCommand):
    help = ('Read-only analysis of AdminNotification records with a proposed '
            'spam classification. Writes nothing.')

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Accepted for symmetry; this command is always read-only.')
        parser.add_argument('--source', default='', help='Limit to one source_type.')
        parser.add_argument('--days', type=int, default=0, help='Only records from the last N days.')

    def handle(self, *args, **options):
        qs = AdminNotification.objects.all()
        if options['source']:
            qs = qs.filter(source_type=options['source'])
        if options['days']:
            qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=options['days']))

        total = qs.count()
        if not total:
            self.stdout.write('No notifications matched.')
            return

        records = list(qs.only(
            'id', 'contact_name', 'contact_email', 'message', 'metadata',
            'source_type', 'status', 'spam_status', 'created_at'))

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

        domains = collections.Counter(
            r.contact_email.rpartition('@')[2].lower()
            for r in records if '@' in (r.contact_email or ''))

        proposals = collections.Counter()
        reason_counter = collections.Counter()
        for r in records:
            decision, reasons = propose(r, name_counts=name_counts,
                                        fingerprint_counts=fingerprint_counts)
            proposals[decision] += 1
            for code in reasons:
                reason_counter[code] += 1

        unread = sum(1 for r in records if r.status == 'unread')
        dupes = sum(c for c in fingerprint_counts.values() if c > 1)
        earliest = min(r.created_at for r in records)
        latest = max(r.created_at for r in records)

        w = self.stdout.write
        w('')
        w('  ANALYSIS — read-only, nothing was modified')
        w('  ' + '─' * 58)
        w(f'  total records            {total}')
        w(f'  unread                   {unread}')
        w(f'  distinct contact names   {len(name_counts)}')
        w(f'  distinct email domains   {len(domains)}')
        w(f'  duplicate fingerprints   {dupes} records across '
          f'{sum(1 for c in fingerprint_counts.values() if c > 1)} groups')
        w(f'  earliest                 {earliest:%Y-%m-%d %H:%M} UTC')
        w(f'  latest                   {latest:%Y-%m-%d %H:%M} UTC')
        w('')
        w('  Most repeated contact names (count only, no other detail):')
        for name, n in name_counts.most_common(5):
            w(f'    {n:>5}  {name[:38]}')
        w('')
        w('  Most common email domains:')
        for dom, n in domains.most_common(8):
            w(f'    {n:>5}  {dom}')
        w('')
        w('  Signals observed:')
        for code, n in reason_counter.most_common():
            w(f'    {n:>5}  {code}')
        w('')
        w('  PROPOSED CLASSIFICATION (not applied):')
        for decision in ('ACCEPT', 'REVIEW', 'REJECT'):
            w(f'    {proposals.get(decision, 0):>5}  {decision}')
        w('')
        w('  Apply with:  python manage.py classify_notification_spam --confirm')
        w('  Nothing is ever hard-deleted; every change records previous_status.')
        w('')
