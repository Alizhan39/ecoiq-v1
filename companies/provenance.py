"""
Provenance service layer — D3A.

The single place that reads and writes CompanyMetricProvenance, so callers never
assemble rows by hand and the append-only discipline cannot be forgotten at one
call site out of thirty.

Scope, stated plainly: D3A records where a value came from. It does not decide
whether a value may be published (D5 owns eligibility thresholds), it does not
change any score field's nullability (D4), and no writer is wired up to it yet
(D3C). `is_publicly_defensible()` exists and is tested, but nothing on a public
path calls it — it is the hook D5 will use, placed now so the rules live in one
function rather than being reproduced in every template.

See docs/product/PROVENANCE_ARCHITECTURE.md for why the model is shaped this way.
"""
from __future__ import annotations

from django.db import transaction

from companies.evidence import (
    EVIDENCED_PROVENANCE, MATERIAL_INPUTS, PROVENANCE_CHOICES, PROVENANCE_NO_VALUE,
    PROVENANCE_SEEDED, UNEVIDENCED_PROVENANCE,
)

#: The metric keys provenance may be recorded for. MATERIAL_INPUTS is already the
#: repository's registry of material EcoIQ metrics — it carries the composite
#: weights, and coverage and eligibility already read from it. A second registry
#: table would add a migration and a join to restate the same fifteen names.
VALID_METRIC_KEYS: frozenset[str] = frozenset(i.field_name for i in MATERIAL_INPUTS)

VALID_ORIGINS: frozenset[str] = frozenset(code for code, _ in PROVENANCE_CHOICES)


def current(company, metric_key: str):
    """The current provenance row for one metric, or None if never recorded."""
    return company.metric_provenance.filter(
        metric_key=metric_key, is_current=True,
    ).select_related('evidence').first()


def current_map(company) -> dict:
    """
    Every current provenance row for a company, keyed by metric.

    One query. Callers rendering a whole profile must use this rather than
    calling current() fifteen times — that is the N+1 the brief warns about, and
    it is easier to avoid now than to find later.
    """
    rows = company.metric_provenance.filter(is_current=True).select_related('evidence')
    return {row.metric_key: row for row in rows}


@transaction.atomic
def record(company, metric_key: str, origin: str, **fields):
    """
    Record provenance for one metric, superseding any previous current row.

    Append-only: the prior row is marked is_current=False rather than updated in
    place, so the question "what did we think this value's origin was last
    month?" stays answerable. Atomic because a supersede followed by a failed
    insert would leave the metric with no current provenance at all — worse than
    the stale row it replaced.

    Returns the new row.
    """
    if metric_key not in VALID_METRIC_KEYS:
        raise ValueError(
            f'{metric_key!r} is not a material EcoIQ metric. '
            f'Valid keys come from companies.evidence.MATERIAL_INPUTS.'
        )
    if origin not in VALID_ORIGINS:
        raise ValueError(f'Unknown provenance state: {origin!r}.')

    from companies.models import CompanyMetricProvenance

    company.metric_provenance.filter(
        metric_key=metric_key, is_current=True,
    ).update(is_current=False)

    return CompanyMetricProvenance.objects.create(
        company=company, metric_key=metric_key, origin=origin,
        is_current=True, **fields,
    )


def history(company, metric_key: str):
    """Every provenance row ever recorded for one metric, newest first."""
    return company.metric_provenance.filter(
        metric_key=metric_key,
    ).select_related('evidence', 'reviewed_by').order_by('-created_at')


def is_publicly_defensible(company, metric_key: str) -> bool:
    """
    Could this metric be published on the strength of its provenance alone?

    ADVISORY IN D3A. Nothing on a public path calls this, and public eligibility
    is unchanged by this PR. It exists so that when D5 arrives the rules live in
    one function instead of being reproduced across templates and serializers.

    Returns False for:

      - no provenance row at all — the default state of every value today, and
        the honest answer for one whose origin has never been stated;
      - SEEDED — synthetic development data. Enforced here and by test, not only
        by documentation: "synthetic data may exercise the system, it must not
        impersonate evidence";
      - LEGACY_UNKNOWN_PROVENANCE — a real number whose lineage nobody can
        reconstruct;
      - UNKNOWN — there is no value to publish;
      - a metric_key that is not a material EcoIQ metric.

    It deliberately does NOT encode coverage thresholds, review requirements, or
    how many metrics a company needs before its composite is publishable. Those
    are D5's decisions and hard-coding a guess at them here would make them
    invisible when D5 comes to make them properly.
    """
    if metric_key not in VALID_METRIC_KEYS:
        return False

    row = current(company, metric_key)
    if row is None:
        return False
    if row.origin in UNEVIDENCED_PROVENANCE:
        return False

    # An origin can only defend a value that exists. A MEASURED row pointing at
    # a NULL field is a contradiction, and the safe reading of a contradiction is
    # that there is nothing to publish.
    return row.value is not None


def unrecorded_metrics(company) -> list[str]:
    """
    Material metrics with no current provenance row.

    The measurement D3B needs: how much of the estate still has no stated origin.
    """
    recorded = set(
        company.metric_provenance.filter(is_current=True).values_list('metric_key', flat=True)
    )
    return sorted(VALID_METRIC_KEYS - recorded)


def summarise(company) -> dict:
    """
    Provenance coverage for one company, as counts by origin.

    Metrics with no row are reported under PROVENANCE_NO_VALUE only when the
    field itself is empty; otherwise they are counted as 'unrecorded', which is
    a different thing and must not be confused with a stated UNKNOWN.
    """
    rows = current_map(company)
    by_origin: dict[str, int] = {}
    unrecorded_with_value = 0

    for metric_key in sorted(VALID_METRIC_KEYS):
        row = rows.get(metric_key)
        if row is not None:
            by_origin[row.origin] = by_origin.get(row.origin, 0) + 1
        elif getattr(company, metric_key, None) is None:
            by_origin[PROVENANCE_NO_VALUE] = by_origin.get(PROVENANCE_NO_VALUE, 0) + 1
        else:
            unrecorded_with_value += 1

    return {
        'total_metrics': len(VALID_METRIC_KEYS),
        'by_origin': by_origin,
        'unrecorded_with_value': unrecorded_with_value,
        'defensible': sum(
            1 for m in VALID_METRIC_KEYS if is_publicly_defensible(company, m)
        ),
    }


# ── Seed writes (D3C-1) ───────────────────────────────────────────────────────

class TrustedProvenanceOverwrite(Exception):
    """
    Raised when a seed write would overwrite trusted provenance.

    Deliberately an exception rather than a silent skip: seed commands run
    inside transaction.atomic(), so raising rolls the metric write back too.
    A skip would leave the value overwritten and its provenance stale — the two
    would disagree, which is the exact drift D3C-1 exists to prevent.
    """


def record_seed_write(profile, metric_keys, writer: str, *,
                      allow_trusted_overwrite: bool = False) -> list:
    """
    Record SEEDED provenance for metrics a seed command just wrote.

    THE CANONICAL ENTRY POINT for seed writers. Commands must not build
    CompanyMetricProvenance rows themselves — five commands assembling rows with
    slightly different semantics is how the vocabulary drifts, and D3B already
    showed what unrecoverable lineage costs.

    MUST be called inside the caller's transaction.atomic(), in the same block
    as the metric write. It does not open its own: an inner atomic() would
    create a savepoint that could commit independently of the value write, which
    is precisely the "value saved, provenance failed" split this prevents.

        with transaction.atomic():
            profile.save()
            record_seed_write(profile, defaults.keys(), 'seed:seed_companies')

    `metric_keys` may be any iterable — typically a defaults dict's keys. Only
    those that are material metrics are recorded; everything else is ignored, so
    a caller can hand over its whole defaults dict without filtering first.

    Returns the rows created, which is empty when every metric already carried
    identical seed provenance.
    """
    from companies.models import CompanyMetricProvenance

    material = sorted(set(metric_keys) & VALID_METRIC_KEYS)
    if not material:
        return []

    existing = {
        row.metric_key: row
        for row in profile.metric_provenance.filter(
            metric_key__in=material, is_current=True,
        )
    }

    # ── Trusted-data protection ───────────────────────────────────────────────
    #
    # A seed command must never silently overwrite an analyst decision or an
    # evidence-backed record. The check is on PROVENANCE, not on the value:
    # "this number looks real" is not a safeguard, but "someone recorded where
    # this came from and it was not a seeder" is.
    if not allow_trusted_overwrite:
        trusted = sorted(
            key for key, row in existing.items()
            if row.origin in EVIDENCED_PROVENANCE
        )
        if trusted:
            raise TrustedProvenanceOverwrite(
                f'{profile} — refusing to seed over trusted provenance on: '
                f'{", ".join(trusted)}. Pass allow_trusted_overwrite=True only '
                f'in development, and never to make a seed run succeed against '
                f'real data.'
            )

    # ── Churn control (STEP 10) ───────────────────────────────────────────────
    #
    # Re-running a seeder that writes the same value by the same writer is not a
    # new provenance event. Recording one anyway would grow history on every run
    # with no new information, and bury genuine origin changes in the noise.
    #
    # The identity is (origin, writer) — NOT the value. A seeder that changes a
    # company's score still records a new event, because what it did changed
    # even though who did it did not.
    to_write = [
        key for key in material
        if not (existing.get(key) is not None
                and existing[key].origin == PROVENANCE_SEEDED
                and existing[key].written_by == writer)
    ]
    if not to_write:
        return []

    # STEP 4 — supersede, never mutate. Prior MEASURED/MODELLED/analyst rows
    # stay in the table as history; only their is_current flag moves.
    profile.metric_provenance.filter(
        metric_key__in=to_write, is_current=True,
    ).update(is_current=False)

    return CompanyMetricProvenance.objects.bulk_create([
        CompanyMetricProvenance(
            company=profile,
            metric_key=key,
            origin=PROVENANCE_SEEDED,
            written_by=writer,
            notes='Synthetic development/demonstration value written by a seed command.',
            # STEP 6 — nothing fabricated. Seeded data has no evidence, no
            # confidence, no reviewer and no observation date, and inventing any
            # of them would let synthetic data impersonate the real thing.
            evidence=None,
            confidence=None,
            observed_at=None,
            review_status='proposed',
            reviewed_by=None,
            reviewed_at=None,
            is_current=True,
        )
        for key in to_write
    ])
