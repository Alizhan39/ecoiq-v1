"""Legally gated, source-linked preliminary public mine and market time series.

Gold-mine observations are a *limited research extraction* from quarterly
operator disclosures, without permission to bulk ingest or redistribute for
commercial data services. These are not SCADA/shift data, validated site
measurements, or environmental or mineral resource determinations.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from functools import lru_cache
import json
import math
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parents[1] / 'reference_data'
RIGHTS = BASE / 'source_rights_register_2026-10.json'
SERIES = BASE / 'first_gold_time_series_2026-10.json'

ALLOWED_STAGES = {
    'GOLD_IN_CONCENTRATE': ('gold_in_concentrate', 'thousand_gold_ounces_in_concentrate', 'quarterly'),
    'PAYABLE_GE': ('payable_GE_production', 'thousand_gold_equivalent_ounces', 'quarterly'),
    'MARKET_PRICE_NOT_PRODUCTION': ('gold_price_monthly_average', 'USD_per_troy_ounce', 'monthly'),
}


def _date(text):
    if not isinstance(text, str):
        raise ValueError('ISO date required.')
    parsed = date.fromisoformat(text)
    if parsed.isoformat() != text:
        raise ValueError('Date must be YYYY-MM-DD.')
    return parsed


def validate_time_series(manifest, rights):
    """Reject fabricated/mislabeled dates, unit mixups and rights escalation."""
    if manifest.get('schema_version') != 1 or rights.get('schema_version') != 1:
        raise ValueError('Unexpected schema version.')
    _date(manifest['as_of'])
    if manifest['rights_register'] != RIGHTS.name:
        raise ValueError('Source rights register mismatch.')
    from gold_intelligence.services.public_operator_benchmarks import public_gold_inventory
    assets = {row['id'] for row in public_gold_inventory()['assets']}
    ids = set()
    for row in manifest['series']:
        if row['id'] in ids:
            raise ValueError('Duplicate time series ID.')
        ids.add(row['id'])
        stage = row['production_stage']
        if stage not in ALLOWED_STAGES:
            raise ValueError('Unknown production stage.')
        metric, unit, frequency = ALLOWED_STAGES[stage]
        if (row['metric'], row['unit'], row['frequency']) != (metric, unit, frequency):
            raise ValueError('Stage/metric/unit/frequency mismatch.')
        if stage == 'MARKET_PRICE_NOT_PRODUCTION':
            if row['asset_id'] is not None:
                raise ValueError('Gold market prices are not observations of an ore deposit.')
        elif row['asset_id'] not in assets:
            raise ValueError('Mine series must reference a known, explicitly scoped asset.')
        src = rights['sources'].get(row['source_rights_key'])
        if src is None or not src['source_urls']:
            raise ValueError('Unknown or untraceable source rights.')
        if stage == 'MARKET_PRICE_NOT_PRODUCTION':
            if row['source_rights_key'] != 'world_bank_pink_sheet' or src['rights_status'] != 'CC_BY_4_0':
                raise ValueError('Market data license mismatch.')
        elif src['rights_status'] != 'PERMISSION_NOT_CONFIRMED':
            raise ValueError('Issuer data cannot silently inherit open-data permissions.')
        previous_end = None
        seen = set()
        for obs in row['observations']:
            period = obs['period']
            if period in seen:
                raise ValueError('Duplicate observation period.')
            seen.add(period)
            start = _date(obs['period_start'])
            if start > _date(manifest['as_of']):
                raise ValueError('Future observation.')
            if frequency == 'quarterly':
                y, q = period.split('-Q')
                q = int(q)
                if not 1 <= q <= 4 or start.month != 1 + (q - 1) * 3 or start.day != 1 or start.year != int(y):
                    raise ValueError('Incorrect quarter start.')
                end = _date(obs['period_end'])
                expected = (date(int(y) + 1, 1, 1) if q == 4 else
                            date(int(y), q * 3 + 1, 1))
                if end.toordinal() != expected.toordinal() - 1:
                    raise ValueError('Quarter end mismatch.')
                if _date(obs['reported_at']) < end:
                    raise ValueError('Publication predates observation period.')
                if _date(obs['reported_at']) > _date(manifest['as_of']):
                    raise ValueError('Unpublished quarterly observation.')
                if obs['source_url'] not in src['source_urls']:
                    raise ValueError('Quarterly value must cite its original release.')
            else:
                if period != start.strftime('%Y-%m') or start.day != 1:
                    raise ValueError('Wrong monthly period.')
                if 'period_end' in obs:
                    raise ValueError('Do not invent monthly end dates.')
                if obs.get('verified_against_original_workbook') is not False:
                    raise ValueError('Unverified workbook extraction must not claim direct verification.')
                if obs['source_url'] not in src['source_urls']:
                    raise ValueError('Market value must cite the licensed primary source.')
            if previous_end is not None and start <= previous_end:
                raise ValueError('Periods must be strictly increasing and non-overlapping.')
            previous_end = _date(obs['period_end']) if frequency == 'quarterly' else start
            value = obs['value']
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError('Non-finite or negative observation.')
        if not row['observations']:
            raise ValueError('Empty series cannot be advertised as connected.')
    if len(ids) != 4:
        raise ValueError('Expected exactly four named pilot time series.')


@lru_cache(maxsize=1)
def _snapshot():
    manifest = json.loads(SERIES.read_text(encoding='utf-8'))
    rights = json.loads(RIGHTS.read_text(encoding='utf-8'))
    validate_time_series(manifest, rights)
    return manifest, rights


def source_rights_summary():
    """Returns a copy: caller must not mutate release-owned catalogues."""
    return deepcopy(_snapshot()[1])


def available_time_series():
    data, rights = _snapshot()
    return deepcopy([
        {
            'id': row['id'],
            'asset_id': row['asset_id'],
            'metric': row['metric'],
            'unit': row['unit'],
            'frequency': row['frequency'],
            'observations': len(row['observations']),
            'source_rights_status': rights['sources'][row['source_rights_key']]['rights_status'],
            'commercial_redistribution_allowed': (
                rights['sources'][row['source_rights_key']]['commercial_redistribution_allowed']),
            'data_verified_from_primary_workbook': (
                False if row['production_stage'] == 'MARKET_PRICE_NOT_PRODUCTION' else None),
        } for row in data['series']
    ])


def time_series_card(series_id):
    """Research-only values and original links; no public API or ML training."""
    data, rights = _snapshot()
    row = next((r for r in data['series'] if r['id'] == series_id), None)
    if row is None:
        return None
    src = rights['sources'][row['source_rights_key']]
    return deepcopy({
        'series': row,
        'rights': src,
        'data_classification': 'PUBLISHED_OPERATOR_RESEARCH_ONLY' if
        row['production_stage'] != 'MARKET_PRICE_NOT_PRODUCTION' else
        'ATTRIBUTED_CC_BY_4_0_SECONDARY_TRANSCRIPTION_PENDING_ORIGINAL_CROSSCHECK',
        'automated_operational_ingestion_enabled': False,
        'commercial_bulk_redistribution_enabled': False,
        'optimisation_outcome_claim_allowed': False,
        'note': ('Quarterly disclosures and monthly commodity prices are not '
                 'live plant telemetry. Do not subtract upstream metal '
                 'from payable production to allege losses; the stages and '
                 'inventory periods are different.'),
    })


def series_scenario_eligibility(series_id):
    """Fail closed for financial/ML/pilot jobs needing approved source rights."""
    card = time_series_card(series_id)
    if card is None:
        return 'UNKNOWN_SERIES'
    if card['series']['production_stage'] != 'MARKET_PRICE_NOT_PRODUCTION':
        return 'OPERATOR_PERMISSION_PENDING'
    if any(not row['verified_against_original_workbook'] for row in card['series']['observations']):
        return 'ORIGINAL_PRICE_WORKBOOK_RECONCILIATION_REQUIRED'
    return 'ATTRIBUTED_OPEN_DATA_ONLY'
