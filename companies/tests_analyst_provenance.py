"""
D3C-5 — human analyst provenance.

The last writer family, and the only one allowed to say `confirmed`.

Two things carry the weight here:

  1. An analyst must not be able to label a DERIVED value MEASURED. ml.score is
     a gradient-boosting output; company.ecoiq_total is a composite. Nobody
     measured either, and MEASURED is an origin that makes a metric publicly
     defensible.

  2. The value and the provenance are one write. A value with no provenance is
     relabelled LEGACY_UNKNOWN_PROVENANCE by the next backfill; a provenance
     row with no value asserts a number never stored.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import SimpleTestCase, TestCase

from companies import analyst
from companies import metric_registry as registry
from companies import provenance as prov
from companies.evidence import (
    PROVENANCE_ESTIMATED, PROVENANCE_INFERRED, PROVENANCE_MEASURED,
    PROVENANCE_MODELLED, PROVENANCE_SEEDED, PROVENANCE_UNKNOWN,
)
from companies.models import CompanyMetricProvenance, CompanyProfile
from league.models import Company


def _populated(company, **fields):
    """
    A profile whose material inputs are EXPLICIT.

    Before D4C these fixtures set no scores at all and relied on
    default=50.0 to invent sixteen of them. The tests read as though they
    set up a company; they set up nothing. Now the data is stated, and a
    caller that wants an unknown overrides that one field by name.
    """
    from companies.models import CompanyProfile
    from companies.testing import MATERIAL_FIELDS, FIXTURE_VALUE

    values = {name: FIXTURE_VALUE for name in MATERIAL_FIELDS}
    values.update(fields)
    return CompanyProfile.objects.create(company=company, **values)


User = get_user_model()


def _profile(slug='declared'):
    company = Company.objects.create(name=slug, slug=slug, country='UK')
    return _populated(company=company, status='public',
                                         pollution_level='low')


def _analyst(username='analyst', confirm=False):
    user = User.objects.create_user(username=username, password='x',
                                    is_staff=True)
    if confirm:
        user.user_permissions.add(
            Permission.objects.get(codename='change_companymetricprovenance'))
        user = User.objects.get(pk=user.pk)      # refresh the permission cache
    return user


def _evidence(profile):
    from evidence_memory.models import EvidenceMemory

    return EvidenceMemory.objects.create(
        company=profile, text_chunk='Audited report, p. 42: 1,250,000 t CO2e.',
        source_url='https://example.com/audit.pdf', source_type='company_report')


class WhatAnAnalystMayDeclare(SimpleTestCase):

    def test_only_three_origins_are_declarable(self):
        self.assertEqual(set(analyst.ANALYST_ORIGINS),
                         {PROVENANCE_MEASURED, PROVENANCE_ESTIMATED,
                          PROVENANCE_INFERRED})

    def test_modelled_is_not_declarable_by_hand(self):
        """A person does not model a value; a calculator does, and records it."""
        self.assertNotIn(PROVENANCE_MODELLED, analyst.ANALYST_ORIGINS)

    def test_seeded_and_legacy_are_not_declarable(self):
        self.assertNotIn(PROVENANCE_SEEDED, analyst.ANALYST_ORIGINS)
        self.assertNotIn(PROVENANCE_UNKNOWN, analyst.ANALYST_ORIGINS)

    def test_a_material_metric_permits_all_three(self):
        self.assertEqual(set(analyst.permitted_origins('water_impact_score')),
                         set(analyst.ANALYST_ORIGINS))

    def test_a_derived_metric_never_permits_measured(self):
        for key in ('company.ecoiq_total', 'ml.score', 'mizan.score',
                    'ethics.nei', 'greenwashing.risk'):
            with self.subTest(key=key):
                self.assertNotIn(PROVENANCE_MEASURED,
                                 analyst.permitted_origins(key))

    def test_the_metric_list_comes_from_the_registry(self):
        keys = {key for key, _ in analyst.available_metrics()}
        self.assertEqual(keys, set(registry.VALID_KEYS))

    def test_measured_is_the_only_origin_requiring_evidence(self):
        self.assertEqual(set(analyst.REQUIRES_EVIDENCE), {PROVENANCE_MEASURED})


class Validation(TestCase):

    def setUp(self):
        self.profile = _profile()
        self.user = _analyst()

    def _declare(self, **kwargs):
        params = dict(metric_key='water_impact_score', value=61.0,
                      origin=PROVENANCE_ESTIMATED, user=self.user)
        params.update(kwargs)
        return analyst.declare_metric(self.profile, params.pop('metric_key'),
                                      params.pop('value'), params.pop('origin'),
                                      **params)

    def test_an_unregistered_metric_is_refused(self):
        with self.assertRaises(analyst.AnalystDeclarationError) as ctx:
            self._declare(metric_key='not_a_metric')
        self.assertIn('not a registered metric', str(ctx.exception))

    def test_a_derived_metric_cannot_be_declared_measured(self):
        """The guardrail this phase exists for."""
        with self.assertRaises(analyst.AnalystDeclarationError) as ctx:
            self._declare(metric_key='company.ecoiq_total',
                          origin=PROVENANCE_MEASURED,
                          evidence=_evidence(self.profile))

        message = str(ctx.exception)
        self.assertIn('not an honest origin', message)
        self.assertIn('nobody observed it directly', message)

    def test_an_ml_output_cannot_be_declared_measured(self):
        with self.assertRaises(analyst.AnalystDeclarationError):
            self._declare(metric_key='ml.score', origin=PROVENANCE_MEASURED,
                          evidence=_evidence(self.profile))

    def test_a_derived_metric_can_still_be_declared_inferred(self):
        row = self._declare(metric_key='company.ecoiq_total', value=64.0,
                            origin=PROVENANCE_INFERRED)

        self.assertEqual(row.origin, PROVENANCE_INFERRED)

    def test_modelled_is_refused_with_a_readable_reason(self):
        with self.assertRaises(analyst.AnalystDeclarationError) as ctx:
            self._declare(origin=PROVENANCE_MODELLED)

        self.assertIn('cannot be declared by hand', str(ctx.exception))

    def test_seeded_is_refused(self):
        with self.assertRaises(analyst.AnalystDeclarationError):
            self._declare(origin=PROVENANCE_SEEDED)

    def test_measured_without_evidence_is_refused(self):
        with self.assertRaises(analyst.AnalystDeclarationError) as ctx:
            self._declare(origin=PROVENANCE_MEASURED)

        self.assertIn('Attach the evidence', str(ctx.exception))

    def test_measured_with_evidence_is_accepted(self):
        row = self._declare(origin=PROVENANCE_MEASURED,
                            evidence=_evidence(self.profile))

        self.assertEqual(row.origin, PROVENANCE_MEASURED)
        self.assertIsNotNone(row.evidence)

    def test_estimated_does_not_require_evidence(self):
        self.assertEqual(self._declare(origin=PROVENANCE_ESTIMATED).origin,
                         PROVENANCE_ESTIMATED)

    def test_a_none_value_is_refused(self):
        with self.assertRaises(analyst.AnalystDeclarationError) as ctx:
            self._declare(value=None)

        self.assertIn('an absent metric is already unknown', str(ctx.exception))

    def test_a_genuine_zero_is_accepted(self):
        row = self._declare(value=0.0)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.water_impact_score, 0.0)
        self.assertIsNotNone(row)


class TheAtomicWrite(TestCase):

    def setUp(self):
        self.profile = _profile()
        self.user = _analyst()

    def test_the_value_reaches_its_canonical_field(self):
        analyst.declare_metric(self.profile, 'water_impact_score', 61.0,
                               PROVENANCE_ESTIMATED, user=self.user)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.water_impact_score, 61.0)

    def test_the_provenance_row_accompanies_it(self):
        analyst.declare_metric(self.profile, 'water_impact_score', 61.0,
                               PROVENANCE_ESTIMATED, user=self.user)

        row = prov.current(self.profile, 'water_impact_score')
        self.assertEqual(row.origin, PROVENANCE_ESTIMATED)
        self.assertEqual(row.value, 61.0)

    def test_the_declaring_user_is_recorded(self):
        analyst.declare_metric(self.profile, 'water_impact_score', 61.0,
                               PROVENANCE_ESTIMATED, user=self.user)

        row = prov.current(self.profile, 'water_impact_score')
        self.assertEqual(row.created_by, self.user)
        self.assertEqual(row.written_by, 'companies.analyst.declare_metric')

    def test_a_company_level_metric_writes_to_the_company(self):
        analyst.declare_metric(self.profile, 'ml.score', 70.0,
                               PROVENANCE_INFERRED, user=self.user)

        self.profile.company.refresh_from_db()
        self.assertEqual(float(self.profile.company.ml_score), 70.0)

    def test_an_ephemeral_metric_stores_its_value_on_the_row(self):
        row = analyst.declare_metric(self.profile, 'greenwashing.risk', 42.0,
                                     PROVENANCE_INFERRED, user=self.user)

        self.assertEqual(row.recorded_value, 42.0)

    def test_a_persisted_metric_stores_no_recorded_value(self):
        row = analyst.declare_metric(self.profile, 'water_impact_score', 61.0,
                                     PROVENANCE_ESTIMATED, user=self.user)

        self.assertIsNone(row.recorded_value)

    def test_optional_fields_are_carried_through(self):
        evidence = _evidence(self.profile)
        row = analyst.declare_metric(
            self.profile, 'water_impact_score', 61.0, PROVENANCE_MEASURED,
            user=self.user, evidence=evidence, methodology='p.42 of the audit',
            confidence=0.82, notes='cross-checked against the 2024 filing',
            source_quality='primary')

        self.assertEqual(row.evidence, evidence)
        self.assertEqual(row.methodology, 'p.42 of the audit')
        self.assertEqual(row.confidence, 0.82)
        self.assertEqual(row.notes, 'cross-checked against the 2024 filing')
        self.assertEqual(row.source_quality, 'primary')

    def test_confidence_stays_none_when_not_supplied(self):
        row = analyst.declare_metric(self.profile, 'water_impact_score', 61.0,
                                     PROVENANCE_ESTIMATED, user=self.user)

        self.assertIsNone(row.confidence, 'a default would fabricate certainty')

    def test_a_failed_provenance_write_rolls_back_the_value(self):
        from unittest.mock import patch

        self.profile.water_impact_score = 10.0
        self.profile.save()

        with self.assertRaises(RuntimeError):
            with patch('companies.provenance.record',
                       side_effect=RuntimeError('injected')):
                analyst.declare_metric(self.profile, 'water_impact_score', 61.0,
                                       PROVENANCE_ESTIMATED, user=self.user)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.water_impact_score, 10.0)


class ReviewAndPermissions(TestCase):

    def setUp(self):
        self.profile = _profile()

    def test_a_declaration_defaults_to_proposed(self):
        row = analyst.declare_metric(self.profile, 'water_impact_score', 61.0,
                                     PROVENANCE_ESTIMATED, user=_analyst())

        self.assertEqual(row.review_status, 'proposed')
        self.assertIsNone(row.reviewed_by)

    def test_confirming_requires_the_permission(self):
        plain = _analyst('plain')

        with self.assertRaises(analyst.AnalystDeclarationError) as ctx:
            analyst.declare_metric(self.profile, 'water_impact_score', 61.0,
                                   PROVENANCE_ESTIMATED, user=plain,
                                   review_status='confirmed')

        self.assertIn('do not have permission', str(ctx.exception))

    def test_a_permitted_reviewer_may_confirm(self):
        reviewer = _analyst('reviewer', confirm=True)

        row = analyst.declare_metric(self.profile, 'water_impact_score', 61.0,
                                     PROVENANCE_ESTIMATED, user=reviewer,
                                     review_status='confirmed')

        self.assertEqual(row.review_status, 'confirmed')
        self.assertEqual(row.reviewed_by, reviewer)
        self.assertIsNotNone(row.reviewed_at)

    def test_an_anonymous_user_cannot_confirm(self):
        from django.contrib.auth.models import AnonymousUser

        with self.assertRaises(analyst.AnalystDeclarationError):
            analyst.declare_metric(self.profile, 'water_impact_score', 61.0,
                                   PROVENANCE_ESTIMATED, user=AnonymousUser(),
                                   review_status='confirmed')

    def test_no_automated_writer_ever_confirms(self):
        """
        The rule that gives 'confirmed' its meaning. Every other writer family
        proposes; this is the only path to a confirmed row.
        """
        from companies.scoring import recalculate_and_save
        from ingestion import provenance as ing_prov

        ing_prov.record_ingestion_write(
            self.profile, {k: 60.0 for k in ing_prov.SIGNAL_FOR_METRIC})
        recalculate_and_save(self.profile)

        statuses = set(CompanyMetricProvenance.objects
                       .filter(company=self.profile)
                       .values_list('review_status', flat=True))
        self.assertEqual(statuses, {'proposed'})


class HistoryIsAppendOnly(TestCase):

    def setUp(self):
        self.profile = _profile()
        self.user = _analyst()
        self.first = analyst.declare_metric(
            self.profile, 'water_impact_score', 61.0, PROVENANCE_ESTIMATED,
            user=self.user, notes='first pass')

    def test_a_second_declaration_supersedes_the_first(self):
        analyst.declare_metric(self.profile, 'water_impact_score', 72.0,
                               PROVENANCE_MEASURED, user=self.user,
                               evidence=_evidence(self.profile))

        self.first.refresh_from_db()
        self.assertFalse(self.first.is_current)
        self.assertEqual(prov.current(self.profile, 'water_impact_score').origin,
                         PROVENANCE_MEASURED)

    def test_the_earlier_declaration_is_not_edited(self):
        analyst.declare_metric(self.profile, 'water_impact_score', 72.0,
                               PROVENANCE_ESTIMATED, user=self.user)

        self.first.refresh_from_db()
        self.assertEqual(self.first.origin, PROVENANCE_ESTIMATED)
        self.assertEqual(self.first.notes, 'first pass')
        self.assertEqual(self.first.created_by, self.user)

    def test_who_said_what_stays_answerable(self):
        second = _analyst('second-analyst')
        analyst.declare_metric(self.profile, 'water_impact_score', 72.0,
                               PROVENANCE_ESTIMATED, user=second)

        rows = list(prov.history(self.profile, 'water_impact_score'))
        self.assertEqual(len(rows), 2)
        self.assertEqual({r.created_by for r in rows}, {self.user, second})

    def test_exactly_one_current_row_survives(self):
        from django.db.models import Count

        for value in (62.0, 63.0, 64.0):
            analyst.declare_metric(self.profile, 'water_impact_score', value,
                                   PROVENANCE_ESTIMATED, user=self.user)

        dupes = (CompanyMetricProvenance.objects
                 .filter(company=self.profile, is_current=True)
                 .values('metric_key').annotate(n=Count('id')).filter(n__gt=1))
        self.assertEqual(dupes.count(), 0)


class Defensibility(TestCase):

    def setUp(self):
        self.profile = _profile()
        self.user = _analyst()

    def test_a_measured_declaration_is_defensible(self):
        analyst.declare_metric(self.profile, 'water_impact_score', 61.0,
                               PROVENANCE_MEASURED, user=self.user,
                               evidence=_evidence(self.profile))

        self.assertTrue(prov.is_publicly_defensible(self.profile,
                                                    'water_impact_score'))

    def test_an_estimated_declaration_is_defensible(self):
        analyst.declare_metric(self.profile, 'water_impact_score', 61.0,
                               PROVENANCE_ESTIMATED, user=self.user)

        self.assertTrue(prov.is_publicly_defensible(self.profile,
                                                    'water_impact_score'))

    def test_a_declaration_cannot_launder_a_seeded_neighbour(self):
        """
        Declaring one metric does not rehabilitate the rest of the graph.
        """
        from companies.scoring import recalculate_and_save

        for key in sorted(prov.MATERIAL_METRIC_KEYS):
            prov.record(self.profile, key, PROVENANCE_SEEDED,
                        written_by='seed:test')
        analyst.declare_metric(self.profile, 'water_impact_score', 61.0,
                               PROVENANCE_MEASURED, user=self.user,
                               evidence=_evidence(self.profile))
        recalculate_and_save(self.profile)

        self.assertTrue(prov.is_publicly_defensible(self.profile,
                                                    'water_impact_score'))
        self.assertFalse(prov.is_derived_publicly_defensible(
            self.profile, 'company.ecoiq_total'))


class AdminForm(TestCase):

    def setUp(self):
        self.profile = _profile()
        self.user = _analyst('admin-user', confirm=True)

    def _form(self, **overrides):
        from companies.admin import AnalystDeclarationForm

        class FakeRequest:
            user = self.user

        data = {'company': self.profile.pk, 'metric_key': 'water_impact_score',
                'value': 61.0, 'origin': PROVENANCE_ESTIMATED,
                'review_status': 'proposed', 'methodology': '', 'notes': '',
                'source_quality': ''}
        data.update(overrides)
        return AnalystDeclarationForm(data=data, request=FakeRequest())

    def test_a_valid_declaration_saves_value_and_provenance(self):
        form = self._form()
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.water_impact_score, 61.0)
        self.assertIsNotNone(prov.current(self.profile, 'water_impact_score'))

    def test_the_form_refuses_measured_on_a_derived_metric(self):
        form = self._form(metric_key='company.ecoiq_total',
                          origin=PROVENANCE_MEASURED)

        self.assertFalse(form.is_valid())
        self.assertIn('not an honest origin', str(form.errors))

    def test_the_form_refuses_measured_without_evidence(self):
        form = self._form(origin=PROVENANCE_MEASURED)

        self.assertFalse(form.is_valid())
        self.assertIn('Attach the evidence', str(form.errors))

    def test_the_metric_choices_come_from_the_registry(self):
        choices = {key for key, _ in self._form().fields['metric_key'].choices}

        self.assertEqual(choices, set(registry.VALID_KEYS))

    def test_saving_creates_exactly_one_row(self):
        form = self._form()
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        self.assertEqual(CompanyMetricProvenance.objects.filter(
            company=self.profile, metric_key='water_impact_score').count(), 1)
