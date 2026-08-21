"""
D4C — unknown is now NULL, and stays NULL.

The target invariant, stated as the brief stated it:

    new CompanyProfile()

does NOT magically receive dozens of 50 scores.

D4B made the columns able to hold unknown. This is where they start to.
"""
from django.db.models.fields import NOT_PROVIDED
from django.test import SimpleTestCase, TestCase

from companies.models import CompanyProfile, CompanyScoreSnapshot
from companies.scoring import recalculate_and_save
from league.models import Company

PROFILE_FIELDS = [
    'waste_management_score', 'water_impact_score', 'biodiversity_impact_score',
    'jobs_created_score', 'regional_development_score',
    'infrastructure_contribution_score', 'national_value_score',
    'energy_transition_score', 'digitalization_score',
    'infrastructure_upgrade_score', 'future_readiness_score',
    'transparency_score_detail', 'audit_quality_score',
    'procurement_transparency_score', 'anti_corruption_score',
    'controversy_risk_score', 'profit_extraction_score',
    'profit_extraction_risk_score', 'public_benefit_score',
    'environmental_responsibility_score', 'modernization_score',
    'transparency_anti_corruption_score', 'ethical_alignment_score',
    'harm_penalty', 'ecoiq_total_score',
]
SNAPSHOT_FIELDS = ['public_benefit_score', 'environmental_score',
                   'modernization_score', 'governance_score',
                   'anti_corruption_score', 'ethical_alignment_score',
                   'harm_penalty']


def _fully_evidence(profile, value=60.0):
    """Give every material input a real value, so all six dimensions resolve."""
    for name in PROFILE_FIELDS:
        if name in ('harm_penalty', 'ecoiq_total_score', 'profit_extraction_score',
                    'profit_extraction_risk_score'):
            continue
        setattr(profile, name, value)
    profile.save()
    return profile


def _company(slug='d4c'):
    return Company.objects.create(name=slug, slug=slug, country='UK')


class TheInvariant(TestCase):

    def test_a_new_profile_receives_no_fabricated_scores(self):
        profile = CompanyProfile.objects.create(
            company=_company(), status='public', pollution_level='low')
        profile.refresh_from_db()

        for name in PROFILE_FIELDS:
            with self.subTest(field=name):
                self.assertIsNone(getattr(profile, name))

    def test_no_field_arrives_as_fifty(self):
        profile = CompanyProfile.objects.create(
            company=_company('no-fifty'), status='public', pollution_level='low')
        profile.refresh_from_db()

        values = [getattr(profile, n) for n in PROFILE_FIELDS]
        self.assertNotIn(50.0, values)

    def test_no_risk_field_arrives_as_low_risk(self):
        """Their default was 30.0 — a favourable finding from an absence."""
        profile = CompanyProfile.objects.create(
            company=_company('no-thirty'), status='public', pollution_level='low')
        profile.refresh_from_db()

        self.assertIsNone(profile.controversy_risk_score)
        self.assertIsNone(profile.profit_extraction_risk_score)

    def test_harm_penalty_does_not_arrive_as_no_harm(self):
        profile = CompanyProfile.objects.create(
            company=_company('no-harm-claim'), status='public',
            pollution_level='low')
        profile.refresh_from_db()

        self.assertIsNone(profile.harm_penalty,
                          '0.0 would assert that no harm was found')

    def test_a_new_snapshot_receives_no_fabricated_scores(self):
        from datetime import date

        profile = CompanyProfile.objects.create(
            company=_company('snap-d4c'), status='public', pollution_level='low')
        snapshot = CompanyScoreSnapshot.objects.create(
            profile=profile, date=date(2026, 1, 1))
        snapshot.refresh_from_db()

        for name in SNAPSHOT_FIELDS:
            with self.subTest(field=name):
                self.assertIsNone(getattr(snapshot, name))


class DefaultsAreGone(SimpleTestCase):

    def test_no_profile_score_field_declares_a_default(self):
        for name in PROFILE_FIELDS:
            with self.subTest(field=name):
                self.assertIs(CompanyProfile._meta.get_field(name).default,
                              NOT_PROVIDED)

    def test_no_snapshot_score_field_declares_a_default(self):
        for name in SNAPSHOT_FIELDS + ['total_score']:
            with self.subTest(field=name):
                self.assertIs(CompanyScoreSnapshot._meta.get_field(name).default,
                              NOT_PROVIDED)

    def test_they_all_remain_nullable(self):
        """D4B's constraint change must survive D4C."""
        for name in PROFILE_FIELDS:
            with self.subTest(field=name):
                self.assertTrue(CompanyProfile._meta.get_field(name).null)


class UnknownIsPersisted(TestCase):
    """
    The D4B → D4C bridge, closed.

    recalculate_and_save used to filter None out of the fields it wrote, so a
    recalculation that found no evidence left the previous number in place. The
    stored value stopped being a statement about the evidence.
    """

    def _profile(self, slug):
        return CompanyProfile.objects.create(
            company=_company(slug), status='public', pollution_level='low')

    def test_a_fully_unknown_profile_gets_a_null_composite(self):
        profile = self._profile('unknown-composite')

        recalculate_and_save(profile)
        profile.refresh_from_db()

        self.assertIsNone(profile.ecoiq_total_score)

    def test_pillars_are_nulled_too(self):
        """
        environmental_responsibility_score is excluded deliberately: it is
        derivable from pollution_level alone, which this profile HAS. It is
        therefore genuinely known, and nulling it would be the mirror-image
        error — discarding evidence that exists.
        """
        profile = self._profile('unknown-pillars')

        recalculate_and_save(profile)
        profile.refresh_from_db()

        for name in ('public_benefit_score', 'modernization_score',
                     'transparency_anti_corruption_score'):
            with self.subTest(field=name):
                self.assertIsNone(getattr(profile, name))

    def test_a_pillar_backed_by_real_evidence_is_kept(self):
        profile = self._profile('env-known')

        recalculate_and_save(profile)
        profile.refresh_from_db()

        self.assertIsNotNone(profile.environmental_responsibility_score,
                             'pollution_level is evidence, and it is present')

    def test_a_withdrawn_input_nulls_a_previously_stored_score(self):
        """
        The case that made the old skip actively wrong: a company whose
        evidence is withdrawn kept its old composite indefinitely.
        """
        profile = self._profile('withdrawn')
        _fully_evidence(profile)
        recalculate_and_save(profile)
        profile.refresh_from_db()
        self.assertIsNotNone(profile.ecoiq_total_score)

        # anti_corruption is a ONE-INPUT dimension, so withdrawing it removes
        # the whole dimension. Withdrawing a single sub-input of a multi-input
        # pillar would not: those re-normalise across what remains, which is
        # correct and documented behaviour one layer down.
        profile.anti_corruption_score = None
        profile.save()
        recalculate_and_save(profile)
        profile.refresh_from_db()

        self.assertIsNone(profile.ecoiq_total_score,
                          'the stored value must describe the current evidence')

    def test_withdrawing_one_sub_input_does_not_null_a_pillar(self):
        """The counterpart: a pillar re-normalises across the inputs it keeps."""
        profile = self._profile('renormalise')
        _fully_evidence(profile)
        recalculate_and_save(profile)

        profile.water_impact_score = None
        profile.save()
        recalculate_and_save(profile)
        profile.refresh_from_db()

        self.assertIsNotNone(profile.environmental_responsibility_score)

    def test_no_moral_label_survives_a_null_score(self):
        """A label with no score behind it asserts a category nobody assessed."""
        profile = self._profile('no-label')
        _fully_evidence(profile)
        recalculate_and_save(profile)

        profile.anti_corruption_score = None
        profile.save()
        recalculate_and_save(profile)
        profile.refresh_from_db()

        self.assertIsNone(profile.ecoiq_total_score)
        self.assertEqual(profile.moral_label, '')
        self.assertEqual(profile.ecoiq_category, '')

    def test_a_real_score_is_still_written(self):
        """
        All six dimensions must be known: the composite refuses to
        re-normalise across missing ones, because they measure different
        things and dropping one would silently redefine the score.
        """
        profile = self._profile('still-writes')
        _fully_evidence(profile)

        recalculate_and_save(profile)
        profile.refresh_from_db()

        self.assertIsNotNone(profile.ecoiq_total_score)

    def test_a_partially_evidenced_profile_gets_no_composite(self):
        profile = self._profile('partial')
        profile.waste_management_score = 60.0
        profile.save()

        recalculate_and_save(profile)
        profile.refresh_from_db()

        self.assertIsNone(profile.ecoiq_total_score,
                          'a partial composite would misrepresent itself as whole')

    def test_a_genuine_zero_is_written_not_skipped(self):
        """
        A measured 0.0 must survive the write path. The environmental pillar
        also folds in pollution_level, so the resulting figure is low rather
        than exactly zero — what matters is that the zeros were not discarded
        as though they were unknown.
        """
        profile = self._profile('genuine-zero')
        _fully_evidence(profile, value=0.0)

        recalculate_and_save(profile)
        profile.refresh_from_db()

        self.assertIsNotNone(profile.public_benefit_score)
        self.assertEqual(profile.public_benefit_score, 0.0)
        self.assertIsNotNone(profile.ecoiq_total_score)


class PublicSurfacesHoldUp(TestCase):
    """A profile that is now genuinely all-NULL must not crash anything."""

    def setUp(self):
        self.profile = CompanyProfile.objects.create(
            company=_company('all-null-public'), status='public',
            pollution_level='low')

    def test_the_gate_reports_unavailable(self):
        from companies.evidence import public_score_state

        self.assertFalse(public_score_state(self.profile).available)

    def test_str_does_not_raise(self):
        self.assertIn('not yet scored', str(self.profile))

    def test_the_company_page_renders(self):
        from django.test import Client

        response = Client().get(f'/companies/{self.profile.company.slug}/')

        self.assertEqual(response.status_code, 200)

    def test_the_directory_renders(self):
        from django.test import Client

        self.assertEqual(Client().get('/companies/').status_code, 200)

    def test_the_league_renders(self):
        from django.test import Client

        self.assertEqual(Client().get('/league/').status_code, 200)

    def test_api_v2_reports_insufficient_evidence(self):
        from django.test import Client

        payload = Client().get(
            f'/api/v2/companies/{self.profile.company.slug}/').json()

        self.assertIsNone(payload['ecoiq_score'])
        self.assertEqual(payload['score_status'], 'INSUFFICIENT_EVIDENCE')

    def test_screening_does_not_raise(self):
        from companies.screening import compute_ethical_screening

        result = compute_ethical_screening(self.profile)

        self.assertNotEqual(result['status'], 'passed')


class ConfidenceIsNeverInvented(SimpleTestCase):
    """
    Two neutral-confidence fabrications were found by the D4C residual sweep,
    in modules the earlier phases never touched.
    """

    def _read(self, path):
        from pathlib import Path

        return (Path(__file__).resolve().parent.parent / path).read_text()

    def test_the_transition_engine_does_not_invent_half_confidence(self):
        source = self._read('transition/engine.py')

        self.assertNotIn("data.get('confidence')) or 0.5", source)

    def test_the_transition_engine_does_not_invent_a_quality_tier(self):
        source = self._read('transition/engine.py')

        self.assertNotIn("data.get('data_quality', 'medium')", source)

    def test_the_why_panel_does_not_render_zero_percent_for_unknown(self):
        source = self._read('core/why.py')

        self.assertNotIn('(confidence or 0) * 100', source)

    def test_the_why_panel_says_not_recorded(self):
        self.assertIn('Confidence not recorded', self._read('core/why.py'))


class MigrationShape(SimpleTestCase):

    def _migration(self):
        from importlib import import_module

        return import_module('companies.migrations.0012_remove_neutral_defaults')

    def test_it_only_alters_fields(self):
        for operation in self._migration().Migration.operations:
            with self.subTest(op=operation):
                self.assertEqual(type(operation).__name__, 'AlterField')

    def test_it_touches_no_data(self):
        names = {type(o).__name__ for o in self._migration().Migration.operations}

        self.assertNotIn('RunPython', names)
        self.assertNotIn('RunSQL', names)

    def test_no_operation_reintroduces_a_default(self):
        for operation in self._migration().Migration.operations:
            with self.subTest(field=operation.name):
                self.assertIs(operation.field.default, NOT_PROVIDED)

    def test_existing_rows_are_not_rewritten(self):
        """
        Historical values stay put. They are covered by
        LEGACY_UNKNOWN_PROVENANCE, and public eligibility rejects them — which
        is the honest treatment. Rewriting them would destroy data on a guess.
        """
        operations = self._migration().Migration.operations

        self.assertTrue(operations)
        self.assertFalse(any(type(o).__name__ == 'RunPython' for o in operations))
