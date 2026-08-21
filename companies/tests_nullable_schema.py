"""
D4B — the schema can now represent "unknown".

Until this migration, it could not. Every score field was NOT NULL, so the only
way to store "we do not know" was to store a number that meant something else —
which is the whole defect the programme has been unwinding.

WHAT THIS DOES NOT DO
---------------------
It does not remove the defaults. A new profile still receives 50.0, because
D4C owns that change. So these tests set None explicitly: they prove the
column ACCEPTS unknown, not that anything produces it yet.
"""
from datetime import date

from django.db import connection
from django.test import SimpleTestCase, TestCase

from companies.models import CompanyProfile, CompanyScoreSnapshot
from league.models import Company

MATERIAL = [
    'waste_management_score', 'water_impact_score', 'biodiversity_impact_score',
    'jobs_created_score', 'regional_development_score',
    'infrastructure_contribution_score', 'national_value_score',
    'energy_transition_score', 'digitalization_score',
    'infrastructure_upgrade_score', 'future_readiness_score',
    'transparency_score_detail', 'audit_quality_score',
    'procurement_transparency_score', 'anti_corruption_score',
]
PILLARS = [
    'public_benefit_score', 'environmental_responsibility_score',
    'modernization_score', 'transparency_anti_corruption_score',
    'ethical_alignment_score',
]
OTHER = ['controversy_risk_score', 'profit_extraction_score',
         'profit_extraction_risk_score', 'harm_penalty', 'ecoiq_total_score']

SNAPSHOT = ['total_score', 'public_benefit_score', 'environmental_score',
            'modernization_score', 'governance_score', 'anti_corruption_score',
            'ethical_alignment_score', 'harm_penalty']


def _profile(slug='nullable'):
    company = Company.objects.create(name=slug, slug=slug, country='UK')
    return CompanyProfile.objects.create(company=company, status='public',
                                         pollution_level='low')


class FieldsAreNullable(SimpleTestCase):

    def test_every_material_metric_accepts_null(self):
        for name in MATERIAL:
            with self.subTest(field=name):
                self.assertTrue(CompanyProfile._meta.get_field(name).null)

    def test_every_pillar_accepts_null(self):
        for name in PILLARS:
            with self.subTest(field=name):
                self.assertTrue(CompanyProfile._meta.get_field(name).null)

    def test_the_composite_accepts_null(self):
        self.assertTrue(CompanyProfile._meta.get_field('ecoiq_total_score').null)

    def test_the_risk_scores_accept_null(self):
        """
        Their default was 30.0 — 'low risk'. A FAVOURABLE finding manufactured
        from an absence, pointing the opposite way from the 50 this programme
        was named after.
        """
        for name in ('controversy_risk_score', 'profit_extraction_risk_score'):
            with self.subTest(field=name):
                self.assertTrue(CompanyProfile._meta.get_field(name).null)

    def test_harm_penalty_accepts_null(self):
        """
        Its default was 0.0 — 'no harm found'. Zero is a real finding here,
        which is exactly why it cannot also mean 'we did not look'.
        """
        self.assertTrue(CompanyProfile._meta.get_field('harm_penalty').null)

    def test_every_snapshot_field_accepts_null(self):
        for name in SNAPSHOT:
            with self.subTest(field=name):
                self.assertTrue(CompanyScoreSnapshot._meta.get_field(name).null)

    def test_snapshot_total_score_is_no_longer_required(self):
        """
        It had no default and NOT NULL, so a snapshot simply could not be
        written for a company with no composite. History can now record
        'unknown at this date'.
        """
        field = CompanyScoreSnapshot._meta.get_field('total_score')

        self.assertTrue(field.null)
        self.assertTrue(field.blank)

    def test_the_count_matches_the_classification(self):
        profile_fields = MATERIAL + PILLARS + OTHER

        self.assertEqual(len(profile_fields), 25)
        self.assertEqual(len(SNAPSHOT), 8)
        self.assertEqual(len(profile_fields) + len(SNAPSHOT), 33)

    def test_defaults_are_deliberately_still_present(self):
        """
        D4B relaxes a constraint; D4C removes the defaults. Splitting them
        means this migration changes no behaviour at all.
        """
        from django.db.models.fields import NOT_PROVIDED

        for name in MATERIAL + PILLARS:
            with self.subTest(field=name):
                default = CompanyProfile._meta.get_field(name).default
                self.assertIsNot(default, NOT_PROVIDED)


class UnknownCanBeStored(TestCase):

    def test_a_material_metric_round_trips_as_null(self):
        profile = _profile()
        profile.water_impact_score = None
        profile.save()
        profile.refresh_from_db()

        self.assertIsNone(profile.water_impact_score)

    def test_every_profile_field_round_trips_as_null(self):
        profile = _profile('all-null')
        for name in MATERIAL + PILLARS + OTHER:
            setattr(profile, name, None)
        profile.save()
        profile.refresh_from_db()

        for name in MATERIAL + PILLARS + OTHER:
            with self.subTest(field=name):
                self.assertIsNone(getattr(profile, name))

    def test_a_snapshot_round_trips_as_null(self):
        profile = _profile('snap-null')
        snapshot = CompanyScoreSnapshot.objects.create(
            profile=profile, date=date(2026, 1, 1),
            **{name: None for name in SNAPSHOT})
        snapshot.refresh_from_db()

        for name in SNAPSHOT:
            with self.subTest(field=name):
                self.assertIsNone(getattr(snapshot, name))

    def test_null_is_distinguishable_from_zero(self):
        """The distinction the schema could not express before."""
        unknown = _profile('unknown-harm')
        unknown.harm_penalty = None
        unknown.save()

        measured = _profile('zero-harm')
        measured.harm_penalty = 0.0
        measured.save()

        unknown.refresh_from_db()
        measured.refresh_from_db()
        self.assertIsNone(unknown.harm_penalty)
        self.assertEqual(measured.harm_penalty, 0.0)
        self.assertNotEqual(unknown.harm_penalty, measured.harm_penalty)

    def test_null_is_distinguishable_from_fifty(self):
        unknown = _profile('unknown-water')
        unknown.water_impact_score = None
        unknown.save()

        measured = _profile('fifty-water')
        measured.water_impact_score = 50.0
        measured.save()

        unknown.refresh_from_db()
        measured.refresh_from_db()
        self.assertIsNone(unknown.water_impact_score)
        self.assertEqual(measured.water_impact_score, 50.0)


class ExistingBehaviourIsUnchanged(TestCase):
    """
    D4B must be inert. Defaults are retained, so nothing that worked before
    behaves differently after.
    """

    def test_a_new_profile_still_gets_the_legacy_defaults(self):
        profile = _profile('legacy-defaults')

        self.assertEqual(profile.water_impact_score, 50.0)
        self.assertEqual(profile.controversy_risk_score, 30.0)
        self.assertEqual(profile.harm_penalty, 0.0)

    def test_scoring_still_works_end_to_end(self):
        from companies.scoring import recalculate_and_save

        profile = _profile('still-scores')
        recalculate_and_save(profile)
        profile.refresh_from_db()

        self.assertIsNotNone(profile.ecoiq_total_score)

    def test_scoring_survives_a_fully_unknown_profile(self):
        """The state the schema can now hold, run through the real calculator."""
        from companies.scoring import recalculate_and_save

        profile = _profile('all-unknown')
        for name in MATERIAL:
            setattr(profile, name, None)
        profile.save()

        recalculate_and_save(profile)   # must not raise

        profile.refresh_from_db()
        self.assertIsNotNone(profile)

    def test_the_calculator_correctly_computes_no_composite(self):
        """
        The arithmetic is already right: with no inputs there is no composite.
        """
        from companies.scoring import compute_ecoiq_profile_score

        profile = _profile('no-composite')
        for name in MATERIAL:
            setattr(profile, name, None)

        self.assertIsNone(compute_ecoiq_profile_score(profile)['ecoiq_total_score'])

    def test_the_none_result_is_still_not_persisted_yet(self):
        """
        THE D4C BRIDGE, pinned so the handover is explicit.

        recalculate_and_save filters None out of the fields it writes
        (companies/scoring.py, `written = [... if value is not None]`). That was
        correct while the columns were NOT NULL — writing None would have
        raised — so the field kept its previous value, or its default.

        D4B makes the column able to hold unknown. It deliberately does NOT
        start writing unknown: that is a behaviour change, it would put NULLs
        into production on the next recalculation, and it belongs in D4C beside
        the removal of the defaults.

        So the calculator says None and the column still holds 0.0. This test
        asserts that gap on purpose, and D4C closes it.
        """
        from companies.scoring import compute_ecoiq_profile_score, recalculate_and_save

        profile = _profile('bridge')
        for name in MATERIAL:
            setattr(profile, name, None)
        profile.save()

        self.assertIsNone(compute_ecoiq_profile_score(profile)['ecoiq_total_score'])

        recalculate_and_save(profile)
        profile.refresh_from_db()
        self.assertEqual(profile.ecoiq_total_score, 0.0,
                         'still the default — D4C is what makes this NULL')

    def test_an_unknown_profile_is_not_publicly_available(self):
        from companies.evidence import public_score_state

        profile = _profile('unknown-public')
        for name in MATERIAL:
            setattr(profile, name, None)
        profile.save()

        self.assertFalse(public_score_state(profile).available)


class DatabaseConstraints(TestCase):
    """Read the actual schema, not just the Django field definitions."""

    def _columns(self, table):
        with connection.cursor() as cursor:
            return {row.name: row for row in connection.introspection
                    .get_table_description(cursor, table)}

    def test_the_profile_columns_are_nullable_in_the_database(self):
        columns = self._columns('companies_companyprofile')

        for name in MATERIAL + PILLARS + OTHER:
            with self.subTest(column=name):
                self.assertTrue(columns[name].null_ok)

    def test_the_snapshot_columns_are_nullable_in_the_database(self):
        columns = self._columns('companies_companyscoresnapshot')

        for name in SNAPSHOT:
            with self.subTest(column=name):
                self.assertTrue(columns[name].null_ok)


class MigrationShape(SimpleTestCase):
    """
    The migration was inspected by hand before being trusted. These assertions
    pin what that inspection found.
    """

    def _migration(self):
        from importlib import import_module

        return import_module('companies.migrations.0011_nullable_score_fields')

    def test_it_only_alters_fields(self):
        operations = self._migration().Migration.operations

        self.assertTrue(operations)
        for operation in operations:
            with self.subTest(op=operation):
                self.assertEqual(type(operation).__name__, 'AlterField')

    def test_it_touches_no_data(self):
        """No RunPython, no RunSQL — a constraint change and nothing else."""
        operations = self._migration().Migration.operations
        names = {type(o).__name__ for o in operations}

        self.assertNotIn('RunPython', names)
        self.assertNotIn('RunSQL', names)

    def test_it_covers_exactly_thirty_three_fields(self):
        self.assertEqual(len(self._migration().Migration.operations), 33)

    def test_it_preserves_the_defaults(self):
        """Removing them is D4C. This migration must change no behaviour."""
        from django.db.models.fields import NOT_PROVIDED

        with_defaults = [
            o for o in self._migration().Migration.operations
            if o.field.default is not NOT_PROVIDED
        ]
        self.assertEqual(len(with_defaults), 32)
