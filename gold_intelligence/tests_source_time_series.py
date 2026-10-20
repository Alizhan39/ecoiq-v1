"""Real public quarterly reporting and market-price time-series validation.

These fixtures test reported observations and rights gates, NOT actual
operator-scoped processing permission, model training or mine optimisation.
"""
from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from gold_intelligence.services.source_time_series import (
    available_time_series, series_scenario_eligibility, source_rights_summary,
    time_series_card, validate_time_series,
)
from gold_intelligence.services.source_time_series import _snapshot


class GoldTimeSeriesValidationTests(SimpleTestCase):
    def setUp(self):
        self.manifest, self.rights = deepcopy(_snapshot())
        self.series = self.manifest['series'][0]

    def test_data_are_real_limited_disclosures_and_licensed_market_context(self):
        validate_time_series(self.manifest, self.rights)
        self.assertEqual(len(self.manifest['series']), 4)
        self.assertEqual([len(s['observations']) for s in self.manifest['series']],
                         [6, 6, 6, 9])
        self.assertEqual(self.series['observations'][0]['period'], '2025-Q1')
        self.assertEqual(self.series['observations'][0]['value'], 97)
        self.assertEqual(self.series['observations'][-1]['value'], 100)
        self.assertEqual(self.manifest['series'][1]['observations'][-1]['value'], 41)
        self.assertEqual(self.manifest['series'][2]['observations'][0]['value'], 37)
        self.assertEqual(self.manifest['series'][3]['observations'][-1]['value'], 4319)

    def test_operator_reuse_permissions_are_not_invented(self):
        rights = source_rights_summary()
        operator = rights['sources']['solidcore_quarterly']
        self.assertFalse(operator['commercial_redistribution_allowed'])
        self.assertFalse(operator['automated_bulk_ingestion_allowed'])
        self.assertEqual(operator['rights_status'], 'PERMISSION_NOT_CONFIRMED')
        self.assertEqual(series_scenario_eligibility(self.series['id']),
                         'OPERATOR_PERMISSION_PENDING')
        self.assertEqual(series_scenario_eligibility(
            'worldbank-gold-monthly-market-price'),
            'ORIGINAL_PRICE_WORKBOOK_RECONCILIATION_REQUIRED')
        self.assertTrue(rights['sources']['world_bank_pink_sheet']['commercial_redistribution_allowed'])

    def test_separate_mine_output_and_payable_ge_without_false_loss_arithmetic(self):
        raw = time_series_card('solidcore-kyzyl-gold-in-concentrate-quarterly')
        final = time_series_card('solidcore-kyzyl-payable-ge-quarterly')
        self.assertEqual(raw['series']['unit'], 'thousand_gold_ounces_in_concentrate')
        self.assertEqual(final['series']['unit'], 'thousand_gold_equivalent_ounces')
        self.assertEqual(final['series']['production_stage'], 'PAYABLE_GE')
        self.assertFalse(final['optimisation_outcome_claim_allowed'])
        self.assertFalse(final['commercial_bulk_redistribution_enabled'])
        self.assertFalse(final['automated_operational_ingestion_enabled'])
        self.assertNotIn('loss_ounces', final)

    def test_rejects_mixed_stage_units(self):
        self.series['unit'] = 'thousand_gold_equivalent_ounces'
        with self.assertRaisesRegex(ValueError, 'Stage/metric/unit'):
            validate_time_series(self.manifest, self.rights)

    def test_rejects_duplicate_future_out_of_order_and_invalid_period(self):
        self.series['observations'].append(deepcopy(self.series['observations'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate observation'):
            validate_time_series(self.manifest, self.rights)
        self.series['observations'].pop()
        self.series['observations'][0]['period_end'] = '2025-04-02'
        with self.assertRaisesRegex(ValueError, 'Quarter end'):
            validate_time_series(self.manifest, self.rights)

    def test_rejects_value_not_from_original_release(self):
        self.series['observations'][0]['source_url'] = 'https://example.com/made-up'
        with self.assertRaisesRegex(ValueError, 'original release'):
            validate_time_series(self.manifest, self.rights)

    def test_rejects_commercial_permissions_silently_added_to_operator(self):
        self.rights['sources']['solidcore_quarterly']['rights_status'] = 'CC_BY_4_0'
        with self.assertRaisesRegex(ValueError, 'operator'):
            validate_time_series(self.manifest, self.rights)

    def test_rejects_fake_wb_primary_verification(self):
        self.manifest['series'][-1]['observations'][0]['verified_against_original_workbook'] = True
        with self.assertRaisesRegex(ValueError, 'workbook'):
            validate_time_series(self.manifest, self.rights)

    def test_rejects_market_price_bound_to_a_mine(self):
        self.manifest['series'][-1]['asset_id'] = 'solidcore-kyzyl-bakyrchik'
        with self.assertRaisesRegex(ValueError, 'not observations'):
            validate_time_series(self.manifest, self.rights)

    def test_data_returns_are_isolated_defensive_copies(self):
        a = available_time_series()
        self.assertEqual(len(a), 4)
        a[0]['unit'] = 'changed'
        self.assertNotEqual(available_time_series()[0]['unit'], 'changed')
        self.assertIsNone(time_series_card('private-mine-id'))


class GoldTimeSeriesViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user('series-benchmark-reader')

    def test_login_required_and_no_private_project_lookup(self):
        path = reverse('gold_intelligence:public_time_series')
        self.assertEqual(self.client.get(path).status_code, 302)
        self.client.force_login(self.user)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Source rights')
        self.assertEqual(len(response.context['series_list']), 4)

        response = self.client.get(path, {'series': '../../secret'})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['card'])

    def test_real_reported_periods_display_with_rights_notice(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('gold_intelligence:public_time_series'),
            {'series': 'solidcore-kyzyl-gold-in-concentrate-quarterly'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PERMISSION_NOT_CONFIRMED')
        self.assertContains(response, '2025-Q1')
        self.assertContains(response, '2026-Q2')
        self.assertContains(response, 'NOT LIVE MINE TELEMETRY')

    def test_gold_market_prices_not_mislabeled_as_mine_production(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('gold_intelligence:public_time_series'),
            {'series': 'worldbank-gold-monthly-market-price'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'MARKET_PRICE_NOT_PRODUCTION')
        self.assertContains(response, 'CC_BY_4_0')
