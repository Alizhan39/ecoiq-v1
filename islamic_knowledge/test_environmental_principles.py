"""Twenty stewardship lenses: provenance, scope, KPI crosswalk and access regressions.

All texts are draft EcoIQ operationalisations, not hadith authentication,
religious interpretation authority or outcomes of a mining assessment.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from gold_intelligence.models import (
    GoldProject, GeologicalEvidenceSource, MineKPIObservation, ProjectMembership,
)
from gold_intelligence.services.kpi_definitions import MINING_KPIS
from gold_intelligence.services.stewardship_lenses import (
    GOLD_KPI_PROXIES, build_stewardship_readiness,
)
from islamic_knowledge.catalog import QuranReference
from islamic_knowledge.contracts import assess_definition
from islamic_knowledge.environmental_principles import (
    BY_CONCEPT, STEWARDSHIP_LENSES, stewardship_drafts,
)
from islamic_knowledge.principles import DRAFT_PRINCIPLES


EXPECTED = (
    'mizan', 'khalifah', 'imarat_al_ard', 'islah', 'amanah',
    'fasad', 'israf', 'tabdhir', 'iqtisad', 'tayyib', 'hima',
    'harim', 'ihya_al_mawat', 'ghars_al_ashjar',
    'rifq_bil_hayawan', 'hifz_al_maa', 'la_darar_wa_la_dirar',
    'maslaha', 'dar_al_mafasid', 'sadaqa_jariya',
)


class StewardshipCatalogueTests(SimpleTestCase):
    def test_all_twenty_unique_concepts_are_present_in_requested_order(self):
        self.assertEqual(tuple(p.concept for p in STEWARDSHIP_LENSES), EXPECTED)
        self.assertEqual(set(BY_CONCEPT), set(EXPECTED))
        self.assertEqual(len(stewardship_drafts()), 20)
        self.assertEqual(len({definition.id for definition in stewardship_drafts()}), 20)

    def test_shared_principles_reuse_existing_knowledge_definitions(self):
        originals = {definition.concept: definition for definition in DRAFT_PRINCIPLES}
        for concept in ('mizan', 'khalifah', 'islah', 'amanah', 'fasad', 'israf'):
            self.assertIs(BY_CONCEPT[concept].draft, originals[concept])
        self.assertEqual(
            tuple(ref.locator for ref in BY_CONCEPT['khalifah'].draft.quran_references),
            ('2:30', '6:165'),
        )

    def test_every_draft_fails_closed_without_reviewed_sources(self):
        for definition in stewardship_drafts():
            with self.subTest(concept=definition.concept):
                gate = assess_definition(definition, {}, as_of=date(2026, 10, 20))
                self.assertFalse(gate.ready)
                self.assertIn('SCHOLAR_REVIEW_REQUIRED', gate.reasons)
                self.assertIn('MISSING_SOURCES', gate.reasons)

    def test_locators_are_valid_but_not_authenticated_quotations(self):
        for lens in STEWARDSHIP_LENSES:
            for locator in lens.quran_locators:
                self.assertIsInstance(QuranReference(*locator), QuranReference)
        self.assertEqual(BY_CONCEPT['mizan'].draft.quran_references[0].locator, '55:7-9')
        self.assertEqual(BY_CONCEPT['imarat_al_ard'].source_family, 'quran_concept')
        self.assertIn('толкование', BY_CONCEPT['imarat_al_ard'].context_note)
        self.assertEqual(BY_CONCEPT['hima'].source_family, 'hadith_practice')
        self.assertEqual(BY_CONCEPT['harim'].source_family, 'fiqh_principle')
        self.assertFalse(BY_CONCEPT['harim'].quran_locators)
        self.assertEqual(BY_CONCEPT['maslaha'].source_family, 'fiqh_principle')
        self.assertEqual(BY_CONCEPT['la_darar_wa_la_dirar'].source_family, 'hadith_practice')
        self.assertIn('daif', BY_CONCEPT['la_darar_wa_la_dirar'].other_sources[0].caution)

    def test_links_are_registered_partial_indicators_not_moral_scores(self):
        self.assertEqual(set(GOLD_KPI_PROXIES), set(EXPECTED))
        for keys in GOLD_KPI_PROXIES.values():
            self.assertTrue(set(keys) <= set(MINING_KPIS))
        self.assertEqual(GOLD_KPI_PROXIES['hima'], ())
        self.assertEqual(GOLD_KPI_PROXIES['sadaqa_jariya'], ())
        self.assertIn('freshwater_m3_per_t', GOLD_KPI_PROXIES['hifz_al_maa'])


class StewardshipViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user('gold-stewardship-owner')
        cls.stranger = get_user_model().objects.create_user('gold-stewardship-stranger')
        cls.project = GoldProject.objects.create(
            name='Private gold project', slug='private-20-lens-gold', is_demo=True)
        ProjectMembership.objects.create(
            project=cls.project, user=cls.owner, role=ProjectMembership.Role.VIEWER)
        cls.source = GeologicalEvidenceSource.objects.create(
            project=cls.project, source_id='S-1', title='Synthetic example',
            issuer='Fixture', kind='operations', is_synthetic=True)
        cls.kpi = MineKPIObservation.objects.create(
            project=cls.project, source=cls.source, metric_key='freshwater_m3_per_t',
            period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
            numerator=Decimal('250'), denominator=Decimal('1000'),
        )

    def test_private_stewardship_view_renders_twenty_no_ethical_verdicts(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('gold_intelligence:stewardship',
                                           args=[self.project.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stewardship']['count'], 20)
        self.assertContains(response, '20 principles')
        self.assertContains(response, 'Mizan')
        self.assertContains(response, 'La Darar')
        self.assertContains(response, 'SCHOLAR_REVIEW_PENDING', count=20)
        self.assertContains(response, 'NOT_ASSESSED', count=20)
        self.assertContains(response, 'Internal review is not external certification', count=0)
        readiness = response.context['stewardship']
        by_key = {lens['concept']: lens for lens in readiness['lenses']}
        self.assertEqual(by_key['hifz_al_maa']['calculable_count'], 1)
        self.assertEqual(by_key['hifz_al_maa']['internally_reviewed_count'], 0)
        self.assertEqual(by_key['hima']['observation_count'], 0)
        self.assertEqual(by_key['sadaqa_jariya']['ethical_status'], 'NOT_ASSESSED')

    def test_private_stewardship_url_and_investor_link_do_not_leak(self):
        path = reverse('gold_intelligence:stewardship', args=[self.project.slug])
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.get(
            reverse('gold_intelligence:investor_view', args=[self.project.slug])
        ).status_code, 404)
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(
            reverse('gold_intelligence:investor_view', args=[self.project.slug])
        ), path)

    def test_no_moral_grade_even_when_measured_kpi_is_present(self):
        self.client.force_login(self.owner)
        readiness = build_stewardship_readiness(self.project)
        self.assertEqual(readiness['status'], 'EVIDENCE_AND_SCHOLAR_REVIEW_REQUIRED')
        self.assertTrue(all(x['ethical_status'] == 'NOT_ASSESSED' for x in readiness['lenses']))
        self.assertTrue(all(x['scholarly_status'] == 'SCHOLAR_REVIEW_PENDING' for x in readiness['lenses']))
