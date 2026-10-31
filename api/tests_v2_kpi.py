"""
Tests for the KPI investigation endpoint.

The properties under test are the ones that make the page trustworthy rather
than merely functional: that unconfirmed evidence cannot move a verdict, that a
preliminary finding is never presented as a concluded one, that absence of
evidence is distinguishable from negative evidence, and that the sacred-source
layer never leaves the server.
"""
import datetime

from django.test import TestCase

from companies.models import CompanyProfile
from company_intelligence.models import (
    CompanyKPIAssessment, CompanyKPIEvidenceLink, KPIRemediationStep,
)
from evidence_memory.models import EvidenceMemory
from league.models import Company

URL = '/api/v2/companies/{slug}/kpis/{kpi}/'


class KpiInvestigationTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Testco', slug='testco')
        self.profile = CompanyProfile.objects.create(company=self.company)
        self.assessment = CompanyKPIAssessment.objects.create(
            company=self.profile, kpi_id=114, is_demo=True)

    def _evidence(self, ref, *, legal_status='company_policy', authority='Testco',
                  tier='human_reviewed'):
        return EvidenceMemory.objects.create(
            text_chunk=f'Body of {ref}', source_reference=ref, source_url='https://example.org/x',
            source_type='manual', source_authority=authority, legal_status=legal_status,
            company=self.profile, date_collected=datetime.date(2026, 1, 1),
            verification_status='verified', review_tier=tier, is_demo=True,
        )

    def _link(self, evidence, relationship, review_state='confirmed'):
        return CompanyKPIEvidenceLink.objects.create(
            assessment=self.assessment, evidence=evidence,
            relationship=relationship, review_state=review_state)

    def get(self, slug='testco', kpi=114):
        return self.client.get(URL.format(slug=slug, kpi=kpi))


class RouteTests(KpiInvestigationTestCase):

    def test_renders_for_a_known_company_and_principle(self):
        self.assertEqual(self.get().status_code, 200)

    def test_unknown_principle_is_404_not_an_empty_assessment(self):
        """115 does not exist. Inventing one would fabricate a framework entry."""
        self.assertEqual(self.get(kpi=115).status_code, 404)

    def test_unknown_company_is_404(self):
        self.assertEqual(self.get(slug='nope').status_code, 404)

    def test_principle_title_comes_from_the_taxonomy(self):
        body = self.get().json()
        self.assertEqual(body['stewardship_principle']['kpi_id'], 114)
        self.assertEqual(body['stewardship_principle']['title'],
                         'Consumer Protection & Anti-Manipulation')


class SacredSourceContainmentTests(KpiInvestigationTestCase):
    """
    docs/governance-principles-surah-map.md: the sacred-source layer is INTERNAL.
    Enforced at the serializer because a template that forgets is a leak.
    """

    def test_payload_contains_no_sacred_source_material(self):
        raw = self.get().content.decode()
        for term in ('surah', 'Surah', 'An-Nas', 'an-nas', 'ayah', 'Ayah',
                     'Qur', 'Arabic'):
            self.assertNotIn(term, raw, f'sacred-source term leaked: {term!r}')

    def test_no_sacred_source_key_is_emitted(self):
        principle = self.get().json()['stewardship_principle']
        for key in ('surah_number', 'surah_name', 'ayah_range',
                    'approved_translation', 'translation_source'):
            self.assertNotIn(key, principle)


class VerdictDerivationTests(KpiInvestigationTestCase):

    def test_no_evidence_is_insufficient_not_zero(self):
        body = self.get().json()
        self.assertEqual(body['assessment']['verdict'], 'insufficient_evidence')
        self.assertEqual(body['assessment']['confidence'], 'INSUFFICIENT_EVIDENCE')

    def test_supports_only_reads_as_support(self):
        self._link(self._evidence('A'), 'supports')
        self.assertIn(self.get().json()['assessment']['verdict'],
                      ('support', 'strong_support'))

    def test_conflicts_only_reads_as_conflict(self):
        self._link(self._evidence('B', legal_status='final_regulatory_finding'), 'conflicts')
        self.assertEqual(self.get().json()['assessment']['verdict'], 'conflict')

    def test_both_directions_produce_mixed(self):
        self._link(self._evidence('A'), 'supports')
        self._link(self._evidence('B', legal_status='third_party_analysis'), 'conflicts')
        self.assertEqual(self.get().json()['assessment']['verdict'], 'mixed')

    def test_a_final_finding_makes_a_mixed_picture_material(self):
        """
        The distinction §16 asks for. A conflict resting on a regulator's
        conclusion is not the same as one resting on commentary, and a reader
        who cannot tell them apart has been told very little.
        """
        self._link(self._evidence('A'), 'supports')
        self._link(self._evidence('B', legal_status='final_regulatory_finding'), 'conflicts')
        body = self.get().json()
        self.assertEqual(body['assessment']['verdict'], 'mixed_material_conflict')
        self.assertEqual(body['assessment']['verdict_label'], 'MIXED — MATERIAL CONFLICT')

    def test_a_preliminary_finding_does_not_make_a_conflict_material(self):
        """A regulator opening a case is not a regulator concluding one."""
        self._link(self._evidence('A'), 'supports')
        self._link(self._evidence('B', legal_status='preliminary_regulatory_finding'),
                   'conflicts')
        self.assertEqual(self.get().json()['assessment']['verdict'], 'mixed')


class ReviewStateTests(KpiInvestigationTestCase):

    def test_unconfirmed_evidence_cannot_move_the_verdict(self):
        self._link(self._evidence('A'), 'supports')
        self._link(self._evidence('B', legal_status='final_regulatory_finding'),
                   'conflicts', review_state='proposed')
        body = self.get().json()
        self.assertIn(body['assessment']['verdict'], ('support', 'strong_support'))
        self.assertEqual(body['counts']['conflicts'], 0)

    def test_rejected_evidence_is_excluded_from_the_assessment(self):
        self._link(self._evidence('A'), 'supports')
        self._link(self._evidence('C'), 'supports', review_state='rejected')
        body = self.get().json()
        self.assertEqual(body['counts']['confirmed'], 1)
        self.assertEqual(body['counts']['excluded_from_assessment'], 1)

    def test_excluded_evidence_is_still_returned_and_flagged(self):
        """
        Hiding it would overstate how well evidenced the verdict is; counting it
        would let unreviewed material decide. It is shown, and marked.
        """
        self._link(self._evidence('C'), 'supports', review_state='proposed')
        item = self.get().json()['evidence'][0]
        self.assertFalse(item['counts_toward_assessment'])
        self.assertEqual(item['review_state'], 'proposed')


class ConfidenceTests(KpiInvestigationTestCase):

    def test_confidence_is_categorical_never_a_number(self):
        self._link(self._evidence('A'), 'supports')
        self.assertIn(self.get().json()['assessment']['confidence'],
                      {'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH', 'INSUFFICIENT_EVIDENCE'})

    def test_confidence_is_explained(self):
        self._link(self._evidence('B', legal_status='final_regulatory_finding'), 'conflicts')
        self.assertTrue(self.get().json()['assessment']['confidence_reasons'])

    def test_a_regulatory_finding_raises_confidence_above_policy_alone(self):
        self._link(self._evidence('A'), 'supports')
        weak = self.get().json()['assessment']['confidence']
        self._link(self._evidence('B', legal_status='final_regulatory_finding',
                                  authority='Regulator', tier='independently_verified'),
                   'conflicts')
        strong = self.get().json()['assessment']['confidence']
        order = ['INSUFFICIENT_EVIDENCE', 'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH']
        self.assertGreater(order.index(strong), order.index(weak))


class RemediationTests(KpiInvestigationTestCase):

    def test_remediation_is_returned_in_chain_order(self):
        for i, kind in enumerate(
                ['finding', 'company_response', 'product_or_policy_change'], start=1):
            KPIRemediationStep.objects.create(
                assessment=self.assessment, position=i, kind=kind,
                summary=f'Step {i}', is_demo=True)
        kinds = [s['kind'] for s in self.get().json()['remediation']]
        self.assertEqual(kinds, ['finding', 'company_response', 'product_or_policy_change'])

    def test_remediation_does_not_offset_a_conflict(self):
        """
        The reason remediation is NOT a relationship value. If it counted, an
        organisation could remediate a problem and watch the finding vanish
        from its own assessment.
        """
        self._link(self._evidence('B', legal_status='final_regulatory_finding'), 'conflicts')
        KPIRemediationStep.objects.create(
            assessment=self.assessment, position=1, kind='product_or_policy_change',
            summary='Fixed it', verification='independently_confirmed', is_demo=True)
        body = self.get().json()
        self.assertEqual(body['assessment']['verdict'], 'conflict')
        self.assertEqual(body['counts']['remediation_steps'], 1)


class DemoDisclosureTests(KpiInvestigationTestCase):

    def test_demo_corpus_is_declared(self):
        self._link(self._evidence('A'), 'supports')
        body = self.get().json()
        self.assertTrue(body['assessment']['is_demo'])
        self.assertTrue(body['evidence'][0]['is_demo'])
