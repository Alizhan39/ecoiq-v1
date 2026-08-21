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

from companies import metric_registry as registry
from companies.evidence import (
    EVIDENCED_PROVENANCE, MATERIAL_INPUTS, PROVENANCE_CHOICES, PROVENANCE_MODELLED,
    PROVENANCE_NO_VALUE, PROVENANCE_SEEDED, UNEVIDENCED_PROVENANCE,
)

#: Every key provenance may be recorded for — material AND derived (D3C-2).
#:
#: MATERIAL_INPUTS remains the canonical list for material COVERAGE: it carries
#: the composite weights that coverage_for() and eligibility() read, and D3C-2
#: deliberately does not migrate them. What changes is only which keys
#: provenance accepts, which now includes registered derived metrics.
VALID_METRIC_KEYS: frozenset[str] = registry.VALID_KEYS

#: The material subset, unchanged in meaning. Callers that mean "the sixteen
#: assessed inputs" — seed writers, coverage — must use this, not VALID_METRIC_KEYS.
MATERIAL_METRIC_KEYS: frozenset[str] = frozenset(i.field_name for i in MATERIAL_INPUTS)

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
    definition = registry.require_metric_definition(metric_key)
    if origin not in VALID_ORIGINS:
        raise ValueError(f'Unknown provenance state: {origin!r}.')
    if origin not in definition.allowed_origins:
        raise ValueError(
            f'{origin!r} is not an honest origin for {metric_key!r} '
            f'({definition.kind}). Allowed: '
            f'{", ".join(sorted(definition.allowed_origins))}.'
        )

    from companies.models import CompanyMetricProvenance

    company.metric_provenance.filter(
        metric_key=metric_key, is_current=True,
    ).update(is_current=False)

    return CompanyMetricProvenance.objects.create(
        company=company, metric_key=metric_key, origin=origin,
        is_current=True, **fields,
    )


def supersede(profile, metric_key: str) -> int:
    """
    Mark a metric's current provenance historical WITHOUT recording a new row.

    D3C-3b needs this for the case where a derived value becomes unavailable:
    a calculation that previously produced a number now returns None because
    the evidence no longer supports it.

    Leaving the old row marked current would be the provenance layer asserting
    that a superseded calculation still describes the current state — which is
    the same class of untruth as a stale score. Superseding says instead: this
    is what we used to think, and we no longer have a current answer.

    Returns the number of rows superseded (0 or 1).
    """
    return profile.metric_provenance.filter(
        metric_key=metric_key, is_current=True,
    ).update(is_current=False)


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
    MATERIAL metrics with no current provenance row.

    Material-scoped on purpose. D3C-2 widened VALID_METRIC_KEYS to include
    derived metrics, and counting an unrecorded derived metric here would say
    the estate is less covered than it is — a derived metric with no provenance
    has simply not been calculated through a wired-up writer yet, which is a
    different fact from a material input whose origin nobody stated.
    """
    recorded = set(
        company.metric_provenance.filter(is_current=True).values_list('metric_key', flat=True)
    )
    return sorted(MATERIAL_METRIC_KEYS - recorded)


def summarise(company) -> dict:
    """
    MATERIAL provenance coverage for one company, as counts by origin.

    Metrics with no row are reported under PROVENANCE_NO_VALUE only when the
    field itself is empty; otherwise they are counted as 'unrecorded', which is
    a different thing and must not be confused with a stated UNKNOWN.
    """
    rows = current_map(company)
    by_origin: dict[str, int] = {}
    unrecorded_with_value = 0

    for metric_key in sorted(MATERIAL_METRIC_KEYS):
        row = rows.get(metric_key)
        if row is not None:
            by_origin[row.origin] = by_origin.get(row.origin, 0) + 1
        elif getattr(company, metric_key, None) is None:
            by_origin[PROVENANCE_NO_VALUE] = by_origin.get(PROVENANCE_NO_VALUE, 0) + 1
        else:
            unrecorded_with_value += 1

    return {
        'total_metrics': len(MATERIAL_METRIC_KEYS),
        'by_origin': by_origin,
        'unrecorded_with_value': unrecorded_with_value,
        'defensible': sum(
            1 for m in MATERIAL_METRIC_KEYS if is_publicly_defensible(company, m)
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

    # MATERIAL_METRIC_KEYS, not VALID_METRIC_KEYS: a seeder hands over its
    # profile_defaults, which now overlaps derived keys too (ecoiq_total_score
    # is written by seeders). Those are recorded by the calculation that
    # produces them, not by the command that triggered it.
    material = sorted(set(metric_keys) & MATERIAL_METRIC_KEYS)
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


# ── Derived metrics (D3C-2) ───────────────────────────────────────────────────

class LineageCycle(Exception):
    """Raised when a provenance row would list itself among its own inputs."""


def record_derived(profile, metric_key: str, *, writer: str, methodology: str,
                   calculation_version: str, inputs=None, recorded_value=None,
                   origin=PROVENANCE_MODELLED, **fields):
    """
    Record provenance for a calculated metric.

    MUST be called inside the caller's transaction.atomic(), alongside whatever
    persisted the value — same rule and same reason as record_seed_write().

    `methodology` and `calculation_version` are REQUIRED, unlike on the base
    record(). A modelled value is only as attributable as the model behind it,
    and a MODELLED row with no version cannot answer "which formula produced
    this?" — the question derived provenance exists for.

    `inputs` is an iterable of CompanyMetricProvenance rows the calculation
    ACTUALLY consumed. Not the rows the formula mentions: a calculation that
    re-normalised around an unknown input did not consume it, and listing it
    would overstate the lineage. The D2 work makes this knowable — _weighted()
    and mean_of_known() already track which inputs they used, because they had
    to in order to re-normalise.

    `recorded_value` is required for an ephemeral metric and rejected for any
    other. See CompanyMetricProvenance.recorded_value.

    Returns the new row.
    """
    from companies.models import CompanyMetricProvenance

    definition = registry.require_metric_definition(metric_key)

    if not methodology or not calculation_version:
        raise ValueError(
            f'{metric_key!r}: methodology and calculation_version are required '
            f'for a derived metric. Without them the row records that something '
            f'was computed but not what computed it.'
        )
    if definition.is_ephemeral and recorded_value is None:
        raise ValueError(
            f'{metric_key!r} is ephemeral, so its provenance must carry the '
            f'value it was recorded for — nothing else can reconstruct it.'
        )

    row = record(
        profile, metric_key, origin,
        written_by=writer, methodology=methodology,
        calculation_version=calculation_version,
        recorded_value=recorded_value, **fields,
    )

    if inputs:
        input_rows = list(inputs)
        # STEP 8 — a row must never be its own input. Full DAG validation across
        # the whole graph is deferred (documented in DERIVED_METRIC_REGISTRY.md);
        # direct self-reference is the case that is both cheap to detect and
        # certain to be wrong.
        if any(candidate.pk == row.pk for candidate in input_rows):
            raise LineageCycle(
                f'{metric_key!r}: a provenance row cannot be its own input.'
            )
        row.inputs.set(input_rows)

    return row


def lineage(row) -> list:
    """
    The provenance rows one derived row was calculated from.

    Returns what was consumed AT CALCULATION TIME, including rows that have
    since been superseded — which is the point. Re-reading current input
    provenance would answer a different question.
    """
    return list(row.inputs.select_related('evidence').all())


def record_calculated(profile, metric_key: str, value, declared, *, writer: str,
                      methodology: str, calculation_version: str) -> str:
    """
    Record MODELLED lineage for one calculated value, or explain why not.

    The rules proven across #249, #250 and #251, extracted here so the
    financing and QDF writers inherit them rather than restating them. Three
    copies of a policy is three places for it to drift, and the policy is the
    part that matters.

    MUST be called inside the caller's transaction.atomic().

    Returns 'recorded' | 'unchanged' | 'incomplete' | 'unavailable'.
    """
    # No value, so nothing to attest to — and any previous row must stop
    # claiming to describe current state.
    if value is None:
        supersede(profile, metric_key)
        return 'unavailable'

    # Only the inputs that exist: a formula that re-normalised around an
    # unknown input did not consume it.
    consumed = [
        key for key in declared
        if registry.resolve_value(profile, key) is not None
    ]
    current_rows = current_map(profile)
    missing = [key for key in consumed if key not in current_rows]
    if not consumed or missing:
        # No lineage-complete row rather than one whose input list
        # understates what the number rests on. Nothing is fabricated, and no
        # LEGACY row is invented — D3B owns historical labelling.
        return 'incomplete'

    input_rows = [current_rows[key] for key in consumed]
    definition = registry.require_metric_definition(metric_key)
    ephemeral = definition.is_ephemeral

    existing = current(profile, metric_key)
    same_lineage = (
        existing is not None
        and existing.origin == PROVENANCE_MODELLED
        and existing.methodology == methodology
        and existing.calculation_version == calculation_version
        and set(existing.inputs.values_list('pk', flat=True))
            == {row.pk for row in input_rows}
    )

    # EPHEMERAL METRICS ADD THE OUTPUT TO THE IDENTITY, and persisted ones
    # deliberately do not. The asymmetry is not an inconsistency.
    #
    # For a persisted metric the comparison is impossible: `existing.value`
    # resolves live through the registry, and the new number has already been
    # written by the time this runs, so it always matches (#249 shipped that
    # bug before a test caught it). It is also unnecessary — the formula is
    # deterministic over its input rows.
    #
    # For an ephemeral metric neither holds. recorded_value is stored
    # immutably on the row, so the comparison genuinely fires; and the
    # determinism assumption can fail, because a calculator may read inputs
    # that are not registered metrics and therefore leave no provenance row —
    # a categorical field, a verification flag, a status. When one of those
    # changes, the lineage is identical and the answer is not.
    #
    # Comparing the output is the smallest representation that catches this
    # without inventing an opaque parameter blob: if an unrepresented input
    # moved the number, the number says so.
    if same_lineage and (not ephemeral or existing.recorded_value == value):
        return 'unchanged'

    record_derived(
        profile, metric_key, writer=writer, methodology=methodology,
        calculation_version=calculation_version, inputs=input_rows,
        recorded_value=value if ephemeral else None,
    )
    return 'recorded'


def is_derived_publicly_defensible(profile, metric_key: str) -> bool:
    """
    Could a derived metric be published, on provenance grounds alone?

    ADVISORY. Nothing on a public path calls this.

    A derived metric needs BOTH:

      1. its own origin to be defensible — MODELLED qualifies, SEEDED does not;
      2. every input it consumed to be defensible, TRANSITIVELY.

    The word transitively is doing real work, and D3C-3c is why. Once the graph
    gained a middle layer, the composite stopped citing material rows directly:
    it cites the pillars, which are MODELLED. A single-level check would see
    five honest MODELLED inputs and pass — while a SEEDED water reading sat one
    layer below, invisible.

    That is laundering by indirection, and a deeper graph is exactly what makes
    it easy. Contamination anywhere beneath a value disqualifies it.

    A derived row with NO recorded inputs returns False: we cannot show the
    lineage, so we cannot defend it.

    Deliberately NOT included: coverage thresholds, or how many inputs a
    composite needs. Those are D5's.
    """
    definition = registry.get_metric_definition(metric_key)
    if definition is None or definition.kind != registry.DERIVED:
        return False

    row = current(profile, metric_key)
    return row is not None and _row_is_defensible(row, seen=set())


def _row_is_defensible(row, seen: set) -> bool:
    """
    Whether one provenance row and everything beneath it is defensible.

    `seen` guards against a cycle. record_derived() rejects direct
    self-reference, but full DAG validation is still deferred, so a traversal
    must not assume the graph is acyclic. A row already being examined is
    treated as not-yet-disqualifying rather than recursed into again.
    """
    if row.pk in seen:
        return True
    seen.add(row.pk)

    if row.origin in UNEVIDENCED_PROVENANCE:
        return False
    if row.value is None:
        # A MEASURED row over a NULL field is a contradiction, and the safe
        # reading of a contradiction is that there is nothing to publish.
        return False

    inputs = list(row.inputs.all())
    if not inputs:
        # A MATERIAL row has no inputs and needs none — its own origin is the
        # whole claim. A DERIVED row with none cannot show its lineage.
        definition = registry.get_metric_definition(row.metric_key)
        return definition is not None and definition.kind == registry.MATERIAL

    return all(_row_is_defensible(item, seen) for item in inputs)
