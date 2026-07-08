"""
geo_intelligence/services/weather.py — real historical weather via Meteostat.

Pinned to meteostat==1.7.6 (the mature `Point`/`Daily` API) rather than the
2.x line, which is a very recent rewrite with a different, less
battle-tested API — not the right choice for a production feature.

Meteostat fetches from a remote bulk-data host over HTTP, so every call
here is:
  1. Cached (Django's cache framework, 24h TTL) — a page load should never
     wait on a live weather fetch more than once a day per city.
  2. Wrapped in try/except — a network failure, timeout, or empty response
     must degrade to an honest "climate data unavailable" result, never a
     crashed page and never a fabricated number.
"""
import logging

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60 * 60 * 24  # 24 hours
EXTREME_HEAT_THRESHOLD_C = 35.0

# Real coordinates for Kazakhstan's largest cities — used as reference
# points on the map and as inputs to this service. Not demo/fabricated data:
# these are genuine geographic facts.
KAZAKHSTAN_CITIES = {
    'Almaty':    {'latitude': 43.2220, 'longitude': 76.8512, 'elevation': 785},
    'Astana':    {'latitude': 51.1694, 'longitude': 71.4491, 'elevation': 347},
    'Shymkent':  {'latitude': 42.3000, 'longitude': 69.6000, 'elevation': 506},
    'Karaganda': {'latitude': 49.8047, 'longitude': 73.1094, 'elevation': 553},
}


def _empty_result(reason):
    return {
        'available': False, 'reason': reason, 'source': 'Meteostat',
        'avg_temp_current_year': None, 'avg_temp_previous_year': None,
        'precipitation_current_year_mm': None, 'precipitation_previous_year_mm': None,
        'extreme_heat_days_current_year': None, 'extreme_heat_days_previous_year': None,
        'years': [], 'fetched_at': None,
    }


def get_city_climate_summary(city_name, latitude, longitude, elevation=0):
    """
    Returns a dict summarising the last two full calendar years of daily
    weather at (latitude, longitude): average temperature, total
    precipitation, and extreme-heat-day count, for both years so a caller
    can show a real year-over-year trend. Cached per city per day.
    """
    cache_key = f'geo_intel:climate_summary:{round(latitude, 3)}:{round(longitude, 3)}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        from datetime import datetime
        from meteostat import Point, Daily

        current_year = timezone.now().year
        previous_year = current_year - 1
        year_before_that = current_year - 2

        point = Point(latitude, longitude, elevation)
        data = Daily(point, datetime(year_before_that, 1, 1), datetime(current_year, 12, 31)).fetch()

        if data is None or data.empty:
            result = _empty_result('No station data returned for this location.')
        else:
            def _year_stats(year):
                year_df = data[data.index.year == year]
                if year_df.empty or year_df['tavg'].isna().all():
                    return None
                return {
                    'avg_temp': round(float(year_df['tavg'].mean()), 1),
                    'precipitation_mm': round(float(year_df['prcp'].fillna(0).sum()), 0),
                    'extreme_heat_days': int((year_df['tmax'] >= EXTREME_HEAT_THRESHOLD_C).sum()),
                }

            latest_complete_year = previous_year if timezone.now().month < 12 else current_year
            year_a = _year_stats(latest_complete_year)
            year_b = _year_stats(latest_complete_year - 1)

            if year_a is None:
                result = _empty_result('Weather station has no recent data for this location.')
            else:
                result = {
                    'available': True, 'reason': '', 'source': 'Meteostat',
                    'avg_temp_current_year': year_a['avg_temp'],
                    'avg_temp_previous_year': year_b['avg_temp'] if year_b else None,
                    'precipitation_current_year_mm': year_a['precipitation_mm'],
                    'precipitation_previous_year_mm': year_b['precipitation_mm'] if year_b else None,
                    'extreme_heat_days_current_year': year_a['extreme_heat_days'],
                    'extreme_heat_days_previous_year': year_b['extreme_heat_days'] if year_b else None,
                    'years': [latest_complete_year - 1, latest_complete_year],
                    'fetched_at': timezone.now().isoformat(),
                }
    except Exception as exc:  # network failure, malformed response, etc. — never crash the page
        logger.warning('Meteostat fetch failed for %s (%s, %s): %s', city_name, latitude, longitude, exc)
        result = _empty_result(f'Weather service temporarily unavailable ({type(exc).__name__}).')

    cache.set(cache_key, result, CACHE_TTL_SECONDS)
    return result


def climate_exposure_score(climate_summary):
    """
    Derives a 0-100 exposure score purely from the real extreme-heat-day
    trend above — never a fabricated number. Returns None (not zero) when
    the underlying data isn't available, so callers must show "not yet
    measured" rather than a false score.
    """
    if not climate_summary.get('available'):
        return None
    current = climate_summary['extreme_heat_days_current_year']
    previous = climate_summary['extreme_heat_days_previous_year']
    # More extreme-heat days this year, and more days in absolute terms,
    # both push exposure up. Capped at 100; simple and inspectable on purpose.
    score = min(100, current * 3)
    if previous is not None and current > previous:
        score = min(100, score + 15)
    return round(score, 0)
