"""
platform_registry/stats.py — the single source of truth for platform counters.

Every number EcoIQ shows about itself comes from here. Nothing may hard-code a
count in a template, a view, a serializer, a README or a meta tag.

WHY
---
The repository contained competing hard-coded claims: 218 companies, 400
companies, 467 companies, "33 agents", "12 agents", "14 agents", "16 agents".
Some were true once. All of them drift the moment the database changes, and a
number that drifts silently is indistinguishable from one that was invented.

Every counter here is derived from the database or from the code-owned module
registry. There is no third category.

THE HARD PART IS WHAT NOT TO COUNT
----------------------------------
`companies_total` is easy and nearly useless on its own: 467 rows, of which
zero have publishable assessments. Presenting that as "467 companies analysed"
would be true about the table and false about the product.

So the counters that matter are the qualified ones — how many are PUBLISHED,
how many have any evidence at all — and `None` is a legitimate answer. A
counter with no meaningful value returns None so the caller renders nothing
rather than a confident zero.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Counter:
    """
    One platform figure.

    `value` may be None, which means "no meaningful figure" and must render as
    nothing or an em dash — never as 0. A zero is a measurement; None is the
    absence of one, and the difference is the whole programme.
    """
    key: str
    label: str
    value: int | None
    #: One line a person could verify. A counter without a stated derivation is
    #: indistinguishable from a hard-coded one.
    derivation: str
    #: True when the figure is safe to show publicly as product proof.
    #: A count of rows in a table is not proof of anything.
    is_proof: bool = False

    @property
    def display(self) -> str:
        return '—' if self.value is None else f'{self.value:,}'


def _company_counters() -> list:
    from companies.eligibility import decide
    from companies.models import CompanyProfile
    from league.models import Company

    from companies.evidence import EVIDENCED_MATERIAL_ORIGINS
    from companies.models import CompanyMetricProvenance

    total = Company.objects.count()

    # ONE query for the evidenced set, not one per company.
    #
    # The obvious implementation calls coverage_for() on every profile, which
    # is ~2 queries each -- around a thousand for a homepage counter. It is
    # also unnecessary: a company with no evidenced provenance row cannot have
    # coverage, so the row table answers the first question directly.
    evidenced_ids = set(
        CompanyMetricProvenance.objects
        .filter(is_current=True, origin__in=EVIDENCED_MATERIAL_ORIGINS)
        .values_list('company_id', flat=True)
        .distinct()
    )
    with_evidence = len(evidenced_ids)

    # Publication still needs the real decision, but only the evidenced set can
    # possibly pass it -- so the expensive loop is bounded by what is actually
    # publishable rather than by the size of the table.
    published = sum(
        1 for profile in CompanyProfile.objects
        .filter(pk__in=evidenced_ids).select_related('company')
        if decide(profile).is_published
    )

    return [
        Counter('companies_total', 'Organisations in the database', total,
                'COUNT(league_company)'),
        Counter('companies_with_evidence',
                'Organisations with at least one evidenced input',
                with_evidence,
                'Profiles whose coverage report has covered_inputs > 0',
                is_proof=True),
        Counter('companies_published', 'Organisations with a published score',
                published,
                'Profiles for which eligibility.decide() returns PUBLISHED',
                is_proof=True),
    ]


def _country_counter() -> Counter:
    from league.models import Company

    countries = (Company.objects.exclude(country='')
                 .values_list('country', flat=True).distinct().count())
    return Counter('countries_total', 'Countries represented', countries,
                   'DISTINCT league_company.country, excluding blank')


def _evidence_counters() -> list:
    from companies.models import CompanyMetricProvenance

    rows = CompanyMetricProvenance.objects.filter(is_current=True).count()
    evidenced = CompanyMetricProvenance.objects.filter(
        is_current=True,
        origin__in=('MEASURED', 'INFERRED', 'ESTIMATED')).count()

    return [
        Counter('provenance_rows_current', 'Current provenance records', rows,
                'COUNT(CompanyMetricProvenance WHERE is_current)'),
        Counter('evidenced_metrics', 'Metrics backed by evidenced provenance',
                evidenced,
                "Current provenance rows whose origin is MEASURED, INFERRED "
                'or ESTIMATED',
                is_proof=True),
    ]


def _project_counters() -> list:
    """
    Projects, and how many are verified.

    Returns None rather than 0 when the table is empty: "0 verified projects"
    invites the reader to conclude the projects failed verification, when in
    fact none has been through it.
    """
    try:
        from league.models import EnvironmentalProject
    except Exception:
        return []

    total = EnvironmentalProject.objects.count()
    verified = EnvironmentalProject.objects.filter(
        verification_status='verified').count() if total else 0

    return [
        Counter('projects_total', 'Projects on record', total or None,
                'COUNT(EnvironmentalProject)'),
        Counter('projects_verified', 'Independently verified projects',
                verified or None,
                "EnvironmentalProject WHERE verification_status='verified'",
                is_proof=True),
    ]


def _module_counters() -> list:
    from platform_registry.agents import counts

    data = counts()
    return [
        Counter('production_modules', 'Production modules',
                data['production_modules'],
                'platform_registry.agents, status=PRODUCTION'),
        Counter('beta_modules', 'Beta modules', data['beta_modules'],
                'platform_registry.agents, status=BETA'),
        Counter('experimental_modules', 'Experimental modules',
                data['experimental_modules'],
                'platform_registry.agents, status=EXPERIMENTAL'),
        Counter('specification_packs', 'Agent specification packs',
                data['specification_packs'],
                'Directories under ai_agents/ — DOCUMENTS, not running code'),
        Counter('evaluated_modules', 'Modules with a measured evaluation',
                data['evaluated_modules'],
                'Registry entries whose evaluation is not NOT YET MEASURED'),
    ]


def platform_stats() -> dict:
    """
    Every counter, keyed. The one function public surfaces call.

    Deliberately not cached here: caching is a decision for the caller, and a
    stale count presented as live is the failure mode this module exists to
    prevent.
    """
    counters = (_company_counters()
                + [_country_counter()]
                + _evidence_counters()
                + _project_counters()
                + _module_counters())
    return {c.key: c for c in counters}


def proof_counters() -> list:
    """
    Only the counters that are safe to present as product proof.

    A row count is not proof. `companies_total` says how many organisations are
    in a table; `companies_published` says how many EcoIQ can actually stand
    behind. Marketing surfaces get the second kind only.
    """
    return [c for c in platform_stats().values() if c.is_proof]
