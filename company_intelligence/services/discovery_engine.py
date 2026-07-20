"""
company_intelligence/services/discovery_engine.py — feat/company-discovery-
ranking (PR 11): "Which companies have evidence supporting the stewardship
principles I care about, and which of those currently pass or conditionally
pass my selected Shariah screen?"

Two independent lenses, never combined into one blended score (the same
discipline PR9 established between Shariah screening and 114-KPI
alignment): Shariah screening status is a FILTER (a company either matches
the requested screen states or it doesn't — never itself weighted into a
ranking number), while 114-KPI evidence coverage feeds a transparent,
component-based RANKING. There is no opaque "EcoIQ investment score" here
and no ranking by expected financial return — only by evidence-backed
research relevance under whatever criteria the user selected. Every
component is returned alongside the composite so a UI can (and must) show
both, never the composite alone.

Reuses, never duplicates:
- company_intelligence.services.shariah_screening.latest_screen_for()
- company_intelligence.services.kpi_engine (PRINCIPLES/status vocabulary)
- company_intelligence.services.freshness.screening_freshness()
- company_intelligence.services.data_origin.company_data_origin()
- company_intelligence.services.evidence_quality.evidence_quality_for_memory()
- harvester.verification.source_tier()
"""
from companies.models import CompanyProfile

from company_intelligence.models import CompanyKPIEvidenceLink
from company_intelligence.services import data_origin, evidence_quality, freshness, shariah_screening
from core.esg_principles_data import PRINCIPLES

PRINCIPLES_BY_ID = {p['id']: p for p in PRINCIPLES}

# Ranking components and their default weights — every one documented,
# every one overridable by a caller (see the `weights` param below), no
# hidden component. `kpi_alignment` is the only component that can be
# pulled down by conflicting evidence; every other component only ever
# helps or is neutral — missing data is EXCLUDED from the composite's own
# weighted average (renormalised over whatever a company actually has),
# never treated as a zero.
DEFAULT_RANKING_WEIGHTS = {
    'kpi_alignment': 0.40,
    'source_authority': 0.20,
    'recency': 0.15,
    'corroboration': 0.15,
    'data_completeness': 0.10,
}

SUPPORT_STATUSES = {'strong_support', 'support'}


def _kpi_component_for_company(company_profile, kpi_ids):
    """
    For the selected kpi_ids (all 114 if none selected), buckets this
    company's CONFIRMED-evidence status per KPI and returns a real [0,1]
    component. 'mixed' evidence counts toward neither the supported nor the
    conflicting bucket on its own (shown separately) — absence of evidence
    (not_assessed/insufficient_evidence) is NEVER treated as negative
    alignment, only ever neutral.
    """
    assessments = {a.kpi_id: a for a in company_profile.kpi_assessments.all()}
    ids = kpi_ids or list(PRINCIPLES_BY_ID.keys())

    supported, conflicting, mixed, insufficient, not_assessed = [], [], [], [], []
    for kpi_id in ids:
        assessment = assessments.get(kpi_id)
        status = assessment.status if assessment else 'not_assessed'
        if status in SUPPORT_STATUSES:
            supported.append(kpi_id)
        elif status == 'conflict':
            conflicting.append(kpi_id)
        elif status == 'mixed':
            mixed.append(kpi_id)
        elif status == 'insufficient_evidence':
            insufficient.append(kpi_id)
        else:
            not_assessed.append(kpi_id)

    raw = len(supported) - len(conflicting)
    component = max(0.0, min(1.0, (raw / len(ids) + 1) / 2)) if ids else None
    return {
        'selected_count': len(ids),
        'supported_kpi_ids': supported, 'conflicting_kpi_ids': conflicting,
        'mixed_kpi_ids': mixed, 'insufficient_kpi_ids': insufficient, 'not_assessed_kpi_ids': not_assessed,
        'component': component,
    }


def _evidence_quality_for_selected_kpis(company_profile, kpi_ids):
    """
    Averages real harvester-backed quality sub-scores (source authority,
    recency, corroboration) across CONFIRMED evidence linked to the
    selected KPIs (every confirmed KPI-linked evidence this company has, if
    no KPIs were selected). Honestly None when no harvester-backed evidence
    exists for this scope — never a fabricated 0.
    """
    from evidence_memory.models import EvidenceMemory

    assessments = (
        company_profile.kpi_assessments.filter(kpi_id__in=kpi_ids) if kpi_ids
        else company_profile.kpi_assessments.all()
    )
    memory_ids = set()
    for a in assessments.prefetch_related('evidence_links'):
        for link in a.evidence_links.all():
            if link.review_state == 'confirmed':
                memory_ids.add(link.evidence_id)

    memories = list(EvidenceMemory.objects.filter(pk__in=memory_ids))
    qualities = [evidence_quality.evidence_quality_for_memory(m) for m in memories]
    harvester_backed = [q for q in qualities if q['has_harvester_record']]

    def _avg(key):
        values = [q[key] for q in harvester_backed if q[key] is not None]
        return round(sum(values) / len(values), 3) if values else None

    return {
        'evidence_count': len(memories), 'harvester_backed_count': len(harvester_backed),
        'source_authority': _avg('source_authority'), 'recency': _avg('recency'),
        'corroboration': _avg('corroboration'),
        'conflicting_evidence_count': sum(1 for q in qualities if q['is_conflicting']),
    }


def _company_meets_min_tier(company_profile, min_tier):
    """
    True if this company has at least one CONFIRMED KPI-linked evidence row
    backed by a real harvester.Evidence at tier <= min_tier (tier 1 is the
    highest authority — regulatory filings/audited statements/government
    records; see harvester.verification.SOURCE_TIER_BY_TYPE). No qualifying
    evidence -> False; a filter this strict must exclude, never silently
    pass, a company with nothing meeting the bar.
    """
    if min_tier is None:
        return True
    from harvester.models import Evidence as HarvesterEvidence
    from harvester.verification import source_tier as tier_for_type

    memories = CompanyKPIEvidenceLink.objects.filter(
        assessment__company=company_profile, review_state='confirmed',
    ).select_related('evidence').values_list('evidence__source_reference', flat=True)

    harvester_pks = []
    for ref in memories:
        if ref and ref.startswith('harvester.Evidence:'):
            try:
                harvester_pks.append(int(ref.split(':', 1)[1]))
            except ValueError:
                continue

    for ev in HarvesterEvidence.objects.filter(pk__in=harvester_pks).select_related('document', 'source'):
        if ev.document_id:
            tier = ev.document.source_tier
        elif ev.source_id:
            tier = tier_for_type(ev.source.source_type)
        else:
            continue
        if tier <= min_tier:
            return True
    return False


def discover_companies(criteria=None):
    """
    criteria (all optional):
      shariah_status        — iterable of SCREEN_RESULT_CHOICES keys
                               ('pass'/'conditional'/'fail'/
                               'insufficient_data'/'not_screened'). Empty/
                               None means no Shariah filter.
      kpi_ids                — iterable of int (1-114). Empty/None matches
                               every company; ranking then reflects all 114.
      sector / country        — exact sector match / substring country match,
                               same convention as companies.views.directory.
      min_source_tier         — 1-4, or None for no tier filter (see
                               _company_meets_min_tier).
      require_current_screening — bool; excludes STALE Shariah screenings.
      controversy_state       — 'any' (default) | 'none' | 'has_unresolved'.
      include_demo            — bool, default False. Demo companies are
                               EXCLUDED from real discovery unless a caller
                               explicitly opts in.

    Returns a list of companies.CompanyProfile — the candidate pool BEFORE
    ranking (pass straight into rank_company_matches()).
    """
    criteria = criteria or {}
    qs = CompanyProfile.objects.filter(status__in=('public', 'verified')).select_related('company')

    sector = criteria.get('sector', '')
    country = criteria.get('country', '')
    if sector:
        qs = qs.filter(company__sector=sector)
    if country:
        qs = qs.filter(company__country__icontains=country)

    companies = list(qs)

    if not criteria.get('include_demo'):
        companies = [c for c in companies if data_origin.company_data_origin(c)['origin'] != data_origin.DEMO]

    kpi_ids = list(criteria.get('kpi_ids') or [])
    if kpi_ids:
        confirmed_company_ids = set(
            CompanyKPIEvidenceLink.objects.filter(
                review_state='confirmed', assessment__kpi_id__in=kpi_ids,
            ).values_list('assessment__company_id', flat=True)
        )
        companies = [c for c in companies if c.pk in confirmed_company_ids]

    shariah_status = set(criteria.get('shariah_status') or [])
    if shariah_status:
        filtered = []
        for c in companies:
            screen = shariah_screening.latest_screen_for(c)
            result = screen.overall_result if screen else 'not_screened'
            if result in shariah_status:
                filtered.append(c)
        companies = filtered

    if criteria.get('require_current_screening'):
        filtered = []
        for c in companies:
            fresh = freshness.screening_freshness(shariah_screening.latest_screen_for(c))
            if fresh['is_stale'] is False:
                filtered.append(c)
        companies = filtered

    controversy_state = criteria.get('controversy_state', 'any')
    if controversy_state == 'none':
        companies = [c for c in companies if not c.controversies.filter(status='unresolved').exists()]
    elif controversy_state == 'has_unresolved':
        companies = [c for c in companies if c.controversies.filter(status='unresolved').exists()]

    min_source_tier = criteria.get('min_source_tier')
    if min_source_tier is not None:
        companies = [c for c in companies if _company_meets_min_tier(c, min_source_tier)]

    return companies


def rank_company_matches(companies, criteria=None, weights=None):
    """
    Computes every ranking component for each company (never hidden behind
    the composite) plus one transparent weighted composite, sorted
    descending. Missing components are excluded from the composite's own
    weighted average (renormalised over whatever a company actually has),
    never coerced to zero. A company with NO components available at all
    gets composite=None and sorts last — "no qualifying evidence", not "0
    alignment".
    """
    criteria = criteria or {}
    kpi_ids = list(criteria.get('kpi_ids') or [])
    weights = weights or DEFAULT_RANKING_WEIGHTS

    results = []
    for company in companies:
        kpi = _kpi_component_for_company(company, kpi_ids)
        eq = _evidence_quality_for_selected_kpis(company, kpi_ids)
        screen = shariah_screening.latest_screen_for(company)
        fresh = freshness.screening_freshness(screen)

        components = {
            'kpi_alignment': kpi['component'],
            'source_authority': eq['source_authority'],
            'recency': eq['recency'],
            'corroboration': eq['corroboration'],
            'data_completeness': (screen.data_completeness_pct / 100.0) if screen else None,
        }

        weighted_sum, weight_total = 0.0, 0.0
        for key, value in components.items():
            if value is None:
                continue
            w = weights.get(key, 0.0)
            weighted_sum += value * w
            weight_total += w
        composite = round(weighted_sum / weight_total, 4) if weight_total > 0 else None

        results.append({
            'company': company,
            'kpi_detail': kpi,
            'evidence_quality_detail': eq,
            'shariah_screen': screen,
            'freshness': fresh,
            'controversies': list(company.controversies.all()),
            'data_origin': data_origin.company_data_origin(company),
            'components': components,
            'weights_used': dict(weights),
            'composite': composite,
        })

    results.sort(key=lambda r: (r['composite'] is None, -(r['composite'] or 0)))
    return results


def compare_companies(company_profiles, criteria=None):
    """
    Same component computation as rank_company_matches(), for a small (2-5)
    explicit set of companies chosen for side-by-side research comparison —
    presented in the order given, never re-sorted (comparison is not a
    ranking). Never includes expected-return/price-target/trading-signal
    fields — see the module docstring's own scope discipline.
    """
    criteria = criteria or {}
    rows = rank_company_matches(company_profiles, criteria=criteria)
    by_pk = {r['company'].pk: r for r in rows}
    return [by_pk[c.pk] for c in company_profiles if c.pk in by_pk]
