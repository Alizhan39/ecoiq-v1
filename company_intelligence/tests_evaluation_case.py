"""
Real review work as evaluation-case material.

The property that matters most: a case pairs a human's judgement with the exact
text they judged. If the source changes afterwards, that pairing silently
becomes wrong — a mislabelled example, which is worse in a benchmark than a
missing one. These tests pin that the drift is detectable rather than hidden,
and that nothing here promotes a candidate into a set.
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from companies.models import CompanyProfile
from company_intelligence.models import (
    CompanyKPIAssessment, CompanyKPIEvidenceLink, EvidenceReviewAction,
)
from company_intelligence.services.evaluation_case import (
    VERSION_DRIFTED, VERSION_MATCHES, VERSION_UNKNOWN, case_from_review,
    corpus_summary, version_status,
)
from company_intelligence.services.evidence_review import apply_review_decision
from evidence_memory.models import EvidenceMemory
from league.models import Company


class EvaluationCaseTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.reviewer = User.objects.create_user(
            username='named-reviewer', password='x', is_staff=True)
        self.company = Company.objects.create(name='Testco', slug='testco')
        self.profile = CompanyProfile.objects.create(company=self.company)
        self.assessment = CompanyKPIAssessment.objects.create(
            company=self.profile, kpi_id=103)

    def _link(self, text='Original evidence text.'):
        evidence = EvidenceMemory.objects.create(
            text_chunk=text, source_type='harvester_evidence',
            source_reference='harvester.Evidence:1',
            source_url='https://example.org/x', company=self.profile,
            date_collected=datetime.date(2026, 1, 1), is_demo=False)
        return CompanyKPIEvidenceLink.objects.create(
            assessment=self.assessment, evidence=evidence,
            relationship='context', review_state='proposed')

    def _review(self, link, action='confirm_supports', reason='Read it; it supports.'):
        apply_review_decision(link, action, self.reviewer, reason=reason)
        return EvidenceReviewAction.objects.order_by('-pk').first()


class VersionPinningTests(EvaluationCaseTestCase):
    """
    A review is a judgement about a specific piece of text.
    """

    def test_a_review_records_which_text_it_judged(self):
        action = self._review(self._link())
        self.assertTrue(action.evidence_version)

    def test_an_unchanged_evidence_matches(self):
        action = self._review(self._link())
        self.assertEqual(version_status(action), VERSION_MATCHES)

    def test_changed_evidence_is_detected_as_drifted(self):
        """
        The failure this exists to prevent: a label pointing at text nobody
        with that opinion ever read.
        """
        link = self._link()
        action = self._review(link)
        link.evidence.text_chunk = 'The source was revised and now says something else.'
        link.evidence.save()
        action.refresh_from_db()
        self.assertEqual(version_status(action), VERSION_DRIFTED)

    def test_a_review_with_no_recorded_version_is_unknown_not_matching(self):
        """
        Rows written before the field existed. Unknown is honest; assuming a
        match would assert something about the past nobody recorded.
        """
        action = self._review(self._link())
        action.evidence_version = ''
        action.save()
        self.assertEqual(version_status(action), VERSION_UNKNOWN)

    def test_the_pinned_version_is_never_recomputed(self):
        """
        A hash computed at read time would say what the text is now, which
        would make drift undetectable by construction.
        """
        link = self._link()
        action = self._review(link)
        pinned = action.evidence_version
        link.evidence.text_chunk = 'Changed.'
        link.evidence.save()
        action.refresh_from_db()
        self.assertEqual(action.evidence_version, pinned)


class CaseShapeTests(EvaluationCaseTestCase):

    def test_a_case_carries_input_label_and_provenance(self):
        case = case_from_review(self._review(self._link()))
        self.assertEqual(case['input']['principle_id'], 103)
        self.assertTrue(case['input']['question'])
        self.assertEqual(case['input']['entity'], 'testco')
        self.assertEqual(case['ground_truth']['label'], 'supports')
        self.assertEqual(case['provenance']['reviewer'], 'named-reviewer')
        self.assertIsNotNone(case['provenance']['reviewed_at'])

    def test_the_rationale_travels_with_the_label(self):
        """A label without reasoning cannot be checked by anyone."""
        case = case_from_review(self._review(self._link()))
        self.assertEqual(case['ground_truth']['rationale'], 'Read it; it supports.')

    def test_a_usable_review_is_benchmark_ready(self):
        case = case_from_review(self._review(self._link()))
        self.assertTrue(case['is_benchmark_ready'])
        self.assertEqual(case['blockers'], [])


class NotUsableTests(EvaluationCaseTestCase):
    """A candidate that cannot be a case says why, rather than being dropped."""

    def test_a_rejection_is_not_a_label_about_the_evidence(self):
        case = case_from_review(self._review(self._link(), action='reject',
                                             reason='Wrong principle.'))
        self.assertIsNone(case['ground_truth']['label'])
        self.assertFalse(case['is_benchmark_ready'])
        self.assertTrue(any('rather than a classification' in b
                            for b in case['blockers']))

    def test_a_label_with_no_rationale_is_not_ready(self):
        case = case_from_review(self._review(self._link(), reason=''))
        self.assertFalse(case['is_benchmark_ready'])
        self.assertTrue(any('No rationale' in b for b in case['blockers']))

    def test_drifted_evidence_blocks_the_case(self):
        link = self._link()
        action = self._review(link)
        link.evidence.text_chunk = 'Revised.'
        link.evidence.save()
        action.refresh_from_db()
        case = case_from_review(action)
        self.assertFalse(case['is_benchmark_ready'])
        self.assertTrue(any('has changed since this review' in b
                            for b in case['blockers']))

    def test_no_label_is_ever_invented(self):
        """
        The whole point of a human-labelled set. A missing label stays missing.
        """
        for action_name in ('reject', 'needs_more_evidence', 'mark_disputed'):
            link = self._link()
            link.review_state = 'confirmed'
            link.save()
            action = self._review(link, action=action_name, reason='because')
            case = case_from_review(action)
            self.assertIsNone(case['ground_truth']['label'], action_name)


class CorpusTests(EvaluationCaseTestCase):

    def test_an_untouched_queue_yields_a_corpus_of_zero(self):
        """
        Zero is a real measurement and the honest answer today. It is NOT the
        same as NOT YET MEASURED, which is what a metric nobody ran says.
        """
        summary = corpus_summary(EvidenceReviewAction.objects.all())
        self.assertEqual(summary['reviews_examined'], 0)
        self.assertEqual(summary['benchmark_ready'], 0)
        self.assertEqual(summary['labels'], {})

    def test_the_corpus_never_claims_to_be_published(self):
        self._review(self._link())
        summary = corpus_summary(EvidenceReviewAction.objects.all())
        self.assertFalse(summary['published_as_benchmark'])
        self.assertIn('human act', summary['note'])

    def test_ready_and_unusable_reviews_are_counted_apart(self):
        self._review(self._link())
        second = self._link()
        second.evidence.source_reference = 'harvester.Evidence:2'
        second.evidence.save()
        self._review(second, action='reject', reason='Not relevant.')

        summary = corpus_summary(EvidenceReviewAction.objects.all())
        self.assertEqual(summary['reviews_examined'], 2)
        self.assertEqual(summary['benchmark_ready'], 1)
        self.assertEqual(summary['not_ready'], 1)
        self.assertEqual(summary['labels'], {'supports': 1})

    def test_the_reviewers_behind_a_corpus_are_named(self):
        """
        A labelled set is only as checkable as the people who labelled it.
        """
        self._review(self._link())
        summary = corpus_summary(EvidenceReviewAction.objects.all())
        self.assertEqual(summary['reviewers'], ['named-reviewer'])

    def test_drift_is_reported_at_corpus_level(self):
        link = self._link()
        self._review(link)
        link.evidence.text_chunk = 'Revised.'
        link.evidence.save()
        summary = corpus_summary(EvidenceReviewAction.objects.all())
        self.assertEqual(summary['drifted'], 1)
        self.assertEqual(summary['benchmark_ready'], 0)


class NoAutoPublicationTests(EvaluationCaseTestCase):
    """Building a candidate must not change anything."""

    def test_reading_candidates_writes_nothing(self):
        action = self._review(self._link())
        before = EvidenceReviewAction.objects.count()
        case_from_review(action)
        corpus_summary(EvidenceReviewAction.objects.all())
        self.assertEqual(EvidenceReviewAction.objects.count(), before)
        action.refresh_from_db()
        self.assertEqual(action.action, 'confirm_supports')
