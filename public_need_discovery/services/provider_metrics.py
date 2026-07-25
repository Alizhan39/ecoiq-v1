"""
public_need_discovery/services/provider_metrics.py — Phase 23: per-provider
observability. Reuses the real, already-returned `provider_reports` from
`good_agents.services.ingestion.fetch_due_signals` for fetch-level counts
(exact, not estimated) and WorldSignal.provider (a real FK — every signal
already records which provider it came from) for the qualitative funnel
counts. Never a second telemetry system — this only aggregates rows that
already exist.
"""
from good_agents.models import SignalProvider, WorldSignal
from public_need_discovery.models import ACTIONABILITY_TERMINAL_REJECTED_STATES, ProviderRunMetrics


def record_run_metrics(run, provider_reports):
    """
    One ProviderRunMetrics row per provider report. `records_fetched`/
    `errors`/`error_detail` come directly from the real fetch result.
    The qualitative funnel counts are computed from this run's own
    opportunities, attributed back to a provider via each opportunity's
    lead WorldSignal.provider (real FK, set at normalise_signal time —
    never inferred from title/publisher text matching).
    """
    opportunities = list(run.opportunities.select_related('pilot_candidate_assessment').all())
    signals_by_title = {
        s.title: s for s in WorldSignal.objects.filter(title__in=[
            t for o in opportunities for t in o.detected_signals
        ])
    }

    rows = []
    for report in provider_reports:
        provider = SignalProvider.objects.filter(slug=report['slug']).first()
        if provider is None:
            continue

        provider_opportunities = [
            o for o in opportunities
            if any(signals_by_title.get(t) and signals_by_title[t].provider_id == provider.pk for t in o.detected_signals)
        ]

        informational_only = potentially_actionable = actionability_qualified = rejected = 0
        missing_jurisdiction = missing_responsible_body = official_routes_found = 0
        for opportunity in provider_opportunities:
            candidate = getattr(opportunity, 'pilot_candidate_assessment', None)
            if candidate is None:
                informational_only += 1
                continue
            if candidate.actionability_state == 'informational_only':
                informational_only += 1
            elif candidate.actionability_state == 'potentially_actionable':
                potentially_actionable += 1
            elif candidate.actionability_qualified:
                actionability_qualified += 1
            elif candidate.actionability_state in ACTIONABILITY_TERMINAL_REJECTED_STATES:
                rejected += 1
            if not candidate.jurisdiction_resolved:
                missing_jurisdiction += 1
            if not candidate.organisation_roles.filter(confirmed=True).exists():
                missing_responsible_body += 1
            if candidate.official_process_route_reference:
                official_routes_found += 1

        row, _ = ProviderRunMetrics.objects.update_or_create(
            provider=provider, run=run,
            defaults=dict(
                records_fetched=report['items_fetched'],
                duplicates=max(0, report['items_fetched'] - report['items_after_validation']),
                informational_only=informational_only,
                potentially_actionable=potentially_actionable,
                actionability_qualified=actionability_qualified,
                rejected=rejected,
                missing_jurisdiction=missing_jurisdiction,
                missing_responsible_body=missing_responsible_body,
                official_routes_found=official_routes_found,
                errors=0 if report['success'] else 1,
                error_detail=report.get('error', ''),
            ),
        )
        rows.append(row)
    return rows
