"""
companies/analyst.py — human analyst provenance (D3C-5).

The last writer family, and the only one allowed to say `confirmed`.

Every automated writer in the estate proposes. Ingestion proposes (#255), the
derived calculators propose (#249–#254), the seed commands propose (#247).
`review_status='confirmed'` means a person looked, and no code path may reach
it without one.

WHAT THIS DELIBERATELY IS NOT
-----------------------------
Not a dashboard. The brief for this phase asked for the smallest safe
workflow, and Django's admin already has authentication, permissions, an audit
of who is logged in, and a form layer. Building a second one would mean
re-implementing all of that less well.

So this module is a service, and the admin is one caller of it. A management
command or a future analyst UI can call the same function and inherit the same
guarantees.

THE GUARDRAIL THAT MATTERS
--------------------------
An analyst must not be able to label a derived value `MEASURED`.

`ml.score` is a gradient-boosting output. `company.ecoiq_total` is a composite.
`mizan.score` is a weighted model. None of them was measured by anyone, and
`MEASURED` is the origin that makes a metric publicly defensible — so a single
mislabelled composite would let a modelled number present itself as observed
fact.

The registry already refuses this: DERIVED metrics do not list MEASURED in
`allowed_origins`, so `provenance.record()` raises. This module surfaces that
as a readable error rather than a stack trace, and adds the rule the registry
cannot express — that a MEASURED declaration needs a source attached.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from companies import metric_registry as registry
from companies import provenance as prov
from companies.evidence import (
    PROVENANCE_ESTIMATED, PROVENANCE_INFERRED, PROVENANCE_MEASURED,
)

#: The only origins a human may declare.
#:
#: MODELLED is excluded because a person does not model a value by hand — a
#: calculator does, and it records its own lineage. SEEDED is excluded because
#: it describes demo data, not analysis. LEGACY_UNKNOWN_PROVENANCE is excluded
#: because it is a statement about what could not be reconstructed, which only
#: the backfill is in a position to make. UNKNOWN is excluded because declining
#: to declare is done by not declaring.
ANALYST_ORIGINS: tuple[str, ...] = (
    PROVENANCE_MEASURED,
    PROVENANCE_ESTIMATED,
    PROVENANCE_INFERRED,
)

#: Origins that assert the value came from an identified source document, and
#: therefore require one.
REQUIRES_EVIDENCE: frozenset[str] = frozenset({PROVENANCE_MEASURED})

ANALYST_WRITER = 'companies.analyst.declare_metric'


class AnalystDeclarationError(ValidationError):
    """A declaration that cannot be recorded honestly."""


def available_metrics() -> list[tuple[str, str]]:
    """Registry choices for a declaration form, material metrics first."""
    material = sorted(k for k, d in registry.REGISTRY.items()
                      if d.kind == registry.MATERIAL)
    derived = sorted(k for k, d in registry.REGISTRY.items()
                     if d.kind == registry.DERIVED)
    return ([(k, f'{registry.REGISTRY[k].label} — {k}') for k in material]
            + [(k, f'{registry.REGISTRY[k].label} — {k} (derived)') for k in derived])


def permitted_origins(metric_key: str) -> tuple[str, ...]:
    """
    Which of the analyst origins are honest for this metric.

    For a DERIVED metric this excludes MEASURED, because the registry says so.
    Exposed separately from validation so a form can narrow the dropdown rather
    than letting someone pick an option that will be rejected.
    """
    definition = registry.get_metric_definition(metric_key)
    if definition is None:
        return ()
    return tuple(o for o in ANALYST_ORIGINS if o in definition.allowed_origins)


def validate_declaration(metric_key: str, value, origin: str, *, evidence=None,
                         review_status: str = 'proposed', user=None) -> None:
    """
    Everything that must be true before a declaration is written.

    Raises AnalystDeclarationError with a message meant for a person.
    """
    definition = registry.get_metric_definition(metric_key)
    if definition is None:
        raise AnalystDeclarationError(f'{metric_key!r} is not a registered metric.')

    if origin not in ANALYST_ORIGINS:
        raise AnalystDeclarationError(
            f'{origin!r} cannot be declared by hand. An analyst may declare: '
            f'{", ".join(ANALYST_ORIGINS)}. MODELLED is recorded by the '
            'calculator that produced the value, and SEEDED by the seed '
            'command that wrote it.'
        )

    if origin not in definition.allowed_origins:
        raise AnalystDeclarationError(
            f'{origin!r} is not an honest origin for {metric_key!r}, which is a '
            f'{definition.kind} metric. {definition.label} is calculated from '
            'other metrics — nobody observed it directly. Allowed here: '
            f'{", ".join(sorted(permitted_origins(metric_key))) or "none"}.'
        )

    if value is None:
        raise AnalystDeclarationError(
            'A declaration needs a value. To record that a value is unknown, '
            'do not declare it — an absent metric is already unknown.'
        )

    if origin in REQUIRES_EVIDENCE and evidence is None:
        raise AnalystDeclarationError(
            f'{origin} asserts the value was taken from a source. Attach the '
            'evidence record it came from, or declare it as ESTIMATED or '
            'INFERRED instead.'
        )

    if review_status == 'confirmed':
        if user is None or not getattr(user, 'is_authenticated', False):
            raise AnalystDeclarationError(
                'Only a signed-in reviewer can confirm a declaration.')
        if not user.has_perm('companies.change_companymetricprovenance'):
            raise AnalystDeclarationError(
                'You do not have permission to confirm provenance. Save it as '
                'proposed and ask a reviewer.')


@transaction.atomic
def declare_metric(profile, metric_key: str, value, origin: str, *, user,
                   evidence=None, methodology: str = '', confidence=None,
                   review_status: str = 'proposed', notes: str = '',
                   source_quality: str = ''):
    """
    Write an analyst's declared value AND its provenance, atomically.

    The value goes to the metric's canonical field and the provenance row
    records who said so and on what basis. Doing one without the other is the
    failure mode D3C exists to prevent: a value with no provenance gets
    relabelled LEGACY_UNKNOWN_PROVENANCE by the next backfill, and a provenance
    row with no value asserts a number that was never stored.

    The previous row becomes history; this one becomes current. Nothing is
    edited in place, so "what did we believe last month, and who said it?"
    stays answerable.

    `confidence` stays None unless the analyst supplied one. A default here
    would be a fabricated statement about how much to trust a human judgement.

    Returns the new provenance row.
    """
    validate_declaration(metric_key, value, origin, evidence=evidence,
                         review_status=review_status, user=user)

    definition = registry.require_metric_definition(metric_key)
    _write_value(profile, definition, value)

    fields = {
        'written_by': ANALYST_WRITER,
        'created_by': user if getattr(user, 'is_authenticated', False) else None,
        'evidence': evidence,
        'methodology': methodology,
        'confidence': confidence,
        'notes': notes,
        'source_quality': source_quality,
        'review_status': review_status,
    }
    if review_status == 'confirmed':
        from django.utils import timezone

        fields['reviewed_by'] = user
        fields['reviewed_at'] = timezone.now()

    if definition.is_ephemeral:
        # No field holds it, so the row itself must carry the number.
        fields['recorded_value'] = value

    return prov.record(profile, metric_key, origin, **fields)


def _write_value(profile, definition, value) -> None:
    """
    Persist the declared value to its canonical field.

    Ephemeral metrics have no field; their value lives on the provenance row
    and is written by the caller above. Anything else is located through
    `value_location`, so this never guesses an attribute name.
    """
    if definition.is_ephemeral:
        return

    model_path, field = definition.value_location.rsplit('.', 1)

    if model_path == 'companies.CompanyProfile':
        setattr(profile, field, value)
        profile.save(update_fields=[field])
        return

    if model_path == 'league.Company':
        company = profile.company
        setattr(company, field, value)
        company.save(update_fields=[field])
        return

    raise AnalystDeclarationError(
        f'{definition.key!r} lives in {definition.value_location!r}, which this '
        'workflow cannot write to yet. Declaring it would record provenance for '
        'a value that was never stored.'
    )
