"""Cited public Kazakhstan gold-mine research seed; never private mine evidence.

This is a source-linked research catalogue for human review, NOT a canonical
mine inventory, geological resource estimate, audited KPI dataset, operational
SCADA feed, licence register, or a ranking of companies. It cannot approve
an operational Mizan indicator nor update mine licences or score a mine.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

CATALOGUE = Path(__file__).resolve().parents[1] / 'reference_data' / 'kazakhstan_gold_public_seed_2026.json'
_ALLOWED_STATUS = 'reported_operating_in_2025'
_ALLOWED_CONFIDENCE = 'PUBLIC_OPERATOR_REPORTED_UNAUDITED_AS_SITE_EVIDENCE'
_UNIT_BY_METRIC = {
    'ore_processed': 'thousand_tonnes',
    'leach_ore_processed': 'thousand_tonnes',
    'flotation_ore_processed': 'thousand_tonnes',
    'ore_mined': 'thousand_tonnes',
    'processed_grade': 'g_Au_per_t',
    'flotation_gold_recovery': 'percent',
    'leach_gold_recovery': 'percent',
    'gold_recovery': 'percent',
    'heap_leach_gold_recovery': 'percent',
    'gold_in_concentrate': 'thousand_ounces',
    'payable_GE_production': 'thousand_GE_ounces',
    'mined_gold_production': 'tonnes_Au',
    'gold_production': 'thousand_ounces',
}


def _validate(dataset: dict[str, Any]) -> None:
    if dataset.get('schema_version') != '1.0' or dataset.get('claim_all_active_mines') is not False:
        raise ValueError('Public source inventory must explicitly be non-exhaustive.')
    if dataset.get('coverage') != 'NON_EXHAUSTIVE_PUBLIC_SEED':
        raise ValueError('Public inventory cannot claim complete Kazakhstan coverage.')
    sources = dataset['sources']
    for ref, source in sources.items():
        if not ref or not source.get('title'):
            raise ValueError('Every research source needs ID and title.')
        url = urlparse(source.get('url', ''))
        if url.scheme != 'https' or not url.hostname or url.username or url.password:
            raise ValueError('Public research URLs must be absolute HTTPS source links.')
    seen_assets = set()
    for asset in dataset['assets']:
        aid = asset['id']
        if aid in seen_assets or asset['status'] != _ALLOWED_STATUS:
            raise ValueError('Duplicate mine or unsupported evidence status.')
        seen_assets.add(aid)
        if asset['last_operation_evidence_year'] > 2025:
            raise ValueError('Never claim ongoing 2026 operations from 2025 evidence.')
        if not asset['source_refs'] or any(ref not in sources for ref in asset['source_refs']):
            raise ValueError('Every asset requires traceable public evidence.')

    seen = set()
    for obs in dataset['observations']:
        if obs['id'] in seen or obs['asset_id'] not in seen_assets:
            raise ValueError('Duplicate observation or unknown mine.')
        seen.add(obs['id'])
        if obs['source_ref'] not in sources or obs['verification'] != _ALLOWED_CONFIDENCE:
            raise ValueError('Public facts cannot impersonate independently validated site evidence.')
        if type(obs['value']) not in (int, float) or obs['value'] < 0:
            raise ValueError('Observations must use finite, nonnegative numeric values.')
        if not math.isfinite(obs['value']):
            raise ValueError('Nonfinite measured value.')
        unit = _UNIT_BY_METRIC.get(obs['metric'])
        if unit is None or obs['unit'] != unit:
            raise ValueError('Metric/unit mismatch.')
        if obs['metric'].endswith('recovery') and obs['value'] > 100:
            raise ValueError('Recovery cannot exceed 100%.')
        if not obs['period']:
            raise ValueError('Period required.')
    for metric in dataset['operator_observations']:
        if metric['source_ref'] not in sources or metric['scope'] not in ('company', 'group'):
            raise ValueError('Company/group metrics must never be promoted to a mine.')

    hypothesis_ids = set()
    for hyp in dataset['optimisation_hypotheses']:
        if hyp['id'] in hypothesis_ids or hyp['asset_id'] not in seen_assets:
            raise ValueError('Duplicate or unknown hypothesis asset.')
        hypothesis_ids.add(hyp['id'])
        if hyp['status'] != 'PROPOSAL_NOT_AUDITED':
            raise ValueError('Public process hypotheses cannot claim on-site audit results.')
        if not hyp['source_refs'] or any(ref not in sources for ref in hyp['source_refs']):
            raise ValueError('Untraceable optimisation hypothesis.')


@lru_cache(maxsize=1)
def _source_snapshot() -> dict[str, Any]:
    data = json.loads(CATALOGUE.read_text(encoding='utf-8'))
    _validate(data)
    return data


def public_gold_inventory() -> dict[str, Any]:
    """Defensive copy: callers cannot mutate the cached source snapshot."""
    return deepcopy(_source_snapshot())


def mine_evidence_card(asset_id: str) -> dict[str, Any] | None:
    """Source-linked, no scoring and no private project lookup."""
    data = _source_snapshot()
    asset = next((a for a in data['assets'] if a['id'] == asset_id), None)
    if asset is None:
        return None
    obs = [x for x in data['observations'] if x['asset_id'] == asset_id]
    hypotheses = [h for h in data['optimisation_hypotheses'] if h['asset_id'] == asset_id]
    referenced = {ref for x in obs for ref in (x['source_ref'],)}
    referenced.update(asset['source_refs'])
    referenced.update(ref for h in hypotheses for ref in h['source_refs'])
    return deepcopy({
        'asset': asset,
        'observations': obs,
        'hypotheses': hypotheses,
        'sources': {k: data['sources'][k] for k in sorted(referenced)},
        'is_verified_operational_kpi': False,
        'is_exhaustive_operating_mine_register': False,
    })


def recovery_uplift_sensitivity(ore_tonnes: float, head_grade_gpt: float,
                                recovery_uplift_percentage_points: float) -> dict[str, Any]:
    """Arithmetic *sensitivity only*: extra recovered Au in flotation/concentrate.

    Only meaningful within an independently reviewed metallurgical mass
    balance. It is NOT a prediction, resource/reserve estimate, economic gain
    or forecast of profitable ounces. Feed tonnes and grade are provided
    explicitly: no mixing of a hub's feed with a single deposit's grade.
    """
    inputs = (ore_tonnes, head_grade_gpt, recovery_uplift_percentage_points)
    if any(type(n) not in (int, float) or not math.isfinite(n) or n < 0 for n in inputs):
        return {'available': False, 'reason': 'Finite, nonnegative numeric inputs required.'}
    if not (0 <= recovery_uplift_percentage_points <= 100):
        return {'available': False, 'reason': 'Recovery uplift must be between 0 and 100 percentage points.'}
    grams = ore_tonnes * head_grade_gpt * recovery_uplift_percentage_points / 100
    return {
        'available': True,
        'additional_recovered_gold_grams': round(grams, 2),
        'additional_recovered_gold_troy_ounces': round(grams / 31.1034768, 2),
        'status': 'SCENARIO_ONLY_NOT_VALIDATED',
        'conditions': ('Identical feed, grade, mineralogy and circuit, with '
                       'a feasible verified absolute recovery uplift; downstream '
                       'payability, costs and ore depletion are NOT modelled.'),
    }
