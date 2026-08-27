"""
The recommendation a reviewer sees, and the boundaries it must not cross.

A recommendation sitting beside a decision field is an anchor whether or not
anyone intends it as one. These tests pin the two things that keep it safe: it
never asserts a valence it cannot establish, and it cannot become a standing
without a named human.
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from companies.models import CompanyProfile
from company_intelligence.models import (
    CompanyKPIAssessment, CompanyKPIEvidenceLink, EvidenceReviewAction,
)
from company_intelligence.services.evidence_review import apply_review_decision
from company_intelligence.services.review_recommendation import (
    recommendation_for_link, review_packet,
)
from evidence_memory.models import EvidenceMemory
from harvester.models import Evidence as HarvesterEvidence, Source, SourceDocument
from league.models import Company


class RecommendationTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Testco', slug='testco')
        self.profile = CompanyProfile.objects.create(company=self.company)
        self.assessment = CompanyKPIAssessment.objects.create(
            company=self.profile, kpi_id=16)

    def _link(self, *, source_type='sustainability_report', match_basis='Keyword overlap: waste',
              relationship='context', url='https://testco.example/s', content_hash='h1'):
        source = Source.objects.create(
            name='S', source_type=source_type, source_url=url,
            source_owner='Testco Inc.', company=self.profile)
        document = SourceDocument.objects.create(
            source=source, company=self.profile, company_slug='testco',
            title='Testco Report', document_type=source_type,
            publisher='Testco Inc.', url=url,
            publication_date=datetime.date(2026, 1, 1), content_hash=content_hash)
        evidence = HarvesterEvidence.objects.create(
            company=self.profile, company_slug='testco', source=source,
            document=document, title='Testco Report', url=url,
            excerpt='Body.', category='environmental',
            document_type=source_type, content_hash=content_hash)
        memory = EvidenceMemory.objects.create(
            text_chunk='Body.', source_type='harvester_evidence',
            source_reference=f'harvester.Evidence:{evidence.pk}',
            source_url=url, company=self.profile, is_demo=False)
        return CompanyKPIEvidenceLink.objects.create(
            assessment=self.assessment, evidence=memory,
            relationship=relationship, review_state='proposed',
            match_basis=match_basis)


class NoValenceTests(RecommendationTestCase):
    """
    The matcher links on keyword overlap and records `context` for every
    candidate. Shared vocabulary shows a document is ABOUT a topic; it cannot
    show whether the document supports or damns the organisation on it.
    """

    def test_a_keyword_match_never_recommends_supports_or_conflicts(self):
        recommendation = recommendation_for_link(self._link())
        self.assertNotIn(recommendation['standing'], ('SUPPORTS', 'CONFLICTS',
                                                      'supports', 'conflicts'))

    def test_no_recommendation_in_any_configuration_asserts_a_valence(self):
        combinations = [
            (source_type, basis)
            for source_type in ('sec_edgar', 'sustainability_report',
                                'company_website', 'some_unmapped_type')
            for basis in ('Keyword overlap: waste', '', 'Something unrecognised')
        ]
        # Distinct url/hash per case: SourceDocument is UNIQUE on
        # (company_slug, url, content_hash), and two of these bases happen to be
        # the same length.
        for index, (source_type, basis) in enumerate(combinations):
            link = self._link(source_type=source_type, match_basis=basis,
                              url=f'https://testco.example/case-{index}',
                              content_hash=f'hash-{index}')
            standing = recommendation_for_link(link)['standing']
            self.assertNotIn(
                standing, ('SUPPORTS', 'CONFLICTS'),
                f'valence suggested for {source_type!r} / {basis!r}')

    def test_the_reason_says_why_no_valence_is_offered(self):
        reason = recommendation_for_link(self._link())['reason']
        self.assertIn('keyword overlap', reason.lower())
        self.assertIn('cannot show', reason.lower())

    def test_a_weak_source_is_flagged_as_needing_a_stronger_one(self):
        link = self._link(source_type='company_website')
        self.assertEqual(recommendation_for_link(link)['standing'],
                         'NEEDS_STRONGER_SOURCE')

    def test_an_authoritative_source_is_worth_reading_but_still_undecided(self):
        link = self._link(source_type='sec_edgar')
        recommendation = recommendation_for_link(link)
        self.assertEqual(recommendation['standing'], 'CONTEXT')
        self.assertIn('worth reading', recommendation['reason'])

    def test_no_recorded_basis_offers_no_standing_at_all(self):
        link = self._link(match_basis='')
        recommendation = recommendation_for_link(link)
        self.assertIsNone(recommendation['standing'])
        self.assertIn('nothing for a recommendation to rest on',
                      recommendation['reason'])


class NonBindingTests(RecommendationTestCase):

    def test_every_recommendation_declares_itself_non_binding(self):
        for source_type in ('sec_edgar', 'company_website'):
            link = self._link(source_type=source_type,
                              url=f'https://testco.example/{source_type}',
                              content_hash=source_type)
            recommendation = recommendation_for_link(link)
            self.assertFalse(recommendation['is_binding'])
            self.assertIn('not reviewed', recommendation['label'].lower())
            self.assertIn('counts toward nothing', recommendation['label'].lower())

    def test_producing_a_recommendation_changes_no_state(self):
        link = self._link()
        recommendation_for_link(link)
        review_packet([link])
        link.refresh_from_db()
        self.assertEqual(link.review_state, 'proposed')
        self.assertEqual(EvidenceReviewAction.objects.count(), 0)
        self.assertEqual(
            CompanyKPIAssessment.objects.get(pk=self.assessment.pk).status,
            'not_assessed')

    def test_a_recommendation_is_not_a_review_action(self):
        """
        The record of who decided is what makes a finding auditable. A
        recommendation must never appear in that history.
        """
        link = self._link()
        recommendation_for_link(link)
        self.assertFalse(EvidenceReviewAction.objects.exists())


class ImmutableHistoryTests(RecommendationTestCase):
    """A later reviewer may supersede a decision. Nobody may erase one."""

    def setUp(self):
        super().setUp()
        User = get_user_model()
        self.first = User.objects.create(username='first-reviewer', is_staff=True)
        self.second = User.objects.create(username='second-reviewer', is_staff=True)

    def test_a_review_records_who_decided(self):
        link = self._link()
        apply_review_decision(link, 'confirm_context', self.first, reason='ok')
        action = EvidenceReviewAction.objects.get()
        self.assertEqual(action.reviewer, self.first)
        self.assertEqual(action.action, 'confirm_context')

    def test_superseding_a_decision_preserves_the_first_one(self):
        link = self._link()
        apply_review_decision(link, 'confirm_context', self.first, reason='first call')
        apply_review_decision(link, 'mark_disputed', self.second, reason='second call')

        actions = list(EvidenceReviewAction.objects.order_by('pk'))
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0].reviewer, self.first)
        self.assertEqual(actions[0].action, 'confirm_context')
        self.assertEqual(actions[1].reviewer, self.second)
        link.refresh_from_db()
        self.assertEqual(link.review_state, 'disputed')

    def test_the_recommendation_does_not_change_after_a_human_disagrees(self):
        """
        The machine's suggestion is a fact about the evidence, not about the
        decision. A reviewer choosing otherwise does not rewrite it — which is
        what makes the pair reviewable later.
        """
        link = self._link()
        before = recommendation_for_link(link)['standing']
        apply_review_decision(link, 'confirm_supports', self.first, reason='read it')
        link.refresh_from_db()
        self.assertEqual(link.review_state, 'confirmed')
        self.assertEqual(link.relationship, 'supports')
        self.assertEqual(recommendation_for_link(link)['standing'], before)


class PacketTests(RecommendationTestCase):

    def test_the_packet_carries_what_a_decision_needs(self):
        packet = review_packet([self._link()])
        item = packet[0]
        self.assertTrue(item['principle']['question'])
        self.assertEqual(item['source']['publisher'], 'Testco Inc.')
        self.assertEqual(item['source']['title'], 'Testco Report')
        self.assertIsNotNone(item['source']['content_hash'])
        self.assertTrue(item['recommendation']['must_decide'])

    def test_the_packet_never_shows_the_idempotency_key_as_a_title(self):
        item = review_packet([self._link()])[0]
        self.assertNotIn('harvester.Evidence:', item['source']['title'] or '')
        self.assertIn('harvester.Evidence:', item['source']['record_reference'])

    def test_the_packet_states_what_is_still_unknown(self):
        link = self._link(relationship='context')
        item = review_packet([link])[0]
        self.assertTrue(item['uncertainty'])
        self.assertTrue(any('context only' in gap for gap in item['uncertainty']))

    def test_the_packet_reports_that_nothing_counts_yet(self):
        item = review_packet([self._link()])[0]
        self.assertFalse(item['proposed']['counts_toward_assessment'])
