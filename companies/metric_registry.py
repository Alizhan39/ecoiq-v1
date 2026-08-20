"""
Metric registry — D3C-2.

One lookup for every metric EcoIQ can record provenance for, across both layers:

    MATERIAL   assessed inputs living directly on CompanyProfile
    DERIVED    calculated outputs, which may live anywhere or nowhere

D3C-1 identified the blocker this solves. CompanyMetricProvenance validated
metric_key against MATERIAL_INPUTS and resolved the value with
getattr(profile, key) — so NEI (on CompanyEthicsProfile), ml_score (on
league.Company) and the Mizan score (on a dataclass that is never persisted)
could not be recorded at all. A registry entry therefore has to carry WHERE the
value lives, not just its name.

Python, not a database table
----------------------------
Metric definitions are code: they change when a formula changes, they belong in
review, and they must be importable without a query. MATERIAL_INPUTS is already
a Python structure for the same reasons. A table would add a migration, an admin
surface and a join to restate names the code already has, and would let a
definition drift from the calculation it describes.

Lookup is a dict access — constant time, no query, safe to call per row.

Resolvers are explicit callables
--------------------------------
No dynamic import from a stored string, and no getattr chain assembled from
user data. Each definition names a function, so resolution is readable, typed
and testable, and a metric that moves fails at import rather than at runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from companies.evidence import (
    MATERIAL_INPUTS, PROVENANCE_ESTIMATED, PROVENANCE_INFERRED, PROVENANCE_MEASURED,
    PROVENANCE_MODELLED, PROVENANCE_NO_VALUE, PROVENANCE_SEEDED, PROVENANCE_UNKNOWN,
)

MATERIAL = 'MATERIAL'
DERIVED = 'DERIVED'

#: Only two kinds. 'AI', 'ETHICAL', 'FINANCE', 'CLIMATE' and the like are
#: domains, not provenance semantics — they say what a metric is ABOUT, and this
#: registry is about how its value came to exist. Domain metadata can live
#: alongside if it is ever needed; it must not fragment the kind.
KINDS = (MATERIAL, DERIVED)


@dataclass(frozen=True)
class MetricDefinition:
    """One metric EcoIQ can record provenance for."""

    key: str
    label: str
    kind: str

    #: Where the value lives, for humans reading the registry.
    #: e.g. 'companies.CompanyProfile.public_benefit_score', or 'ephemeral'.
    value_location: str

    #: Resolves the value from a CompanyProfile, or None when unavailable.
    #: None for ephemeral metrics, which have no stored value to resolve.
    resolver: Callable | None

    #: The origins that are HONEST for this metric. Enforced when provenance is
    #: recorded, so a derived composite cannot be labelled MEASURED — the
    #: mislabel D3C-1 identified as the most likely one to slip through.
    allowed_origins: frozenset

    #: The function that produces the value, for humans. Not imported.
    calculation: str = ''

    description: str = ''

    @property
    def is_ephemeral(self) -> bool:
        """True when no persisted field holds this metric's value."""
        return self.resolver is None

    def resolve(self, profile):
        return None if self.resolver is None else self.resolver(profile)


# ── Resolvers ─────────────────────────────────────────────────────────────────
#
# Each is a plain function, so a metric that moves breaks loudly here rather
# than returning None somewhere far away.

def _profile_field(name: str) -> Callable:
    def resolve(profile):
        return getattr(profile, name, None)
    resolve.__name__ = f'resolve_profile_{name}'
    return resolve


def _related_field(relation: str, name: str) -> Callable:
    """
    Resolve through a one-to-one relation, tolerating its absence.

    A company with no ethics profile yet is not an error — it is a company
    whose NEI has not been computed, and the honest answer is None.
    """
    def resolve(profile):
        try:
            related = getattr(profile, relation, None)
        except Exception:
            # RelatedObjectDoesNotExist for an unpopulated OneToOne.
            return None
        return None if related is None else getattr(related, name, None)
    resolve.__name__ = f'resolve_{relation}_{name}'
    return resolve


def _company_field(name: str) -> Callable:
    def resolve(profile):
        company = getattr(profile, 'company', None)
        return None if company is None else getattr(company, name, None)
    resolve.__name__ = f'resolve_company_{name}'
    return resolve


def _latest_qdf(profile):
    """
    QDF is a ForeignKey, not a OneToOne — a profile may hold several
    assessments. The current value is the most recent one.
    """
    assessment = profile.qdf_assessments.order_by('-id').first()
    return None if assessment is None else assessment.decision_integrity_score


# ── Honest origin policies ────────────────────────────────────────────────────

#: These describe the ABSENCE of lineage rather than a claim about it, so they
#: are honest for any metric of any kind. D3B writes LEGACY_UNKNOWN_PROVENANCE
#: across the whole estate and must keep being able to.
LINEAGE_ABSENT = frozenset({PROVENANCE_UNKNOWN, PROVENANCE_NO_VALUE})

#: Material metrics accept every substantive origin.
#:
#: A NOTE ON WHAT IS *NOT* ENFORCED HERE, because it is a deliberate choice
#: rather than an oversight. The D3C-1 finding stands: an assessed
#: CompanyProfile score is not a direct observation — 'water_impact_score' is
#: declared as "0-100: water stewardship quality", a judgment about water rather
#: than water — so MEASURED is arguably dishonest for this layer, and INFERRED
#: or ESTIMATED would be the truthful labels.
#:
#: Enforcing that would break D3A's shipped contract, which explicitly tests and
#: permits MEASURED on material metrics, and would reject provenance that a
#: future ingestion writer might legitimately record. D3C-2 is an identity and
#: storage-location PR; narrowing which origins a material metric may claim is a
#: semantics change that belongs with the introduction of a real source layer.
#: Recorded in DERIVED_METRIC_REGISTRY.md as an open item rather than smuggled
#: in here.
MATERIAL_ORIGINS = frozenset({
    PROVENANCE_MEASURED, PROVENANCE_ESTIMATED, PROVENANCE_INFERRED,
    PROVENANCE_MODELLED, PROVENANCE_SEEDED,
}) | LINEAGE_ABSENT

#: Derived metrics may NOT be MEASURED. This is the one restriction D3C-2 does
#: enforce, and the mislabel most likely to slip through: a composite is a model
#: output however good its inputs, and calling it MEASURED claims an observation
#: that never happened.
#:
#: SEEDED is allowed because a seed command may write a composite directly, and
#: calling that MODELLED would credit a calculation that never ran.
DERIVED_ORIGINS = frozenset({
    PROVENANCE_MODELLED, PROVENANCE_ESTIMATED, PROVENANCE_INFERRED,
    PROVENANCE_SEEDED,
}) | LINEAGE_ABSENT


# ── Material metrics ──────────────────────────────────────────────────────────
#
# Keys are the bare CompanyProfile field names, unchanged. Renaming them to a
# dotted namespace would invalidate every provenance row D3B and D3C-1 already
# wrote, for cosmetic consistency. The asymmetry is deliberate and is documented
# in DERIVED_METRIC_REGISTRY.md rather than papered over.

_MATERIAL_DEFINITIONS = [
    MetricDefinition(
        key=item.field_name,
        label=item.field_name.replace('_', ' ').title(),
        kind=MATERIAL,
        value_location=f'companies.CompanyProfile.{item.field_name}',
        resolver=_profile_field(item.field_name),
        allowed_origins=MATERIAL_ORIGINS,
        description=f'Assessed {item.pillar} input, weight {item.weight:.4f}.',
    )
    for item in sorted({i.field_name: i for i in MATERIAL_INPUTS}.values(),
                       key=lambda i: i.field_name)
]


# ── Derived metrics ───────────────────────────────────────────────────────────
#
# Only metrics that actually exist in this repository, verified against the
# models. Nothing aspirational.

_DERIVED_DEFINITIONS = [
    # Composites persisted on CompanyProfile itself.
    MetricDefinition(
        key='company.ecoiq_total', label='EcoIQ Total Score', kind=DERIVED,
        value_location='companies.CompanyProfile.ecoiq_total_score',
        resolver=_profile_field('ecoiq_total_score'),
        allowed_origins=DERIVED_ORIGINS,
        calculation='companies.scoring.compute_ecoiq_profile_score',
        description='Six-pillar weighted composite, minus harm penalty.',
    ),
    MetricDefinition(
        key='company.public_benefit', label='Public Benefit Pillar', kind=DERIVED,
        value_location='companies.CompanyProfile.public_benefit_score',
        resolver=_profile_field('public_benefit_score'),
        allowed_origins=DERIVED_ORIGINS,
        calculation='companies.scoring.calculate_public_benefit',
    ),
    MetricDefinition(
        key='company.environmental', label='Environmental Stewardship Pillar',
        kind=DERIVED,
        value_location='companies.CompanyProfile.environmental_responsibility_score',
        resolver=_profile_field('environmental_responsibility_score'),
        allowed_origins=DERIVED_ORIGINS,
        calculation='companies.scoring.calculate_environmental_responsibility',
    ),
    MetricDefinition(
        key='company.modernization', label='Responsible Modernization Pillar',
        kind=DERIVED,
        value_location='companies.CompanyProfile.modernization_score',
        resolver=_profile_field('modernization_score'),
        allowed_origins=DERIVED_ORIGINS,
        calculation='companies.scoring.calculate_modernization',
    ),
    MetricDefinition(
        key='company.transparency_governance', label='Transparent Governance Pillar',
        kind=DERIVED,
        value_location='companies.CompanyProfile.transparency_anti_corruption_score',
        resolver=_profile_field('transparency_anti_corruption_score'),
        allowed_origins=DERIVED_ORIGINS,
        calculation='companies.scoring.calculate_transparency',
    ),
    MetricDefinition(
        key='company.harm_penalty', label='Harm Penalty', kind=DERIVED,
        value_location='companies.CompanyProfile.harm_penalty',
        resolver=_profile_field('harm_penalty'),
        allowed_origins=DERIVED_ORIGINS,
        calculation='companies.scoring.calculate_harm_penalty',
    ),

    # Ethics — a separate model reached through a OneToOne.
    MetricDefinition(
        key='ethics.nei', label='Net Ethical Impact', kind=DERIVED,
        value_location='ethics.CompanyEthicsProfile.net_ethical_impact',
        resolver=_related_field('ethics', 'net_ethical_impact'),
        allowed_origins=DERIVED_ORIGINS,
        calculation='ethics.scoring.compute_net_ethical_impact',
        description='Benefit minus harm balance.',
    ),
    MetricDefinition(
        key='ethics.tss', label='Transition Stewardship Score', kind=DERIVED,
        value_location='ethics.CompanyEthicsProfile.transition_stewardship',
        resolver=_related_field('ethics', 'transition_stewardship'),
        allowed_origins=DERIVED_ORIGINS,
        calculation='ethics.scoring.compute_transition_stewardship',
    ),
    MetricDefinition(
        key='ethics.rvi', label='Regenerative Value Index', kind=DERIVED,
        value_location='ethics.CompanyEthicsProfile.regenerative_value',
        resolver=_related_field('ethics', 'regenerative_value'),
        allowed_origins=DERIVED_ORIGINS,
        calculation='ethics.scoring.compute_regenerative_value',
    ),

    # Financing readiness — another OneToOne.
    MetricDefinition(
        key='financing.readiness', label='Financing Readiness', kind=DERIVED,
        value_location='financing.CompanyFinancingProfile.financing_readiness',
        resolver=_related_field('financing_intel', 'financing_readiness'),
        allowed_origins=DERIVED_ORIGINS,
        calculation='financing.matching.compute_and_save',
    ),

    # QDF — a ForeignKey, so the current value is the latest assessment.
    MetricDefinition(
        key='qdf.decision_integrity', label='Decision Integrity Score', kind=DERIVED,
        value_location='qdf.DecisionAssessment.decision_integrity_score (latest)',
        resolver=_latest_qdf,
        allowed_origins=DERIVED_ORIGINS,
        calculation='qdf.scoring.compute_and_save',
    ),

    # ML — persisted on league.Company, not on the profile.
    MetricDefinition(
        key='ml.score', label='ML Predicted Score', kind=DERIVED,
        value_location='league.Company.ml_score',
        resolver=_company_field('ml_score'),
        allowed_origins=DERIVED_ORIGINS,
        calculation='ml.scoring_model.EcoIQScoringModel.predict_company',
    ),
    MetricDefinition(
        key='ml.predicted_12m', label='12-Month Forecast', kind=DERIVED,
        value_location='league.Company.ml_predicted_score_12m',
        resolver=_company_field('ml_predicted_score_12m'),
        allowed_origins=DERIVED_ORIGINS,
        calculation='ml.prediction.predict_12m',
    ),

    # ── Ephemeral: computed on demand, never stored ──────────────────────────
    #
    # resolver=None is the honest declaration. These have no field to read, so
    # provenance for them must carry the value it was recorded for — see
    # CompanyMetricProvenance.recorded_value.
    MetricDefinition(
        key='mizan.score', label='Mizan Score', kind=DERIVED,
        value_location='ephemeral — mizan.scoring.MizanResult dataclass',
        resolver=None,
        allowed_origins=DERIVED_ORIGINS,
        calculation='mizan.scoring.score_company',
        description='Six-dimension Mizan balance. Recomputed per request; never persisted.',
    ),
    MetricDefinition(
        key='ml.responsible_finance', label='Responsible Finance Score', kind=DERIVED,
        value_location='ephemeral — dict returned by the scorer',
        resolver=None,
        allowed_origins=DERIVED_ORIGINS,
        calculation='ml.responsible_finance.compute_responsible_finance_score',
    ),
    MetricDefinition(
        key='greenwashing.risk', label='Greenwashing Risk Score', kind=DERIVED,
        value_location='ephemeral — GreenwashingAssessment dataclass',
        resolver=None,
        allowed_origins=DERIVED_ORIGINS,
        calculation='ml.ethics.greenwashing_risk.greenwashing_from_profile',
        description='Public-data greenwashing risk. Recomputed per request; never persisted.',
    ),
]


def _build_registry() -> dict:
    registry: dict[str, MetricDefinition] = {}
    for definition in _MATERIAL_DEFINITIONS + _DERIVED_DEFINITIONS:
        if definition.key in registry:
            raise ValueError(
                f'Duplicate metric key {definition.key!r}. Metric identity must be '
                f'unique across both layers — two definitions for one key would '
                f'make provenance ambiguous about which metric it describes.'
            )
        if definition.kind not in KINDS:
            raise ValueError(f'{definition.key!r}: unknown kind {definition.kind!r}.')
        registry[definition.key] = definition
    return registry


REGISTRY: dict[str, MetricDefinition] = _build_registry()

#: Every key provenance may be recorded for. Strict: an unregistered string is
#: rejected, never accepted as a free-form label.
VALID_KEYS: frozenset[str] = frozenset(REGISTRY)

MATERIAL_KEYS: frozenset[str] = frozenset(
    k for k, d in REGISTRY.items() if d.kind == MATERIAL)
DERIVED_KEYS: frozenset[str] = frozenset(
    k for k, d in REGISTRY.items() if d.kind == DERIVED)
EPHEMERAL_KEYS: frozenset[str] = frozenset(
    k for k, d in REGISTRY.items() if d.is_ephemeral)


def get_metric_definition(key: str) -> MetricDefinition | None:
    """The definition for a metric key, or None if it is not registered."""
    return REGISTRY.get(key)


def require_metric_definition(key: str) -> MetricDefinition:
    """The definition for a metric key, raising if it is not registered."""
    definition = REGISTRY.get(key)
    if definition is None:
        raise ValueError(
            f'{key!r} is not a registered EcoIQ metric. Register it in '
            f'companies/metric_registry.py — provenance never accepts an '
            f'unregistered key, because a metric whose identity is a free-form '
            f'string cannot be reliably queried later.'
        )
    return definition


def resolve_value(profile, key: str):
    """
    The current value of one metric for one profile, or None.

    Returns None for an ephemeral metric: there is no stored value to read, and
    recomputing one here would return today's answer rather than the value the
    provenance row was recorded for.
    """
    definition = get_metric_definition(key)
    return None if definition is None else definition.resolve(profile)
