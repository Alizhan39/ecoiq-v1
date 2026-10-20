"""Versioned, deterministic mine-specific KPI method registry.

Values are ratios of like-period raw observations, NEVER machine-generated
mine ratings. Quran/Maqasid principles inform metric selection; thresholds,
formula multipliers and units here are engineering conventions, not scripture.
"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class MiningKPIDefinition:
    key: str
    label: str
    numerator: str
    denominator: str
    unit: str
    multiplier: Decimal
    mizan_dimension: str
    percent: bool = False
    method_version: str = '1'


MINING_KPIS = {
    item.key: item for item in (
        MiningKPIDefinition('gold_recovery_pct', 'Metallurgical gold recovery',
                            'Recovered gold (g)', 'Gold in processed feed (g)',
                            '%', Decimal('100'), 'resource_efficiency', True),
        MiningKPIDefinition('freshwater_m3_per_t', 'Freshwater withdrawal intensity',
                            'Freshwater withdrawn (m³)', 'Dry ore processed (t)',
                            'm³/t', Decimal('1'), 'water'),
        MiningKPIDefinition('process_water_reuse_pct', 'Process water recirculation',
                            'Recirculated water (m³)', 'Total process water supplied (m³)',
                            '%', Decimal('100'), 'water', True),
        MiningKPIDefinition('electricity_kwh_per_t', 'Electricity intensity',
                            'Electricity used (kWh)', 'Dry ore processed (t)',
                            'kWh/t', Decimal('1'), 'energy'),
        MiningKPIDefinition('tailings_t_per_t', 'Tailings generation intensity',
                            'Tailings produced (dry t)', 'Dry ore processed (t)',
                            't/t', Decimal('1'), 'environment'),
        MiningKPIDefinition('rehabilitation_pct', 'Land rehabilitation ratio',
                            'Land restored and accepted (ha)', 'Disturbed land (ha)',
                            '%', Decimal('100'), 'intergenerational', True),
        MiningKPIDefinition('local_procurement_pct', 'Local procurement share',
                            'Eligible local supplier spend (USD)', 'Total eligible procurement spend (USD)',
                            '%', Decimal('100'), 'justice', True),
        MiningKPIDefinition('lost_time_injury_frequency', 'Lost-time injury frequency',
                            'Recordable lost-time injuries (count)', 'Worker-hours (h)',
                            'per 1,000,000 h', Decimal('1000000'), 'worker'),
        MiningKPIDefinition('ghg_tco2e_per_t', 'Scope-defined emissions intensity',
                            'Emissions within declared scope (tCO₂e)', 'Dry ore processed (t)',
                            'tCO₂e/t', Decimal('1'), 'environment'),
    )
}
KPI_CHOICES = [(item.key, item.label) for item in MINING_KPIS.values()]
