import re
from unittest.mock import patch

import pandas as pd
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from countries.models import CountryProfile
from geo_intelligence.models import GeoAsset, GeoRiskZone, InvestmentGeoOpportunity
from geo_intelligence.services import spatial, weather

TEMPLATE_LEAK_RE = re.compile(r'\{%|\{\{')

ALMATY = weather.KAZAKHSTAN_CITIES['Almaty']
ASTANA = weather.KAZAKHSTAN_CITIES['Astana']


def _fake_climate_summary(**kwargs):
    return {
        'available': True, 'reason': '', 'source': 'Meteostat',
        'avg_temp_current_year': 13.4, 'avg_temp_previous_year': 11.9,
        'precipitation_current_year_mm': 557.0, 'precipitation_previous_year_mm': 904.0,
        'extreme_heat_days_current_year': 19, 'extreme_heat_days_previous_year': 17,
        'years': [2024, 2025], 'fetched_at': '2026-01-01T00:00:00+00:00',
    }


class SpatialServiceTests(TestCase):
    def test_distance_km_matches_known_real_world_distance(self):
        # Almaty -> Astana, real geodesic distance is ~965km.
        d = spatial.distance_km(ALMATY['latitude'], ALMATY['longitude'], ASTANA['latitude'], ASTANA['longitude'])
        self.assertAlmostEqual(d, 965, delta=30)

    def test_nearest_row_picks_the_closer_city(self):
        candidates = [
            {'name': 'Astana', 'latitude': ASTANA['latitude'], 'longitude': ASTANA['longitude']},
            {'name': 'Shymkent', **{k: v for k, v in weather.KAZAKHSTAN_CITIES['Shymkent'].items()}},
        ]
        nearest, dist = spatial.nearest_row(ALMATY['latitude'], ALMATY['longitude'], candidates)
        self.assertEqual(nearest['name'], 'Shymkent')
        self.assertLess(dist, 965)  # closer than Astana

    def test_nearest_row_empty_candidates_returns_none(self):
        nearest, dist = spatial.nearest_row(ALMATY['latitude'], ALMATY['longitude'], [])
        self.assertIsNone(nearest)
        self.assertIsNone(dist)

    def test_assets_within_risk_zone_uses_real_spatial_buffer(self):
        zone = {'latitude': ALMATY['latitude'], 'longitude': ALMATY['longitude'], 'radius_km': 50}
        assets = [
            {'name': 'Inside', 'latitude': ALMATY['latitude'] + 0.05, 'longitude': ALMATY['longitude'] + 0.05},
            {'name': 'Far away', 'latitude': ASTANA['latitude'], 'longitude': ASTANA['longitude']},
        ]
        inside = spatial.assets_within_risk_zone(zone, assets)
        self.assertEqual([a['name'] for a in inside], ['Inside'])

    def test_cluster_bounding_box_covers_all_points(self):
        rows = [
            {'latitude': ALMATY['latitude'], 'longitude': ALMATY['longitude']},
            {'latitude': ASTANA['latitude'], 'longitude': ASTANA['longitude']},
        ]
        bbox = spatial.cluster_bounding_box(rows)
        self.assertEqual(bbox['min_lat'], ALMATY['latitude'])   # Almaty (43.2°N) is further south than Astana (51.2°N)
        self.assertEqual(bbox['max_lat'], ASTANA['latitude'])
        self.assertEqual(bbox['min_lon'], ASTANA['longitude'])  # Astana (71.4°E) is further west than Almaty (76.9°E)
        self.assertEqual(bbox['max_lon'], ALMATY['longitude'])

    def test_cluster_bounding_box_empty_returns_none(self):
        self.assertIsNone(spatial.cluster_bounding_box([]))


class WeatherServiceTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_climate_summary_computes_year_over_year_stats_from_mocked_data(self):
        dates = pd.date_range('2024-01-01', '2025-12-31', freq='D')
        df = pd.DataFrame({'tavg': 15.0, 'tmax': 20.0, 'prcp': 1.0}, index=dates)
        # Make 2025 have more extreme-heat days than 2024.
        df.loc[df.index.year == 2025, 'tmax'] = 36.0

        class _FakeDaily:
            def __init__(self, *a, **kw):
                pass

            def fetch(self):
                return df

        with patch('meteostat.Daily', _FakeDaily), patch('meteostat.Point', lambda *a, **kw: None):
            with patch('django.utils.timezone.now') as mock_now:
                import datetime
                # December: the service treats the current calendar year as "complete"
                # only from December onward — otherwise it reports the prior two years,
                # since a still-in-progress year can't be fairly compared year-over-year.
                mock_now.return_value = datetime.datetime(2025, 12, 15, tzinfo=datetime.timezone.utc)
                result = weather.get_city_climate_summary('Almaty', ALMATY['latitude'], ALMATY['longitude'], 785)

        self.assertTrue(result['available'])
        self.assertEqual(result['extreme_heat_days_current_year'], 365)
        self.assertEqual(result['extreme_heat_days_previous_year'], 0)

    def test_climate_summary_degrades_gracefully_on_network_failure(self):
        with patch('meteostat.Point', side_effect=RuntimeError('no network')):
            result = weather.get_city_climate_summary('Nowhere', 0.0, 0.0, 0)
        self.assertFalse(result['available'])
        self.assertIn('Weather service temporarily unavailable', result['reason'])

    def test_climate_exposure_score_is_none_when_data_unavailable(self):
        unavailable = weather._empty_result('no data')
        self.assertIsNone(weather.climate_exposure_score(unavailable))

    def test_climate_exposure_score_is_derived_not_fabricated(self):
        summary = _fake_climate_summary()
        score = weather.climate_exposure_score(summary)
        self.assertIsNotNone(score)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


class GeoIntelligenceModelTests(TestCase):
    def test_geo_asset_str_and_defaults(self):
        asset = GeoAsset.objects.create(name='Test Asset', latitude=1.0, longitude=2.0)
        self.assertEqual(str(asset), 'Test Asset')
        self.assertTrue(asset.is_demo)  # honesty default — never assume real unless told
        self.assertIsNone(asset.climate_exposure_score)  # never fabricated

    def test_geo_risk_zone_str(self):
        zone = GeoRiskZone.objects.create(name='Test Zone', risk_type='extreme_heat', latitude=1.0, longitude=2.0)
        self.assertIn('Test Zone', str(zone))
        self.assertIn('Extreme Heat', str(zone))

    def test_investment_opportunity_str(self):
        opp = InvestmentGeoOpportunity.objects.create(title='Test Opportunity', latitude=1.0, longitude=2.0)
        self.assertEqual(str(opp), 'Test Opportunity')


class SeedCommandTests(TestCase):
    def test_seed_is_idempotent_and_uses_real_tour_figures(self):
        call_command('seed_khalifa_stewardship_demo')
        with patch('geo_intelligence.services.weather.get_city_climate_summary', return_value=_fake_climate_summary()):
            call_command('seed_geo_intelligence_demo')
            count_after_first = GeoAsset.objects.count()
            call_command('seed_geo_intelligence_demo')
        self.assertEqual(GeoAsset.objects.count(), count_after_first)

        opportunity = InvestmentGeoOpportunity.objects.filter(workbench_case_slug='kazakhstan-clean-heat').first()
        self.assertIsNotNone(opportunity)
        self.assertIn('700', opportunity.estimated_impact)  # real estimated_benefit from the tour's intervention
        self.assertIn('1,400', opportunity.estimated_impact)  # real capex_estimate

    def test_cities_are_marked_real_not_demo(self):
        call_command('seed_khalifa_stewardship_demo')
        with patch('geo_intelligence.services.weather.get_city_climate_summary', return_value=_fake_climate_summary()):
            call_command('seed_geo_intelligence_demo')
        almaty = GeoAsset.objects.get(name='Almaty')
        self.assertFalse(almaty.is_demo)

    def test_seed_completes_even_if_weather_fetch_fails(self):
        call_command('seed_khalifa_stewardship_demo')
        with patch('geo_intelligence.services.weather.get_city_climate_summary', return_value=weather._empty_result('no network')):
            call_command('seed_geo_intelligence_demo')  # must not raise
        self.assertEqual(GeoRiskZone.objects.count(), 0)  # honestly skipped, not fabricated


class CommandCentreViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_khalifa_stewardship_demo')

    def setUp(self):
        cache.clear()
        patcher = patch('geo_intelligence.services.weather.get_city_climate_summary', return_value=_fake_climate_summary())
        self.addCleanup(patcher.stop)
        patcher.start()
        call_command('seed_geo_intelligence_demo')

    def test_command_centre_loads_with_map_and_no_template_leak(self):
        resp = self.client.get(reverse('geo_intelligence:command_centre'))
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertFalse(TEMPLATE_LEAK_RE.search(body))
        self.assertIn('<iframe', body)
        self.assertIn('ECOIQ GEO INTELLIGENCE', body)

    def test_analyse_with_ai_links_to_real_workbench_case(self):
        resp = self.client.get(reverse('geo_intelligence:command_centre'))
        body = resp.content.decode()
        self.assertIn('/ai-agents/workbench/?case=kazakhstan-clean-heat&agent=capital-allocation-agent', body)

    def test_demo_data_is_clearly_labelled(self):
        resp = self.client.get(reverse('geo_intelligence:command_centre'))
        self.assertContains(resp, 'Demo Data')

    def test_layer_filter_hides_other_layers(self):
        resp = self.client.get(reverse('geo_intelligence:command_centre'), {'layer': 'investment'})
        body = resp.content.decode()
        self.assertIn('Investment Opportunities (1)', body)
        self.assertNotIn('Climate Risk Zones (1)', body)

    def test_search_query_filters_results(self):
        resp_match = self.client.get(reverse('geo_intelligence:command_centre'), {'q': 'Almaty'})
        resp_no_match = self.client.get(reverse('geo_intelligence:command_centre'), {'q': 'zzz_no_such_place'})
        self.assertIn('Companies &amp; Assets', resp_match.content.decode())
        self.assertIn('No results for the current filters', resp_no_match.content.decode())

    def test_climate_trend_section_shows_real_data_not_fabricated(self):
        resp = self.client.get(reverse('geo_intelligence:command_centre'))
        body = resp.content.decode()
        self.assertIn('13.4', body)
        self.assertIn('Meteostat', body)

    def test_climate_unavailable_degrades_honestly_without_crashing(self):
        with patch('geo_intelligence.services.weather.get_city_climate_summary', return_value=weather._empty_result('no network')):
            resp = self.client.get(reverse('geo_intelligence:command_centre'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Climate data temporarily unavailable')

    def test_never_fabricates_climate_exposure_score(self):
        GeoAsset.objects.create(name='Unmeasured Asset', latitude=1.0, longitude=2.0)
        resp = self.client.get(reverse('geo_intelligence:command_centre'))
        self.assertContains(resp, 'not yet measured')

    def test_next_actions_link_to_workbench_and_stewardship_tour(self):
        resp = self.client.get(reverse('geo_intelligence:command_centre'))
        body = resp.content.decode()
        self.assertIn(reverse('ai_agent_workbench:directory'), body)
        self.assertIn(
            reverse('khalifa_stewardship_tour_operating_system:tour_detail', args=['kazakhstan-clean-heat']), body,
        )


class NavigationIntegrationTests(TestCase):
    """Geo Intelligence must be reachable from anywhere, and link back to the
    Kazakhstan tour that supplied its one real demo asset/opportunity."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_khalifa_stewardship_demo')

    def test_geo_intelligence_reachable_from_global_nav(self):
        for url in (reverse('home'), '/about/', '/pricing/'):
            resp = self.client.get(url)
            self.assertContains(resp, '/geo-intelligence/')

    def test_kazakhstan_tour_links_back_to_geo_intelligence(self):
        resp = self.client.get(
            reverse('khalifa_stewardship_tour_operating_system:tour_detail', args=['kazakhstan-clean-heat']),
        )
        self.assertContains(resp, 'VIEW ON GEO INTELLIGENCE MAP')
        self.assertContains(resp, reverse('geo_intelligence:command_centre'))
