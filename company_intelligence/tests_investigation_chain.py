"""
The investigation chain, and the distinction it exists to preserve.

    NOT_INVESTIGATED   nobody has looked yet
    NONE_FOUND         someone looked and found nothing

"No verified remediation found" is a finding. "Remediation not investigated" is
an admission. A chain that rendered both as an empty section would let the
second borrow the credibility of the first, which is the failure these tests
exist to prevent.
"""
import datetime

from django.test import TestCase

from companies.models import CompanyProfile
from company_intelligence.models import (
    CompanyKPIAssessment, CompanyKPIEvidenceLink, KPIRemediationStep,
)
from company_intelligence.services.investigation_chain import (
    NONE_FOUND, NOT_INVESTIGATED, investigation_chain,
)
from company_intelligence.services.kpi_engine import recompute_assessment_status
from evidence_memory.models import EvidenceMemory
from league.models import Company

NODES = ('standing', 'finding', 'conflict', 'remediation',
         'residual_concern', 'decision_implication')


class ChainTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Testco', slug='testco')
        self.profile = CompanyProfile.objects.create(company=self.company)
        self.assessment = CompanyKPIAssessment.objects.create(
            company=self.profile, kpi_id=103)

    def _evidence(self, ref, *, legal_status='unclassified', tier='uploaded'):
        return EvidenceMemory.objects.create(
            text_chunk=f'Body {ref}', source_reference=ref,
            source_url='https://example.org/x', source_type='harvester_evidence',
            legal_status=legal_status, review_tier=tier, company=self.profile,
            date_collected=datetime.date(2026, 1, 1), is_demo=False)

    def _link(self, evidence, relationship='supports', state='confirmed'):
        link = CompanyKPIEvidenceLink.objects.create(
            assessment=self.assessment, evidence=evidence,
            relationship=relationship, review_state=state)
        recompute_assessment_status(self.assessment)
        return link

    def chain(self):
        self.assessment.refresh_from_db()
        return investigation_chain(self.assessment)


class NothingLookedAtTests(ChainTestCase):

    def test_every_node_is_present_even_with_no_evidence(self):
        """An omitted node reads as 'nothing to say'. There is always a state."""
        chain = self.chain()
        for node in NODES:
            self.assertIn(node, chain)
            self.assertTrue(chain[node]['state'])

    def test_every_downstream_node_is_not_investigated(self):
        chain = self.chain()
        for node in NODES:
            self.assertEqual(chain[node]['state'], NOT_INVESTIGATED, node)

    def test_a_company_never_assessed_still_gets_a_chain(self):
        """`assessment=None` yields the chain, not an absence of one."""
        chain = investigation_chain(None)
        self.assertFalse(chain['investigation_started'])
        for node in NODES:
            self.assertEqual(chain[node]['state'], NOT_INVESTIGATED, node)

    def test_requirements_are_not_investigated_rather_than_unmet(self):
        """
        An unmet requirement is a judgement about evidence that exists. With no
        evidence there is nothing to judge, and saying NOT_MET would read as a
        failure by the organisation.
        """
        for requirement in self.chain()['evidence_requirements']:
            self.assertEqual(requirement['state'], NOT_INVESTIGATED)


class AwaitingReviewTests(ChainTestCase):
    """
    Real evidence, none reviewed — production's exact state for the nine
    Walmart candidates.
    """

    def setUp(self):
        super().setUp()
        self._link(self._evidence('harvester.Evidence:1'), state='proposed')
        self._link(self._evidence('harvester.Evidence:2'), state='proposed')

    def test_evidence_is_recorded_as_awaiting_review(self):
        evidence = self.chain()['evidence']
        self.assertEqual(evidence['state'], 'AWAITING_REVIEW')
        self.assertEqual(evidence['awaiting_review'], 2)
        self.assertEqual(evidence['confirmed'], 0)
        self.assertIn('count toward nothing', evidence['detail'])

    def test_an_investigation_has_not_started(self):
        """Evidence in a queue is a queue, not an investigation in progress."""
        self.assertFalse(self.chain()['investigation_started'])

    def test_proposed_evidence_moves_no_downstream_node(self):
        chain = self.chain()
        for node in NODES:
            self.assertEqual(chain[node]['state'], NOT_INVESTIGATED, node)

    def test_remediation_says_nobody_looked_not_none_found(self):
        """
        The distinction that matters most. Unreviewed evidence must not produce
        'no verified remediation found', which would claim an enquiry nobody made.
        """
        remediation = self.chain()['remediation']
        self.assertEqual(remediation['state'], NOT_INVESTIGATED)
        self.assertIn('no remediation has been looked for', remediation['detail'])


class ReviewedTests(ChainTestCase):
    """Once a reviewer confirms, the chain populates."""

    def test_confirming_starts_the_investigation(self):
        self._link(self._evidence('harvester.Evidence:3'))
        self.assertTrue(self.chain()['investigation_started'])

    def test_no_conflict_found_is_distinguishable_from_not_looked(self):
        self._link(self._evidence('harvester.Evidence:4'))
        conflict = self.chain()['conflict']
        self.assertEqual(conflict['state'], NONE_FOUND)
        self.assertIn('none conflicts', conflict['detail'])

    def test_no_remediation_found_is_a_finding(self):
        self._link(self._evidence('harvester.Evidence:5'))
        remediation = self.chain()['remediation']
        self.assertEqual(remediation['state'], NONE_FOUND)
        self.assertIn('not an absence of enquiry', remediation['detail'])

    def test_requirements_report_what_is_missing_not_merely_insufficient(self):
        """
        One unclassified, uncorroborated item. The finding may still be
        'support'; the requirements say plainly why that rests on very little.
        """
        self._link(self._evidence('harvester.Evidence:6'))
        states = {r['key']: r['state'] for r in self.chain()['evidence_requirements']}
        self.assertEqual(states['corroboration'], 'NOT_MET')
        self.assertEqual(states['authority'], 'NOT_MET')
        self.assertEqual(states['independence'], 'NOT_MET')
        self.assertEqual(states['both_sides'], 'NOT_MET')

    def test_requirements_are_met_when_the_evidence_earns_it(self):
        self._link(self._evidence('harvester.Evidence:7',
                                  legal_status='final_regulatory_finding',
                                  tier='independently_verified'),
                   relationship='conflicts')
        self._link(self._evidence('harvester.Evidence:8'), relationship='supports')
        states = {r['key']: r['state'] for r in self.chain()['evidence_requirements']}
        self.assertEqual(states['corroboration'], 'MET')
        self.assertEqual(states['authority'], 'MET')
        self.assertEqual(states['independence'], 'MET')
        self.assertEqual(states['both_sides'], 'MET')


class ConflictAndStandingTests(ChainTestCase):

    def test_a_regulatory_conflict_is_material(self):
        self._link(self._evidence('harvester.Evidence:9'), relationship='supports')
        self._link(self._evidence('harvester.Evidence:10',
                                  legal_status='final_regulatory_finding'),
                   relationship='conflicts')
        chain = self.chain()
        self.assertEqual(chain['conflict']['state'], 'MATERIAL_CONFLICT')
        self.assertEqual(chain['standing']['state'],
                         'FINAL_REGULATORY_OR_COURT_FINDING')

    def test_a_preliminary_finding_is_not_a_material_conflict(self):
        """A regulator's opening position is not its conclusion."""
        self._link(self._evidence('harvester.Evidence:11'), relationship='supports')
        self._link(self._evidence('harvester.Evidence:12',
                                  legal_status='preliminary_regulatory_finding'),
                   relationship='conflicts')
        chain = self.chain()
        self.assertEqual(chain['conflict']['state'], 'CONFLICT')
        self.assertEqual(chain['standing']['state'], 'PRELIMINARY_REGULATORY_FINDING')


class RemediationAndResidualConcernTests(ChainTestCase):

    def _material_conflict(self):
        self._link(self._evidence('harvester.Evidence:13'), relationship='supports')
        self._link(self._evidence('harvester.Evidence:14',
                                  legal_status='final_regulatory_finding'),
                   relationship='conflicts')

    def _step(self, verification):
        KPIRemediationStep.objects.create(
            assessment=self.assessment, position=1, kind='company_action',
            summary='Action taken', occurred_on=datetime.date(2026, 5, 1),
            verification=verification)

    def test_claimed_remediation_does_not_reduce_concern(self):
        """
        The organisation's own account of its remediation is a claim. Treating
        it as a resolution would let any concern be closed by asserting it was.
        """
        self._material_conflict()
        self._step('claimed')
        residual = self.chain()['residual_concern']
        self.assertEqual(residual['state'], 'REMEDIATION_CLAIMED_NOT_VERIFIED')
        self.assertIn('none of it was independently verified', residual['detail'])

    def test_independently_verified_remediation_reduces_concern(self):
        self._material_conflict()
        self._step('independently_verified')
        residual = self.chain()['residual_concern']
        self.assertEqual(residual['state'], 'REDUCED_BY_VERIFIED_REMEDIATION')
        self.assertIn('without erasing the original finding', residual['detail'])

    def test_remediation_never_removes_the_conflict(self):
        """History is preserved. Remediation changes standing, not the record."""
        self._material_conflict()
        before = self.chain()['conflict']['state']
        self._step('independently_verified')
        self.assertEqual(self.chain()['conflict']['state'], before)
        self.assertEqual(self.chain()['conflict']['state'], 'MATERIAL_CONFLICT')

    def test_an_unremediated_conflict_is_unmitigated(self):
        self._material_conflict()
        self.assertEqual(self.chain()['residual_concern']['state'], 'UNMITIGATED')


class DecisionImplicationTests(ChainTestCase):

    def test_nothing_established_supports_no_decision_either_way(self):
        implication = self.chain()['decision_implication']
        self.assertEqual(implication['state'], NOT_INVESTIGATED)
        self.assertIn("not a point in the organisation's favour", implication['detail'])

    def test_a_material_conflict_is_on_the_record(self):
        self._link(self._evidence('harvester.Evidence:15'), relationship='supports')
        self._link(self._evidence('harvester.Evidence:16',
                                  legal_status='court_finding'),
                   relationship='conflicts')
        self.assertEqual(self.chain()['decision_implication']['state'],
                         'MATERIAL_CONCERN_ON_RECORD')

    def test_support_is_bounded_by_what_was_looked_at(self):
        self._link(self._evidence('harvester.Evidence:17'))
        implication = self.chain()['decision_implication']
        self.assertEqual(implication['state'], 'SUPPORTED_ON_THE_EVIDENCE_SEEN')
        self.assertIn('bounds what was looked at', implication['detail'])

    def test_no_node_ever_recommends_an_action(self):
        """
        EcoIQ reports what can be concluded. A decision implication that told a
        reader to buy, sell or hold would be investment advice.
        """
        self._link(self._evidence('harvester.Evidence:18'))
        chain = self.chain()
        text = ' '.join(chain[node]['detail'].lower() for node in NODES)
        for word in ('you should', 'we recommend', 'buy', 'sell', 'divest',
                     'invest in'):
            self.assertNotIn(word, text, f'action recommended: {word!r}')
