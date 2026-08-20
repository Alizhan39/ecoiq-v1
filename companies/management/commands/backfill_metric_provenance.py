"""
D3B — deterministic legacy provenance labelling.

Records the FIRST known provenance state for metric values that predate D3.
Labels only. It changes no metric value, no scoring, no schema, and wires up no
live writer — those are D3C and D4.

The rule this command exists to obey:

    lineage can be PROVEN   -> record the proven origin
    lineage cannot be proven -> LEGACY_UNKNOWN_PROVENANCE

Provenance is never inferred from the number. 50 does not imply unknown, 72 does
not imply modelled, 0 does not imply measured. See STEP 4 below for what counts
as proof, and — more importantly — what does not.

Not run at deploy time. Not in start.sh, not in predeploy.sh, not in a
migration. An explicit operator action, because labelling 3000 rows is a
decision, not a deploy side effect.

    python manage.py backfill_metric_provenance              # dry run, no writes
    python manage.py backfill_metric_provenance --apply
    python manage.py backfill_metric_provenance --rollback --apply
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from companies.evidence import (
    PROVENANCE_NO_VALUE, PROVENANCE_SEEDED, PROVENANCE_UNKNOWN,
)
from companies.models import CompanyMetricProvenance, CompanyProfile
from companies.provenance import VALID_METRIC_KEYS

#: Tags every row this command writes, so rollback can remove exactly its own
#: work and nothing else. Never widen this filter.
WRITER = 'd3b_backfill'


def seed_lineage_reason(profile) -> str | None:
    """
    Why this profile's metrics are PROVABLY seed-generated — or None.

    STEP 4. The bar is deliberately high, and two tempting signals are rejected:

      * "the value equals the model default" — this is what D3A's
        field_provenance() used, and it is the brief's own example of
        UNACCEPTABLE evidence. A company genuinely measured at 50 is
        indistinguishable from a seeded 50 by value alone. That is the entire
        reason provenance exists as a separate record.

      * "the company appears in a seed command" — not enough on its own. A
        company can be created by a seed command and later have individual
        metrics overwritten by ingestion or an analyst, and this command cannot
        see which.

    What IS accepted is the conjunction of a NAMED seed command and the absence
    of any other writer ever having touched the profile:

      1. ai_summary carries one of mizan.scoring._PLACEHOLDER_MARKERS — an
         existing, already-relied-upon marker that names the writing command
         ('seeded by', 'add_400_companies', 'focus_target_markets'), or flags
         the text as placeholder; AND
      2. nothing else has ever written to this profile: no ingestion log, no
         non-seed score snapshot, no cited source, not analyst-verified.

    Together those establish seed-only lineage for the whole profile, which is
    per-metric lineage for every metric on it — a "unique seed-only writer
    pattern" in the brief's terms, not a guess about a number.

    Returns a short human-readable reason for the audit trail, or None.
    """
    from mizan.scoring import _PLACEHOLDER_MARKERS

    summary = (getattr(profile, 'ai_summary', '') or '').lower()
    marker = next((m for m in _PLACEHOLDER_MARKERS if m in summary), None)
    if marker is None:
        return None

    # Any of these means a non-seed writer has touched this profile, so the
    # seed command is no longer the only possible origin of its metrics.
    if getattr(profile, 'is_verified', False):
        return None
    if profile.cited_sources.exists():
        return None
    if profile.score_snapshots.exclude(trigger='seed').exists():
        return None
    if profile.company_id and profile.company.ingestion_logs.exists():
        return None

    return f'seed marker {marker!r} in ai_summary; no other writer touched this profile'


class Command(BaseCommand):
    help = ('D3B — record deterministic provenance for legacy metric values. '
            'Dry run by default; pass --apply to write.')

    #: Class-level default so that dry-run is the behaviour of any code path
    #: that has not explicitly opted into writing — including a caller that
    #: reaches _process_profile() without going through handle(). Writing must
    #: be opted into, never fallen into.
    apply = False

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='Actually write. Without it the command performs zero database writes.',
        )
        parser.add_argument(
            '--rollback', action='store_true',
            help=f"Remove only rows written_by='{WRITER}'. Never touches provenance "
                 f'from any other source.',
        )
        parser.add_argument('--company', help='Limit to one company slug.')
        parser.add_argument('--metric', help='Limit to one material metric key.')
        parser.add_argument('--limit', type=int, help='Process at most N profiles.')

    # ── Entry point ───────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        self.apply = options['apply']
        if options['rollback']:
            return self._rollback()

        metric_filter = options.get('metric')
        if metric_filter and metric_filter not in VALID_METRIC_KEYS:
            self.stderr.write(self.style.ERROR(
                f'{metric_filter!r} is not a material EcoIQ metric.'))
            return

        metrics = [metric_filter] if metric_filter else sorted(VALID_METRIC_KEYS)

        profiles = CompanyProfile.objects.select_related('company').prefetch_related(
            # 2976 pairs is small, but the seed-lineage check touches four
            # relations per profile; prefetching keeps this one pass over the
            # data rather than 186 x 4 extra queries.
            'cited_sources', 'score_snapshots', 'company__ingestion_logs',
        ).order_by('company__slug')
        if options.get('company'):
            profiles = profiles.filter(company__slug=options['company'])
        if options.get('limit'):
            profiles = profiles[:options['limit']]

        stats = {
            'companies_scanned': 0, 'metrics_scanned': len(metrics),
            'pairs_considered': 0, 'existing_skipped': 0,
            'seeded': 0, 'legacy': 0, 'unknown': 0,
            'conflicts': 0, 'errors': 0, 'written': 0,
        }
        seed_reasons: dict[str, str] = {}

        self._banner(options)

        for profile in profiles:
            stats['companies_scanned'] += 1
            try:
                self._process_profile(profile, metrics, stats, seed_reasons)
            except Exception as exc:               # noqa: BLE001 — reported, not swallowed
                stats['errors'] += 1
                self.stderr.write(self.style.ERROR(
                    f'  {profile.company.slug}: {exc}'))

        self._report(stats, seed_reasons)

    # ── Per-profile work ──────────────────────────────────────────────────────

    def _process_profile(self, profile, metrics, stats, seed_reasons):
        """
        Classify and (optionally) write one profile's metrics.

        TRANSACTION GRANULARITY: one atomic block PER COMPANY.

        Not one transaction for the whole run: 186 companies is small today but
        this command is meant to run against production, and a single failure at
        company 150 would roll back 149 companies of correct work for no reason —
        the classifications are independent.

        Not one transaction per metric either: a company left with provenance on
        nine of its sixteen metrics is a genuinely confusing half-state to
        inspect, whereas a company with none is simply unprocessed and the
        command is idempotent, so re-running finishes the job.

        The company is therefore the unit of work: all-or-nothing per company,
        independent across companies.
        """
        reason = seed_lineage_reason(profile)
        if reason:
            seed_reasons[profile.company.slug] = reason

        existing = set(
            profile.metric_provenance.filter(is_current=True)
            .values_list('metric_key', flat=True)
        )

        planned = []
        for metric_key in metrics:
            stats['pairs_considered'] += 1

            # STEP 3 — never overwrite provenance from any other source. An
            # analyst decision, an evidence-backed record or a D3C writer all
            # outrank a backfill label, and this command has no basis to
            # second-guess them.
            if metric_key in existing:
                stats['existing_skipped'] += 1
                continue

            value = getattr(profile, metric_key, None)
            if value is None:
                # STEP 6 — no value exists, so there is nothing whose lineage
                # could be established.
                origin, note = PROVENANCE_NO_VALUE, 'No value stored at backfill time.'
                stats['unknown'] += 1
            elif reason:
                origin, note = PROVENANCE_SEEDED, reason
                stats['seeded'] += 1
            else:
                # STEP 5 — a value exists and nothing proves where it came from.
                # No fake evidence, no fake reviewer, no fake confidence.
                origin = PROVENANCE_UNKNOWN
                note = ('Value predates provenance recording; no seed marker and no '
                        'other writer lineage could be established.')
                stats['legacy'] += 1

            planned.append((metric_key, origin, note))

        if not planned or not self.apply:
            return

        with transaction.atomic():
            CompanyMetricProvenance.objects.bulk_create([
                CompanyMetricProvenance(
                    company=profile,
                    metric_key=metric_key,
                    origin=origin,
                    notes=note,
                    written_by=WRITER,
                    # STEP 10 — the backfill time is NOT the observation time.
                    observed_at=None,
                    # STEP 11 — classification is not human verification.
                    review_status='proposed',
                    reviewed_by=None,
                    reviewed_at=None,
                    # STEP 5 — never fabricated.
                    confidence=None,
                    evidence=None,
                    # STEP 9 — the first known provenance state, not a rewrite
                    # of history that did not happen.
                    is_current=True,
                )
                for metric_key, origin, note in planned
            ])
            stats['written'] += len(planned)

    # ── Rollback ──────────────────────────────────────────────────────────────

    def _rollback(self):
        """
        Remove only what this command wrote.

        The filter is written_by=WRITER and nothing else. Provenance recorded by
        an analyst, by evidence ingestion or by a D3C writer is never in scope,
        which is the whole point of tagging the rows on the way in.
        """
        qs = CompanyMetricProvenance.objects.filter(written_by=WRITER)
        count = qs.count()
        other = CompanyMetricProvenance.objects.exclude(written_by=WRITER).count()

        self.stdout.write(f'Rows written by {WRITER!r}: {count}')
        self.stdout.write(f'Rows from other sources (never touched): {other}')

        if not self.apply:
            self.stdout.write(self.style.WARNING(
                'DRY RUN — nothing deleted. Re-run with --apply to remove them.'))
            return

        with transaction.atomic():
            deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted} backfill row(s).'))

    # ── Output ────────────────────────────────────────────────────────────────

    def _banner(self, options):
        mode = 'APPLY — writing' if self.apply else 'DRY RUN — no database writes'
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'D3B deterministic provenance backfill  [{mode}]'))
        scope = []
        if options.get('company'):
            scope.append(f"company={options['company']}")
        if options.get('metric'):
            scope.append(f"metric={options['metric']}")
        if options.get('limit'):
            scope.append(f"limit={options['limit']}")
        if scope:
            self.stdout.write(f'  scope: {", ".join(scope)}')
        self.stdout.write('')

    def _report(self, stats, seed_reasons):
        self.stdout.write('')
        self.stdout.write('  Companies scanned                  %d' % stats['companies_scanned'])
        self.stdout.write('  Metrics scanned                    %d' % stats['metrics_scanned'])
        self.stdout.write('  Pairs considered                   %d' % stats['pairs_considered'])
        self.stdout.write('  Existing provenance skipped        %d' % stats['existing_skipped'])
        self.stdout.write('  SEEDED candidates                  %d' % stats['seeded'])
        self.stdout.write('  LEGACY_UNKNOWN_PROVENANCE          %d' % stats['legacy'])
        self.stdout.write('  UNKNOWN candidates                 %d' % stats['unknown'])
        self.stdout.write('  Conflicts                          %d' % stats['conflicts'])
        self.stdout.write('  Errors                             %d' % stats['errors'])
        self.stdout.write('  Rows written                       %d' % stats['written'])

        if seed_reasons:
            self.stdout.write('')
            self.stdout.write('  Seed lineage established for %d company/companies:'
                              % len(seed_reasons))
            for slug, reason in list(seed_reasons.items())[:10]:
                self.stdout.write(f'    {slug}: {reason}')
        elif stats['pairs_considered']:
            self.stdout.write('')
            self.stdout.write(
                '  No profile carried provable seed lineage, so nothing was\n'
                '  classified SEEDED. This is the honest result on this dataset,\n'
                '  not a failure: a value equal to the model default is NOT proof\n'
                '  of seeding, and this command will not treat it as such.')

        if not self.apply and stats['pairs_considered']:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                'DRY RUN — nothing written. Re-run with --apply to record these.'))
