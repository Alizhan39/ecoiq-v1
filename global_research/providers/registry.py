"""
global_research/providers/registry.py — provider registry, mirroring
`agent_runtime_model_router/services/model_adapters.py::get_adapter()`.
"""
from global_research.providers.simulated import (
    AuthoritativeStandardsProvider, CommercialManufacturerProvider,
    EarlyInnovationProvider, MarketProcurementProvider,
)

PROVIDERS = {
    'authoritative_standards_provider': AuthoritativeStandardsProvider(),
    'commercial_manufacturer_provider': CommercialManufacturerProvider(),
    'market_procurement_provider': MarketProcurementProvider(),
    'early_innovation_provider': EarlyInnovationProvider(),
}

# Every mission dispatches to at least one provider per layer — never just
# one search engine (docs/adr/ADR-global-research-engine.md decision 6).
EVIDENCE_LAYERS = ['authoritative', 'commercial', 'market', 'early_innovation']


def get_provider(name):
    provider = PROVIDERS.get(name)
    if provider is None:
        raise KeyError(f'Unknown research provider: {name!r}. Known providers: {sorted(PROVIDERS)}.')
    return provider


def all_providers():
    return list(PROVIDERS.values())


def providers_for_layer(layer):
    return [p for p in PROVIDERS.values() if p.layer == layer]


def health_check_all():
    return {name: provider.health_check() for name, provider in PROVIDERS.items()}
