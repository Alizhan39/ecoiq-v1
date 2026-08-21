"""
Test fixtures for company profiles.

D4C removed the neutral defaults, and that broke a lot of tests — correctly.

Every fixture that wrote `CompanyProfile.objects.create(...)` without naming a
single score was silently relying on `default=50.0` to populate sixteen
material inputs. The tests read as though they set up a company; they actually
set up nothing and let the model invent one. When the defaults went, so did the
data, and 289 tests failed.

That is the same defect the programme has been removing from production code,
living in the test suite: a fixture that does not say what it contains, backed
by a number nobody chose.

So fixtures now state their data. `populated()` gives a profile whose material
inputs are explicitly set, and a test that wants unknowns says so by not
calling it — or by nulling exactly the field it means.

Not a `TestCase` mixin on purpose: the helpers are used by module-level
functions in a dozen suites, and a mixin would force them all to restructure.
"""
from __future__ import annotations

#: The 16 registered material inputs, plus pollution_level, which the
#: environmental pillar reads directly.
MATERIAL_FIELDS: tuple[str, ...] = (
    'waste_management_score', 'water_impact_score', 'biodiversity_impact_score',
    'jobs_created_score', 'regional_development_score',
    'infrastructure_contribution_score', 'national_value_score',
    'energy_transition_score', 'digitalization_score',
    'infrastructure_upgrade_score', 'future_readiness_score',
    'transparency_score_detail', 'audit_quality_score',
    'procurement_transparency_score', 'anti_corruption_score',
    'controversy_risk_score',
)

#: Fields that are derived, not supplied. Populating them directly would make a
#: fixture disagree with what the calculator would produce from its own inputs.
DERIVED_FIELDS: tuple[str, ...] = (
    'public_benefit_score', 'environmental_responsibility_score',
    'modernization_score', 'transparency_anti_corruption_score',
    'ethical_alignment_score', 'harm_penalty', 'ecoiq_total_score',
)

#: The value fixtures use unless told otherwise.
#:
#: 60.0 rather than 50.0, deliberately. A fixture full of 50s is
#: indistinguishable at a glance from the old fabricated default, and a reader
#: skimming a failure would not be able to tell whether the number was chosen
#: or inherited.
FIXTURE_VALUE = 60.0


def populate_material(profile, value: float = FIXTURE_VALUE, save: bool = True):
    """
    Give every material input an explicit value.

    Enough for all six dimensions to resolve, so the composite computes and the
    provenance graph has something real to describe.
    """
    for name in MATERIAL_FIELDS:
        setattr(profile, name, value)
    if profile.pollution_level in (None, ''):
        profile.pollution_level = 'low'
    if save and profile.pk:
        profile.save()
    return profile


def populated(company, *, value: float = FIXTURE_VALUE, status: str = 'public',
              pollution_level: str = 'low', **overrides):
    """
    Create a CompanyProfile whose material inputs are explicitly populated.

    `overrides` wins over the fixture value, so a test can name the one field
    it cares about:

        populated(company, water_impact_score=0.0)
    """
    from companies.models import CompanyProfile

    fields = {name: value for name in MATERIAL_FIELDS}
    fields.update(status=status, pollution_level=pollution_level)
    fields.update(overrides)
    return CompanyProfile.objects.create(company=company, **fields)


def unpopulated(company, *, status: str = 'public',
                pollution_level: str = 'low', **overrides):
    """
    Create a CompanyProfile with NO material inputs — genuinely unknown.

    The post-D4C default state, named explicitly so a test that wants it is
    obviously choosing it rather than forgetting to set anything.
    """
    from companies.models import CompanyProfile

    return CompanyProfile.objects.create(
        company=company, status=status, pollution_level=pollution_level,
        **overrides)
