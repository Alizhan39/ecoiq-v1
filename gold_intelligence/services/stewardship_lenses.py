"""Mining-only evidence crosswalk for the 20 stewardship principles.

DO NOT equate a numeric proxy with Islamic ethical compliance, Shariah
certification, a Qur'anic formula or legal/environmental approval.
"""
from __future__ import annotations

from islamic_knowledge.environmental_principles import STEWARDSHIP_LENSES
from gold_intelligence.services.kpi_definitions import MINING_KPIS
from gold_intelligence.services.mine_kpis import mine_kpi_readiness

# These measure aspects of environmental/social stewardship, never the whole
# religious principle. Empty tuples explicitly represent missing indicators.
GOLD_KPI_PROXIES = {
    'mizan': ('freshwater_m3_per_t', 'electricity_kwh_per_t', 'ghg_tco2e_per_t',
              'tailings_t_per_t', 'lost_time_injury_frequency'),
    'khalifah': ('rehabilitation_pct', 'local_procurement_pct'),
    'imarat_al_ard': ('rehabilitation_pct', 'local_procurement_pct'),
    'islah': ('rehabilitation_pct',),
    'amanah': (),
    'fasad': ('tailings_t_per_t', 'ghg_tco2e_per_t', 'lost_time_injury_frequency'),
    'israf': ('freshwater_m3_per_t', 'electricity_kwh_per_t', 'tailings_t_per_t'),
    'tabdhir': ('electricity_kwh_per_t', 'tailings_t_per_t'),
    'iqtisad': ('freshwater_m3_per_t', 'electricity_kwh_per_t'),
    'tayyib': (),
    'hima': (),
    'harim': (),
    'ihya_al_mawat': ('rehabilitation_pct',),
    'ghars_al_ashjar': (),
    'rifq_bil_hayawan': (),
    'hifz_al_maa': ('freshwater_m3_per_t', 'process_water_reuse_pct'),
    'la_darar_wa_la_dirar': ('lost_time_injury_frequency', 'tailings_t_per_t',
                             'ghg_tco2e_per_t'),
    'maslaha': ('local_procurement_pct', 'lost_time_injury_frequency'),
    'dar_al_mafasid': ('lost_time_injury_frequency', 'tailings_t_per_t'),
    'sadaqa_jariya': (),
}
MISSING_EVIDENCE = {
    'amanah': 'Independently verifiable obligations, audit trail and governance evidence.',
    'tayyib': 'Toxic substances, worker/public exposure and water/soil quality.',
    'hima': 'Legally recognised protected-site boundaries and permitted activities.',
    'harim': 'Local legal setbacks, groundwater buffers and hydrological modelling.',
    'ghars_al_ashjar': 'Native planting area, seedling survival and biodiversity follow-up.',
    'rifq_bil_hayawan': 'Wildlife incident logs, habitat surveys and species impact.',
    'sadaqa_jariya': 'Long-lived charitable outcomes, governance, beneficiaries and sustainability.',
}
if set(GOLD_KPI_PROXIES) != {lens.concept for lens in STEWARDSHIP_LENSES}:
    raise RuntimeError('All 20 stewardship concepts must have an explicit gold mapping.')
if any(key not in MINING_KPIS for keys in GOLD_KPI_PROXIES.values() for key in keys):
    raise RuntimeError('Gold stewardship map references an unregistered mine KPI.')


def build_stewardship_readiness(project):
    """Read-only project-scoped status for 20 environmental stewardship lenses.

    Caller MUST enforce GoldProject membership. We do not grant knowledge
    approval, independent third-party verification, or religious compliance.
    """
    kpis = mine_kpi_readiness(project)
    by_key = {}
    for record in kpis['observations']:
        by_key.setdefault(record['key'], []).append(record)

    result = []
    for lens in STEWARDSHIP_LENSES:
        keys = GOLD_KPI_PROXIES[lens.concept]
        rows = [r for key in keys for r in by_key.get(key, [])]
        available = sum(r['value'] is not None for r in rows)
        reviewed = sum(bool(r['publishable']) for r in rows)
        hints = lens.other_sources
        result.append({
            'concept': lens.concept,
            'name_ru': lens.name_ru,
            'arabic': lens.arabic,
            'transliteration': lens.transliteration,
            'question_ru': lens.question_ru,
            'source_family': lens.source_family,
            'source_note': lens.context_note,
            'quran_refs': [r.locator for r in lens.draft.quran_references],
            'non_quran_refs': [{'type': hint.source_type, 'locator': hint.locator,
                                'url': hint.url, 'caution': hint.caution} for hint in hints],
            'linked_kpis': [{
                'key': key, 'unit': MINING_KPIS[key].unit,
                'label': MINING_KPIS[key].label,
                'observation_count': len(by_key.get(key, [])),
            } for key in keys],
            'observation_count': len(rows),
            'calculable_count': available,
            'internally_reviewed_count': reviewed,
            'missing_evidence': MISSING_EVIDENCE.get(
                lens.concept, 'Site-specific evidence and independent interpretation are required.'),
            'ethical_status': 'NOT_ASSESSED',
            'scholarly_status': 'SCHOLAR_REVIEW_PENDING',
            'note': ('Indicators are partial proxies only. Even internally reviewed '
                     'measurements do not prove an ethical or religious ruling.'),
        })
    return {'count': len(result), 'lenses': result,
            'status': 'EVIDENCE_AND_SCHOLAR_REVIEW_REQUIRED',
            'total_kpi_observations': kpis['observed_count']}
