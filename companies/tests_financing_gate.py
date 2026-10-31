"""
D5 — company-specific financial claims obey the same evidence gate.

An eligibility card is a STRONGER statement than the score it rests on:
"this organisation meets Green Bond use-of-proceeds criteria" is a claim about
capital access, made by name. If the score cannot be published, a claim built
on it cannot either.
"""
from django.test import TestCase

from companies import provenance as prov
from companies.eligibility import decide
from companies.evidence import PROVENANCE_MEASURED, PROVENANCE_UNKNOWN
from companies.scoring import recalculate_and_save
from companies.testing import populated
from companies.views import _get_financing_eligibility
from league.models import Company


def _profile(slug, score=78.0):
    company = Company.objects.create(name=slug, slug=slug, country='UK',
                                     ecoiq_score=score)
    return populated(company, ecoiq_total_score=score, pollution_level='low')


def _evidence(profile, count=16, origin=PROVENANCE_MEASURED):
    for key in sorted(prov.MATERIAL_METRIC_KEYS)[:count]:
        prov.record(profile, key, origin, written_by='t')
    recalculate_and_save(profile)
    profile.refresh_from_db()
    profile.ecoiq_total_score = 78.0
    profile.save()
    return profile


class FinancingClaimsFollowEvidence(TestCase):

    def test_a_legacy_company_with_a_stored_score_gets_no_cards(self):
        """
        The case the old guard missed. `s is None` was the only check, and a
        legacy company HAS a stored composite — so it collected positive
        financing claims while its score was being withheld.
        """
        profile = _evidence(_profile('fin-legacy'), origin=PROVENANCE_UNKNOWN)

        self.assertIsNotNone(profile.ecoiq_total_score)
        self.assertFalse(decide(profile).is_published)
        self.assertEqual(_get_financing_eligibility(profile), [])

    def test_a_partially_evidenced_company_gets_no_cards(self):
        profile = _evidence(_profile('fin-partial'), count=4)

        self.assertEqual(_get_financing_eligibility(profile), [])

    def test_a_company_with_no_evidence_gets_no_cards(self):
        self.assertEqual(_get_financing_eligibility(_profile('fin-none')), [])

    def test_a_fully_evidenced_company_does_get_cards(self):
        """
        The gate must not be a blanket refusal — a company that genuinely
        qualifies should see its eligibility.
        """
        profile = _evidence(_profile('fin-full'))

        self.assertTrue(decide(profile).is_published)
        self.assertTrue(_get_financing_eligibility(profile))

    def test_the_cards_are_still_indicative(self):
        profile = _evidence(_profile('fin-indicative'))

        for card in _get_financing_eligibility(profile):
            with self.subTest(card=card['type']):
                self.assertIn('indicative', card['detail'].lower())

    def test_no_profile_does_not_raise(self):
        profile = _profile('fin-null-score')
        profile.ecoiq_total_score = None
        profile.save()

        self.assertEqual(_get_financing_eligibility(profile), [])

    def test_containment_does_not_depend_on_the_caller(self):
        """
        The page-level gate happens to contain this today. Relying on that
        would make the containment a property of the caller rather than of the
        claim, and a second caller would not inherit it.
        """
        import inspect

        source = inspect.getsource(_get_financing_eligibility)

        self.assertIn('decide(profile).is_published', source)
