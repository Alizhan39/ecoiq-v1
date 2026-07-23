"""
good_agents/services/ingestion.py — real ingestion orchestration (PR4
Phase 5):

    SignalProvider -> provider fetch -> raw source reference -> raw signal
    dicts (ready for services.signals.normalise_signal / discovery_engine)

One provider's failure never kills the run: each provider is fetched
through `provider_adapters.fetch_from_provider`, which never raises — a
bad response, a timeout, an SSRF block, or an adapter bug all come back as
an honest `ProviderFetchResult(success=False, error=...)` instead of an
exception. This module's own job is only to aggregate results and update
each SignalProvider's health fields (Phase 31 — no silent ingestion
failures) truthfully either way.
"""
import logging

from good_agents.models import SignalProvider
from good_agents.services.provider_adapters import fetch_from_provider

logger = logging.getLogger(__name__)


def fetch_due_signals(providers=None):
    """
    providers: iterable of SignalProvider rows to fetch from now (defaults
    to every provider not marked 'inactive'). Returns
    (raw_signals: list[dict], provider_reports: list[dict]).

    Each raw signal dict carries a private `_provider` key (the actual
    SignalProvider instance) so the caller can attribute normalisation
    (fact/claim/inference classification depends on the provider's trust
    tier — see services.signals.classify_content) back to the exact
    provider that supplied it.
    """
    providers = list(providers) if providers is not None else list(SignalProvider.objects.exclude(status='inactive'))
    raw_signals = []
    provider_reports = []

    for provider in providers:
        result = fetch_from_provider(provider)

        if result.success:
            provider.mark_refreshed()
            for raw in result.raw_signals:
                raw['_provider'] = provider
            raw_signals.extend(result.raw_signals)
        else:
            provider.mark_failed(result.error)
            logger.warning('good_agents.ingestion: provider %s failed: %s', provider.slug, result.error)

        provider_reports.append({
            'slug': provider.slug,
            'name': provider.name,
            'success': result.success,
            'error': result.error,
            'items_fetched': result.items_fetched,
            'items_after_validation': result.items_after_validation,
        })

    return raw_signals, provider_reports
