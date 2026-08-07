"""
Read-only analysis of existing AdminNotification records.

Writes nothing, and holds its transaction read-only so it cannot, even by
mistake. Prints aggregate statistics, the signals observed, the proposed
ACCEPT / REVIEW / REJECT split, and where that proposal disagrees with the
status the records already carry.

Never prints message bodies, contact names, full email addresses, IP addresses
or tokens — only counts, mailbox domains and truncated fingerprint prefixes.
"""
import collections
import hashlib
import json
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

from notifications.antispam.classify import (
    CLASSIFIER_VERSION, Corpus, SIGNALS, Strength, classify,
)
from notifications.antispam.fingerprint import submission_fingerprint
from notifications.models import AdminNotification

DECISIONS = ('ACCEPT', 'REVIEW', 'REJECT')

# Stored spam_status ↔ classifier decision. Anything else counts as "unset".
STATUS_TO_DECISION = {
    'accepted': 'ACCEPT',
    'review': 'REVIEW',
    'quarantined': 'REVIEW',
    'rejected': 'REJECT',
    'spam': 'REJECT',
}


def subject_of(record):
    return (record.metadata or {}).get('subject', '') or ''


def build_corpus(records):
    corpus = Corpus()
    for r in records:
        corpus.add(
            name=r.contact_name or '',
            email=r.contact_email or '',
            subject=subject_of(r),
            message=r.message or '',
            fingerprint=fingerprint_of(r),
        )
    return corpus


def fingerprint_of(record):
    return submission_fingerprint(
        email=record.contact_email or '',
        name=record.contact_name or '',
        subject=subject_of(record),
        message=record.message or '',
        form=record.source_type or '',
    )


DECISION_TO_STATUS = {'REJECT': 'rejected', 'REVIEW': 'review', 'ACCEPT': 'accepted'}

# A human has ruled on these; a batch job does not get to overrule them.
HUMAN_DECIDED = ('legitimate',)


def is_high_confidence(reasons):
    """True when at least one STRONG signal fired, not merely a pair of MEDIUMs."""
    return any(SIGNALS[c][0] is Strength.STRONG for c in reasons if c in SIGNALS)


def plan_transitions(records, corpus):
    """
    The single definition of "which rows would actually change", shared by the
    read-only analysis and the mutating command.

    They must agree exactly: the analysis prints the figure an operator passes
    to --expected-transitions, and the mutating command aborts if its own count
    differs. Two separate implementations would eventually disagree and the
    guard would fire on a correct run — or, worse, not fire on an incorrect one.

    Returns (planned, decisions, refused).

    Two guards live here rather than in the classifier, because they are about
    what a *bulk job* may do to stored rows, not about what a submission is:

      - An existing ACCEPT is never downgraded to REJECT automatically. A
        disagreement there is for a human to look at, not for a batch job.
      - REVIEW is promoted to REJECT only on high confidence — at least one
        STRONG signal. Two MEDIUM signals reject a live submission, but are not
        enough to relabel a row a human may already have seen in the queue.
    """
    planned = []
    decisions = collections.Counter()
    refused = collections.Counter()

    for r in records:
        decision, reasons = classify_record(r, corpus)
        decisions[decision] += 1
        current = r.spam_status
        target = DECISION_TO_STATUS[decision]

        if current in HUMAN_DECIDED:
            refused['human decision, left alone'] += 1
            continue
        if current == target:
            # Already there. Not a transition, and must not be counted as one.
            continue
        if current == 'accepted' and target == 'rejected':
            refused['accepted -> rejected, never automatic'] += 1
            continue
        if current == 'review' and target == 'rejected' and not is_high_confidence(reasons):
            refused['review -> rejected without a strong signal'] += 1
            continue

        planned.append((r, target, reasons))
    return planned, decisions, refused


def snapshot_hash(records, corpus):
    """
    Digest of (id, stored status, computed decision) over every record, in id
    order.

    This is the strictest of the expectation checks: the three counts can each
    stay the same while the underlying rows change (one record moves out of
    REJECT, another moves in). The digest cannot. An operator who supplies it is
    asserting "the table is exactly as I reviewed it", and any addition,
    removal, status edit or ruleset change invalidates it.

    Contains no message text, name, address or fingerprint — only primary keys
    and status strings.
    """
    h = hashlib.sha256()
    for record in sorted(records, key=lambda r: r.pk):
        decision, _reasons = classify_record(record, corpus)
        h.update(f'{record.pk}:{record.spam_status}:{decision}\n'.encode())
    return h.hexdigest()


def classify_record(record, corpus):
    return classify(
        name=record.contact_name or '',
        email=record.contact_email or '',
        subject=subject_of(record),
        message=record.message or '',
        fingerprint=fingerprint_of(record),
        corpus=corpus,
    )


class Command(BaseCommand):
    help = ('Read-only analysis of AdminNotification records with a proposed '
            'spam classification. Writes nothing.')

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Accepted for symmetry; this command is always read-only.')
        parser.add_argument('--source', default='', help='Limit to one source_type.')
        parser.add_argument('--days', type=int, default=0, help='Only records from the last N days.')
        parser.add_argument('--report', default='',
                            help='Also write the aggregate counts to this path as JSON. '
                                 'Contains counts only — no record content.')

    def handle(self, *args, **options):
        # Belt and braces: a read-only transaction means an accidental write in
        # this command, or in anything it calls, fails loudly instead of landing.
        with transaction.atomic():
            self._set_read_only()
            self._analyse(options)

    def _set_read_only(self):
        if connection.vendor == 'postgresql':
            with connection.cursor() as cur:
                cur.execute('SET TRANSACTION READ ONLY')

    def _analyse(self, options):
        qs = AdminNotification.objects.all()
        if options['source']:
            qs = qs.filter(source_type=options['source'])
        if options['days']:
            qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=options['days']))

        records = list(qs.only(
            'id', 'contact_name', 'contact_email', 'message', 'metadata',
            'source_type', 'status', 'spam_status', 'created_at'))
        total = len(records)
        if not total:
            self.stdout.write('No notifications matched.')
            return

        corpus = build_corpus(records)

        proposals = collections.Counter()
        reason_counter = collections.Counter()
        transitions = collections.Counter()
        current_counter = collections.Counter()

        for r in records:
            decision, reasons = classify_record(r, corpus)
            proposals[decision] += 1
            for code in reasons:
                reason_counter[code] += 1
            current = STATUS_TO_DECISION.get((r.spam_status or '').lower(), 'UNSET')
            current_counter[current] += 1
            if current != decision:
                transitions[(current, decision)] += 1

        domains = collections.Counter(
            (r.contact_email or '').rpartition('@')[2].lower()
            for r in records if '@' in (r.contact_email or ''))

        dup_groups = sum(1 for c in corpus.fingerprint_counts.values() if c > 1)
        dup_records = sum(c for c in corpus.fingerprint_counts.values() if c > 1)
        name_spread = sorted(
            ((len(emails), name) for name, emails in corpus.emails_by_name.items()),
            reverse=True)
        unread = sum(1 for r in records if r.status == 'unread')
        earliest = min(r.created_at for r in records)
        latest = max(r.created_at for r in records)
        disagreements = sum(transitions.values())

        w = self.stdout.write
        w('')
        w('  ANALYSIS — read-only, nothing was modified')
        w(f'  classifier {CLASSIFIER_VERSION}')
        w('  ' + '─' * 62)
        w(f'  total records              {total}')
        w(f'  unread                     {unread}')
        w(f'  distinct contact names     {len(corpus.emails_by_name)}')
        w(f'  distinct email domains     {len(domains)}')
        w(f'  duplicate fingerprints     {dup_records} records across {dup_groups} groups')
        w(f'  window                     {earliest:%Y-%m-%d %H:%M} → {latest:%Y-%m-%d %H:%M} UTC')
        w('')
        w('  Name spread — distinct addresses per contact name (no names shown):')
        for rank, (n_emails, _name) in enumerate(name_spread[:5], start=1):
            w(f'    #{rank}  {n_emails:>5} distinct addresses')
        if len(name_spread) > 5:
            w(f'    … {len(name_spread) - 5} further names')
        w('')
        w('  Most common mailbox domains:')
        for dom, n in domains.most_common(8):
            w(f'    {n:>5}  {dom}')
        w('')
        w('  Signals observed (a record can carry several):')
        for code, n in reason_counter.most_common():
            strength = SIGNALS[code][0].value
            w(f'    {n:>5}  {code}  [{strength}]')
        w('')
        w('  CURRENT stored classification:')
        for key in ('UNSET',) + DECISIONS:
            w(f'    {current_counter.get(key, 0):>5}  {key}')
        w('')
        w('  PROPOSED classification (not applied):')
        for decision in DECISIONS:
            w(f'    {proposals.get(decision, 0):>5}  {decision}')
        w('')
        w(f'  DISAGREEMENTS with what is stored: {disagreements}')
        if transitions:
            for (current, proposed), n in transitions.most_common():
                w(f'    {n:>5}  {current:<7} → {proposed}')
        else:
            w('    none — stored classification already matches')
        w('')
        planned, _decisions, refused = plan_transitions(records, corpus)
        digest = snapshot_hash(records, corpus)
        w('')
        w(f'  ROWS THAT WOULD ACTUALLY CHANGE: {len(planned)}')
        if refused:
            w('  refused by a bulk-job guard (counted as no change):')
            for reason, n in sorted(refused.items()):
                w(f'    {n:>5}  {reason}')
        w(f'  SNAPSHOT HASH  {digest}')
        w('')
        w('  Apply with (every figure below is checked before any write):')
        w('    python manage.py classify_notification_spam --confirm \\')
        w(f'      --expected-total {total} \\')
        w(f'      --expected-reject-count {proposals.get("REJECT", 0)} \\')
        w(f'      --expected-transitions {len(planned)} \\')
        w(f'      --snapshot-hash {digest}')
        w('  Nothing is ever hard-deleted; every change records previous_status.')
        w('')

        if options['report']:
            payload = {
                'classifier_version': CLASSIFIER_VERSION,
                'generated_at': timezone.now().isoformat(),
                'total_records': total,
                'window_start': earliest.isoformat(),
                'window_end': latest.isoformat(),
                'distinct_names': len(corpus.emails_by_name),
                'distinct_domains': len(domains),
                'duplicate_records': dup_records,
                'duplicate_groups': dup_groups,
                'max_distinct_emails_per_name': name_spread[0][0] if name_spread else 0,
                'signals': dict(reason_counter),
                'current': dict(current_counter),
                'proposed': dict(proposals),
                'transitions': {f'{a}->{b}': n for (a, b), n in transitions.items()},
            }
            with open(options['report'], 'w', encoding='utf-8') as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
            w(f'  Aggregate counts written to {options["report"]} (counts only).')
            w('')
