"""
D5 — Confidence, independent of Coverage.

    COVERAGE   how much of what the assessment needs is supported at all
    CONFIDENCE how good that support is

A company can have 100% coverage built entirely on unverified press releases —
complete, and weak. Another can have 40% coverage from independently verified
audits — incomplete, and strong. A single number cannot say both.
"""
from datetime import date, timedelta

from django.test import SimpleTestCase, TestCase

from companies import provenance as prov
from companies.confidence import (
    CONFIDENCE_HIGH, CONFIDENCE_INSUFFICIENT, CONFIDENCE_LOW, CONFIDENCE_MEDIUM,
    CONFIDENCE_ORDER, confidence_for,
)
from companies.evidence import (
    PROVENANCE_ESTIMATED, PROVENANCE_INFERRED, PROVENANCE_MEASURED,
    PROVENANCE_SEEDED, coverage_for,
)
from companies.testing import populated
from league.models import Company


def _profile(slug, **overrides):
    company = Company.objects.create(name=slug, slug=slug, country='UK')
    return populated(company, **overrides)


def _memory(profile, verification='pending', tier='uploaded', expiry=None):
    from evidence_memory.models import EvidenceMemory

    return EvidenceMemory.objects.create(
        company=profile, text_chunk='Audited figure.', source_type='company_report',
        verification_status=verification, review_tier=tier, expiry_date=expiry)


def _record(profile, origin, count=16, review='proposed', evidence=None):
    for key in sorted(prov.MATERIAL_METRIC_KEYS)[:count]:
        prov.record(profile, key, origin, written_by='t',
                    review_status=review, evidence=evidence)
    return profile


class Vocabulary(SimpleTestCase):

    def test_it_reuses_the_decision_studio_labels(self):
        from decision_studio.models import DecisionQuery

        labels = {value for value, _ in DecisionQuery.CONFIDENCE_CHOICES}

        self.assertEqual(set(CONFIDENCE_ORDER), labels)

    def test_the_order_runs_weakest_to_strongest(self):
        self.assertEqual(CONFIDENCE_ORDER,
                         (CONFIDENCE_INSUFFICIENT, CONFIDENCE_LOW,
                          CONFIDENCE_MEDIUM, CONFIDENCE_HIGH))

    def test_no_numeric_confidence_is_produced(self):
        """
        Categorical inputs. Combining them into '0.72 confidence' would
        manufacture precision the data cannot support — the same fabrication
        this programme has spent eleven phases removing.
        """
        import inspect

        from companies import confidence

        self.assertNotIn('def confidence_score', inspect.getsource(confidence))


class NoEvidenceIsNotLowConfidence(TestCase):
    """
    'We looked and it is weak' and 'we have not looked' are different
    statements, and only one of them is a finding about the company.
    """

    def test_no_provenance_is_insufficient_not_low(self):
        report = confidence_for(_profile('conf-none'))

        self.assertEqual(report.label, CONFIDENCE_INSUFFICIENT)
        self.assertNotEqual(report.label, CONFIDENCE_LOW)

    def test_seeded_evidence_is_insufficient(self):
        profile = _record(_profile('conf-seeded'), PROVENANCE_SEEDED)

        self.assertEqual(confidence_for(profile).label, CONFIDENCE_INSUFFICIENT)

    def test_it_says_why(self):
        report = confidence_for(_profile('conf-why'))

        self.assertTrue(report.reasons)
        self.assertIn('no evidence', ' '.join(report.reasons).lower())

    def test_a_none_profile_does_not_raise(self):
        self.assertEqual(confidence_for(None).label, CONFIDENCE_INSUFFICIENT)


class Grading(TestCase):

    def test_measured_plus_review_is_high(self):
        profile = _record(_profile('conf-high'), PROVENANCE_MEASURED,
                          review='confirmed')

        self.assertEqual(confidence_for(profile).label, CONFIDENCE_HIGH)

    def test_measured_without_review_is_medium(self):
        profile = _record(_profile('conf-medium'), PROVENANCE_MEASURED)

        self.assertEqual(confidence_for(profile).label, CONFIDENCE_MEDIUM)

    def test_inferred_without_verification_is_low(self):
        profile = _record(_profile('conf-low'), PROVENANCE_INFERRED)

        self.assertEqual(confidence_for(profile).label, CONFIDENCE_LOW)

    def test_estimated_without_verification_is_low(self):
        profile = _record(_profile('conf-est'), PROVENANCE_ESTIMATED)

        self.assertEqual(confidence_for(profile).label, CONFIDENCE_LOW)

    def test_a_verified_source_lifts_inferred_to_medium(self):
        profile = _profile('conf-verified')
        memory = _memory(profile, verification='verified')
        _record(profile, PROVENANCE_INFERRED, evidence=memory)

        self.assertEqual(confidence_for(profile).label, CONFIDENCE_MEDIUM)

    def test_an_independently_verified_tier_also_counts(self):
        profile = _profile('conf-tier')
        memory = _memory(profile, tier='independently_verified')
        _record(profile, PROVENANCE_INFERRED, evidence=memory)

        self.assertEqual(confidence_for(profile).label, CONFIDENCE_MEDIUM)

    def test_merely_uploaded_does_not_count_as_corroboration(self):
        """A file being present is not a person having verified it."""
        profile = _profile('conf-uploaded')
        memory = _memory(profile, tier='uploaded')
        _record(profile, PROVENANCE_INFERRED, evidence=memory)

        self.assertEqual(confidence_for(profile).label, CONFIDENCE_LOW)

    def test_every_label_states_its_basis(self):
        for slug, origin, review in (('r-high', PROVENANCE_MEASURED, 'confirmed'),
                                     ('r-med', PROVENANCE_MEASURED, 'proposed'),
                                     ('r-low', PROVENANCE_INFERRED, 'proposed')):
            with self.subTest(slug=slug):
                profile = _record(_profile(slug), origin, review=review)
                self.assertTrue(confidence_for(profile).reasons)


class Staleness(TestCase):

    def test_a_stale_source_downgrades_high_to_medium(self):
        profile = _profile('conf-stale')
        memory = _memory(profile, verification='verified',
                         expiry=date(2020, 1, 1))
        _record(profile, PROVENANCE_MEASURED, review='confirmed', evidence=memory)

        report = confidence_for(profile)

        self.assertEqual(report.label, CONFIDENCE_MEDIUM)
        self.assertGreater(report.stale_sources, 0)

    def test_a_current_source_is_not_penalised(self):
        profile = _profile('conf-fresh')
        memory = _memory(profile, verification='verified',
                         expiry=date.today() + timedelta(days=365))
        _record(profile, PROVENANCE_MEASURED, review='confirmed', evidence=memory)

        report = confidence_for(profile)

        self.assertEqual(report.label, CONFIDENCE_HIGH)
        self.assertEqual(report.stale_sources, 0)

    def test_staleness_can_only_lower_a_label(self):
        profile = _profile('conf-stale-low')
        memory = _memory(profile, expiry=date(2020, 1, 1))
        _record(profile, PROVENANCE_INFERRED, evidence=memory)

        self.assertEqual(confidence_for(profile).label, CONFIDENCE_LOW)


class IndependentOfCoverage(TestCase):
    """The distinction this module exists to protect."""

    def test_full_coverage_with_weak_sources_is_not_high_confidence(self):
        profile = _record(_profile('full-weak'), PROVENANCE_INFERRED, count=16)

        self.assertEqual(coverage_for(profile).coverage_percent, 100)
        self.assertEqual(confidence_for(profile).label, CONFIDENCE_LOW)

    def test_partial_coverage_with_strong_sources_is_not_low_confidence(self):
        profile = _record(_profile('partial-strong'), PROVENANCE_MEASURED,
                          count=4, review='confirmed')

        report = coverage_for(profile)
        self.assertGreater(report.coverage_percent, 0)
        self.assertLess(report.coverage_percent, 100)
        self.assertEqual(confidence_for(profile).label, CONFIDENCE_HIGH)

    def test_the_two_do_not_track_each_other(self):
        weak_full = _record(_profile('t-weak-full'), PROVENANCE_INFERRED, count=16)
        strong_partial = _record(_profile('t-strong-partial'), PROVENANCE_MEASURED,
                                 count=4, review='confirmed')

        self.assertGreater(coverage_for(weak_full).coverage_percent,
                           coverage_for(strong_partial).coverage_percent)
        self.assertLess(
            CONFIDENCE_ORDER.index(confidence_for(weak_full).label),
            CONFIDENCE_ORDER.index(confidence_for(strong_partial).label))

    def test_confidence_does_not_gate_publication_by_itself(self):
        """Advisory. The publication gate decides; this reports."""
        profile = _record(_profile('conf-advisory'), PROVENANCE_INFERRED)

        self.assertFalse(confidence_for(profile).is_publishable_quality)


class ReservedHooks(SimpleTestCase):

    def test_contradiction_detection_is_a_documented_no_op(self):
        """
        Nothing records contradictions between sources today, and inferring
        disagreement from text would be a research problem wearing a confidence
        label. The hook exists so the gap is visible rather than forgotten.
        """
        from companies.confidence import _contradiction_penalty

        self.assertEqual(_contradiction_penalty(None), 0)
        self.assertIn('Reserved', _contradiction_penalty.__doc__)
