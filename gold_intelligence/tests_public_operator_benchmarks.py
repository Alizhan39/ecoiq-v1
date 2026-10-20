"""Independent public-facts seed: scope safety, provenance and access."""
from copy import deepcopy
from math import isclose
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from gold_intelligence.services.public_operator_benchmarks import (
    _validate, mine_evidence_card, public_gold_inventory,
    recovery_uplift_sensitivity,
)


class PublicGoldBenchmarkContractTests(SimpleTestCase):
    def setUp(self):
        self.snapshot = public_gold_inventory()

    def test_documented_non_exhaustive_inventory_has_citations(self):
        d = self.snapshot
        self.assertEqual(d['schema_version'], '1.0')
        self.assertFalse(d['claim_all_active_mines'])
        self.assertEqual(d['coverage'], 'NON_EXHAUSTIVE_PUBLIC_SEED')
        self.assertEqual(len(d['assets']), 15)
        self.assertEqual(len(d['observations']), 24)
        self.assertEqual(len(d['operator_observations']), 7)
        self.assertEqual(len(d['optimisation_hypotheses']), 8)
        self.assertEqual(len(d['sources']), 13)
        self.assertTrue(all(row['source_refs'] for row in d['assets']))
        self.assertTrue(all(row['status'] == 'reported_operating_in_2025' for row in d['assets']))
        self.assertTrue(all(row['last_operation_evidence_year'] == 2025 for row in d['assets']))

    def test_source_coverage_must_not_be_declared_complete(self):
        d = deepcopy(self.snapshot)
        d['claim_all_active_mines'] = True
        with self.assertRaisesRegex(ValueError, 'non-exhaustive'):
            _validate(d)

    def test_invalid_or_duplicate_mine_fails_fast(self):
        d = deepcopy(self.snapshot)
        d['assets'].append(deepcopy(d['assets'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            _validate(d)

    def test_wrong_units_or_missing_source_block_research_data(self):
        for changes in (
            {'unit': 'tonnes_Au'}, {'source_ref': 'made_up'},
            {'value': -1}, {'value': float('nan')},
        ):
            with self.subTest(changes=changes):
                d = deepcopy(self.snapshot)
                d['observations'][0].update(changes)
                with self.assertRaises(ValueError):
                    _validate(d)

    def test_recovery_percent_over_100_is_rejected(self):
        d = deepcopy(self.snapshot)
        record = next(o for o in d['observations'] if o['metric'] == 'gold_recovery')
        record['value'] = 101
        with self.assertRaisesRegex(ValueError, 'exceed 100'):
            _validate(d)

    def test_operator_group_aisc_is_not_mislabelled_as_mine_data(self):
        card = mine_evidence_card('solidcore-kyzyl-bakyrchik')
        self.assertFalse(card['is_verified_operational_kpi'])
        mine_metrics = {m['metric'] for m in card['observations']}
        self.assertNotIn('AISC', mine_metrics)
        self.assertIn('flotation_gold_recovery', mine_metrics)
        company_aisc = [x for x in self.snapshot['operator_observations']
                        if x['operator'] == 'Solidcore' and x['metric'] == 'AISC']
        self.assertEqual({x['scope'] for x in company_aisc}, {'company'})
        self.assertEqual({x['value'] for x in company_aisc}, {1532, 1912})

    def test_company_GOLD_and_GE_ounce_types_are_distinct(self):
        output = [o for o in self.snapshot['operator_observations']
                  if o['operator'] == 'Solidcore' and o['metric'] == 'payable_GE_production']
        self.assertEqual(output[0]['unit'], 'thousand_GE_ounces')
        self.assertEqual(output[0]['value'], 395)
        self.assertNotEqual(output[0]['unit'], 'ounces_Au')

    def test_early_mining_without_own_plant_output_is_not_fake_zero(self):
        asset = mine_evidence_card('altynalmas-baktai')
        self.assertEqual(asset['observations'][0]['metric'], 'ore_mined')
        self.assertTrue(all(x['metric'] != 'gold_production' for x in asset['observations']))
        self.assertIsNone(mine_evidence_card('not-a-real-mine'))

    def test_research_hypotheses_never_upgrade_to_audited(self):
        for x in self.snapshot['optimisation_hypotheses']:
            self.assertEqual(x['status'], 'PROPOSAL_NOT_AUDITED')
            self.assertIn('test', x)
            self.assertTrue(x['source_refs'])

    def test_recovery_sensitivity_is_only_arithmetic(self):
        # Kyzyl 2025 2.47 Mt × 4.9 g/t × 1 absolute percentage point
        result = recovery_uplift_sensitivity(2_470_000, 4.9, 1)
        self.assertTrue(result['available'])
        self.assertEqual(result['status'], 'SCENARIO_ONLY_NOT_VALIDATED')
        self.assertEqual(result['additional_recovered_gold_grams'], 121030)
        self.assertTrue(isclose(result['additional_recovered_gold_troy_ounces'],
                                3891.24, abs_tol=1.0))
        self.assertNotIn('revenue_usd', result)

    def test_sensitivity_rejects_nan_bool_and_negative(self):
        for values in ((float('nan'), 4.9, 1), (True, 4.9, 1),
                       (200, -1, 1), (200, 2.0, 101)):
            with self.subTest(inputs=values):
                self.assertFalse(recovery_uplift_sensitivity(*values)['available'])

    def test_catalogue_return_is_independently_mutable(self):
        snapshot = public_gold_inventory()
        snapshot['assets'][0]['name'] = 'tampered'
        self.assertNotEqual(public_gold_inventory()['assets'][0]['name'], 'tampered')

    def test_source_validator_does_not_accept_non_https(self):
        d = deepcopy(self.snapshot)
        first = next(iter(d['sources']))
        d['sources'][first]['url'] = 'http://untrusted.example/doc'
        with self.assertRaisesRegex(ValueError, 'HTTPS'):
            _validate(d)


class PublicGoldBenchmarkViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user('public-benchmark-user')

    def test_login_required_for_public_benchmarks_explorer(self):
        path = reverse('gold_intelligence:public_benchmarks')
        response = self.client.get(path)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_logged_in_user_can_read_only_static_non_private_research(self):
        self.client.force_login(self.user)
        path = reverse('gold_intelligence:public_benchmarks')
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NON-EXHAUSTIVE PUBLIC RESEARCH')
        self.assertContains(response, 'Kyzyl / Bakyrchik')
        self.assertContains(response, 'Raygorodok')
        self.assertEqual(len(response.context['catalogue']['assets']), 15)

    def test_filtered_mine_has_individual_sources_and_hypotheses(self):
        self.client.force_login(self.user)
        path = reverse('gold_intelligence:public_benchmarks')
        response = self.client.get(path, {'asset': 'solidcore-kyzyl-bakyrchik'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['card']['asset']['id'],
                         'solidcore-kyzyl-bakyrchik')
        self.assertContains(response, 'Kyzyl')
        self.assertContains(response, 'PROPOSAL_NOT_AUDITED')
        self.assertContains(response, 'External concentrate oxidation')

    def test_invalid_query_cannot_lookup_private_project(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('gold_intelligence:public_benchmarks'),
                                   {'asset': '../../private'})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['card'])
