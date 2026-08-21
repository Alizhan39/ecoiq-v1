"""
EcoIQ Company Intelligence — Public Views.

/companies/           → directory with search + filters
/companies/<slug>/    → full public company profile
"""
import json

from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, JsonResponse, HttpResponse, HttpResponseForbidden
from django.contrib import messages
from django.views.decorators.http import require_POST

from core.unknown import clamp, mean_of_known

from companies.models import CompanyProfile, CompanyGuidanceVideo, MORAL_LABEL_CHOICES
from companies.scoring import get_path_to_100_actions
from companies.throttle import rate_limit, cache_response
from companies.improvement_data import get_improvement_pathway
from league.models import Company, SECTOR_CHOICES
from company_intelligence.models import ResearchWatchlistEntry


# ── Helpers ────────────────────────────────────────────────────────────────────

MORAL_DISPLAY = dict(MORAL_LABEL_CHOICES)

DISCLAIMER_FULL = (
    "This company profile is based on publicly available information and "
    "AI-assisted analysis. It has not been verified or endorsed by the company "
    "unless marked as Verified."
)
DISCLAIMER_LIGHT = (
    "EcoIQ scores are indicative and designed to support transparency, "
    "modernization, and responsible investment dialogue."
)
DISCLAIMER_FINANCIAL = (
    "EcoIQ provides environmental stewardship and sustainability-risk intelligence. "
    "It does not provide investment advice, financial recommendations or predictions "
    "of investment performance."
)


def _get_harm_signals(profile):
    """Return detailed harm signal breakdown for the intelligence panel."""
    signals = []

    # Pollution severity
    p = profile.pollution_level
    if p == 'severe':
        signals.append({
            'id': 'pollution', 'label': 'Pollution Severity',
            'status': 'critical', 'penalty': 15,
            'detail': 'Severe pollution classification — maximum penalty tier applies.',
        })
    elif p == 'high':
        signals.append({
            'id': 'pollution', 'label': 'Pollution Severity',
            'status': 'elevated', 'penalty': 8,
            'detail': 'High pollution classification — significant harm penalty applied.',
        })
    else:
        signals.append({
            'id': 'pollution', 'label': 'Pollution Severity',
            'status': 'clear', 'penalty': 0,
            'detail': f'Pollution level: {profile.get_pollution_level_display()} — no penalty.',
        })

    # Controversy risk
    #
    # `or 0` made an unknown score read as 0, which fell through to the else
    # branch and told the reader "within acceptable range" — a clean bill of
    # health for a company that had never been assessed. Unknown now says so.
    cr = clamp(profile.controversy_risk_score)
    if cr is None:
        signals.append({
            'id': 'controversy', 'label': 'Controversy Risk',
            'status': 'insufficient_evidence', 'penalty': 0,
            'detail': 'Controversy risk has not been assessed for this organisation.',
        })
    elif cr >= 70:
        signals.append({
            'id': 'controversy', 'label': 'Controversy Risk',
            'status': 'elevated', 'penalty': 5,
            'detail': f'Controversy risk score {cr:.0f}/100 — penalty applied.',
        })
    elif cr >= 50:
        signals.append({
            'id': 'controversy', 'label': 'Controversy Risk',
            'status': 'moderate', 'penalty': 0,
            'detail': f'Controversy risk score {cr:.0f}/100 — monitored.',
        })
    else:
        signals.append({
            'id': 'controversy', 'label': 'Controversy Risk',
            'status': 'clear', 'penalty': 0,
            'detail': f'Controversy risk score {cr:.0f}/100 — within acceptable range.',
        })

    # Transparency quality
    #
    # The most consequential of the three: `or 0` put an unknown score below the
    # 30 threshold, so an unassessed company was published with a "Transparency
    # Deficit — below minimum threshold" finding and a 5-point penalty.
    tr = clamp(profile.transparency_score_detail)
    if tr is None:
        signals.append({
            'id': 'transparency', 'label': 'Transparency Quality',
            'status': 'insufficient_evidence', 'penalty': 0,
            'detail': 'Disclosure quality has not been assessed for this organisation.',
        })
    elif tr < 30:
        signals.append({
            'id': 'transparency', 'label': 'Transparency Deficit',
            'status': 'elevated', 'penalty': 5,
            'detail': f'Transparency score {tr:.0f}/100 — below minimum threshold.',
        })
    elif tr < 50:
        signals.append({
            'id': 'transparency', 'label': 'Transparency Quality',
            'status': 'moderate', 'penalty': 0,
            'detail': f'Transparency score {tr:.0f}/100 — improvement recommended.',
        })
    else:
        signals.append({
            'id': 'transparency', 'label': 'Transparency Quality',
            'status': 'clear', 'penalty': 0,
            'detail': f'Transparency score {tr:.0f}/100 — meets standard.',
        })

    # Profit extraction
    #
    # `pb = ... or 50` was the falsy-trigger bug in its purest form: it rewrote a
    # genuine measured 0.0 public benefit to 50, which then failed the `< 50`
    # test — so the company with the worst possible public-benefit score was the
    # one guaranteed NOT to be flagged for it.
    pe = clamp(profile.profit_extraction_score)
    pb = clamp(profile.public_benefit_score)
    if pe is None:
        signals.append({
            'id': 'profit_extraction', 'label': 'Profit Distribution',
            'status': 'insufficient_evidence', 'penalty': 0,
            'detail': 'Profit distribution has not been assessed for this organisation.',
        })
    elif pe > 75 and pb is not None and pb < 50:
        signals.append({
            'id': 'profit_extraction', 'label': 'Profit Extraction',
            'status': 'elevated', 'penalty': 5,
            'detail': f'High profit extraction ({pe:.0f}) without proportionate public benefit ({pb:.0f}).',
        })
    elif pe > 60:
        signals.append({
            'id': 'profit_extraction', 'label': 'Profit Distribution',
            'status': 'moderate', 'penalty': 0,
            'detail': f'Elevated profit extraction indicator ({pe:.0f}) — monitored.',
        })
    else:
        signals.append({
            'id': 'profit_extraction', 'label': 'Profit Distribution',
            'status': 'clear', 'penalty': 0,
            'detail': f'Profit extraction indicator within range ({pe:.0f}/100).',
        })

    # High pollution + low modernization
    #
    # `or 50` here suppressed the flag for unknown modernization (50 >= 40) but
    # also rewrote a real 0.0 to 50, hiding the worst genuine transition gaps.
    mod = clamp(profile.modernization_score)
    if mod is None:
        signals.append({
            'id': 'transition_gap', 'label': 'Transition Readiness',
            'status': 'insufficient_evidence', 'penalty': 0,
            'detail': 'Modernization progress has not been assessed for this organisation.',
        })
    elif p in ('high', 'severe') and mod < 40:
        signals.append({
            'id': 'transition_gap', 'label': 'Transition Gap',
            'status': 'elevated', 'penalty': 3,
            'detail': f'High pollution with low modernization ({mod:.0f}/100) — transition urgency penalty.',
        })
    elif p in ('high', 'severe'):
        signals.append({
            'id': 'transition_gap', 'label': 'Transition Gap',
            'status': 'moderate', 'penalty': 0,
            'detail': f'Polluting sector — modernization progress {mod:.0f}/100.',
        })
    else:
        signals.append({
            'id': 'transition_gap', 'label': 'Transition Readiness',
            'status': 'clear', 'penalty': 0,
            'detail': f'Modernization score {mod:.0f}/100 — adequate.',
        })

    return signals


def _get_ai_confidence(profile):
    """
    0–100 indicator of data completeness and AI intelligence quality.
    Higher = more reliable analysis. Shown as 'Intelligence Quality' indicator.
    """
    score = 0

    # AI content completeness (40 pts)
    for field in ('ai_summary', 'ai_modernization_report', 'ai_investment_opportunity', 'ai_risk_notes'):
        val = getattr(profile, field, '')
        if val and len(val) > 80:
            score += 10

    # Source citations (20 pts)
    src_count = profile.cited_sources.count()
    score += min(src_count * 5, 20)

    # Score diversity — penalise if many fields are at default 50 (10 pts)
    check_fields = [
        'jobs_created_score', 'regional_development_score', 'waste_management_score',
        'energy_transition_score', 'transparency_score_detail', 'anti_corruption_score',
    ]
    # An UNKNOWN field is not evidence either, and counts the same as one parked
    # at the seeded default. Also guards against abs(None - 50.0) raising once
    # these columns become nullable in D4.
    def _is_not_evidence(field):
        v = getattr(profile, field, None)
        return v is None or abs(float(v) - 50.0) < 0.5

    default_count = sum(1 for f in check_fields if _is_not_evidence(f))
    score += max(0, 10 - default_count * 2)

    # Verification and public data (30 pts)
    if profile.is_verified:
        score += 30
    else:
        if profile.annual_report_url:
            score += 10
        if profile.sustainability_report_url:
            score += 8
        if profile.ai_recommendations:
            score += 7
        score += 5  # baseline

    return min(round(score), 100)


def _get_financing_eligibility(profile):
    """
    Indicative financing eligibility cards based on EcoIQ profile.
    All results are indicative only — not investment advice.
    """
    # Not a fallback site — these comparisons have no `or 50`, so nothing is
    # fabricated today. But every card here is a POSITIVE eligibility claim, and
    # once these columns become nullable (D4) a bare `s >= 70` would raise
    # TypeError on the public company page. Refusing up front is both the safe
    # answer and the truthful one: we cannot assert a company qualifies for
    # Green Bond finance on the strength of a score we do not have.
    s = clamp(profile.ecoiq_total_score)
    transparency = clamp(profile.transparency_score_detail)
    energy = clamp(profile.energy_transition_score)
    if s is None:
        return []

    items = []

    if s >= 70 and profile.pollution_level in ('low', 'medium'):
        items.append({
            'type': 'Green Bond',
            'institution': 'International Capital Markets',
            'status': 'eligible',
            'color': '#00e89a',
            'detail': 'Responsible Builder tier meets indicative Green Bond use-of-proceeds criteria.',
        })

    if s >= 60 and transparency is not None and transparency >= 50:
        items.append({
            'type': 'ESG Fund',
            'institution': 'ESG-Screened Portfolios',
            'status': 'eligible' if s >= 70 else 'partial',
            'color': '#58a6ff',
            'detail': 'Transparency and governance scores meet indicative ESG fund screening thresholds.',
        })

    if transparency is not None and transparency >= 50 and s >= 50:
        items.append({
            'type': 'IFC / EBRD',
            'institution': 'Multilateral Development Banks',
            'status': 'eligible' if s >= 65 else 'partial',
            'color': '#8b5cf6',
            'detail': 'Governance and transparency standards meet MDB indicative assessment criteria.',
        })

    if energy is not None and energy >= 60 and profile.pollution_level in ('low', 'medium'):
        items.append({
            'type': 'Climate Finance',
            'institution': 'Climate Bonds / GCF',
            'status': 'eligible' if s >= 65 else 'partial',
            'color': '#06b6d4',
            'detail': 'Energy transition progress meets indicative climate finance eligibility.',
        })

    if s < 55 and profile.pollution_level in ('high', 'severe'):
        items.append({
            'type': 'Just Transition',
            'institution': 'JETP / Transition Finance',
            'status': 'transition',
            'color': '#f4a261',
            'detail': 'Eligible for just transition finance mechanisms — requires improvement commitment.',
        })

    return items


def _get_institutional_signals(profile):
    """
    Compute 6 institutional intelligence signals for a company profile.
    Each signal: {label, value, level, description}
    level: 'good' | 'moderate' | 'elevated' | 'critical'

    Used to render the Institutional Signals strip on company profile pages.
    All outputs are indicative.
    """
    # Was a local `float(v or 0)` — the same defect as ethics and core scoring,
    # in a third copy. core.unknown is now the single authority.
    #
    # The shape of the bug here was the trailing `else:` on each signal. With
    # unknown arriving as 0, every unassessed company fell into the worst tier
    # and was published as 'High Risk', 'Early Stage', 'Limited' and 'Poor' —
    # four negative institutional claims generated purely by absence of data.
    signals = []

    def _tiered(label, value, tiers, unknown_value='Not assessed'):
        """
        Emit one signal, or an explicit not-assessed one when value is unknown.

        `tiers` is [(threshold, value, level), ...] highest first. The final
        tier is reached only by a KNOWN value below every threshold, so the
        worst label is now a finding rather than a default.
        """
        if value is None:
            signals.append({'label': label, 'value': unknown_value,
                            'level': 'insufficient_evidence'})
            return
        for threshold, tier_value, level in tiers:
            if value >= threshold:
                signals.append({'label': label, 'value': tier_value, 'level': level})
                return
        _, tier_value, level = tiers[-1]
        signals.append({'label': label, 'value': tier_value, 'level': level})

    # 1. Governance Risk — transparency + anti-corruption
    _tiered('Governance Risk',
            mean_of_known(profile.transparency_score_detail, profile.anti_corruption_score),
            [(68, 'Low Risk', 'good'), (50, 'Moderate', 'moderate'),
             (34, 'Elevated', 'elevated'), (0, 'High Risk', 'critical')])

    # 2. Transition Readiness — energy + future + modernization
    _tiered('Transition Readiness',
            mean_of_known(profile.energy_transition_score,
                          profile.future_readiness_score,
                          profile.modernization_score),
            [(68, 'Leading', 'good'), (52, 'Advancing', 'moderate'),
             (37, 'Developing', 'elevated'), (0, 'Early Stage', 'critical')])

    # 3. Financing Compatibility — overall score adjusted for pollution
    pol_adj = {'low': 0, 'medium': 4, 'high': 14, 'severe': 24}.get(profile.pollution_level, 0)
    total = clamp(profile.ecoiq_total_score)
    fin = None if total is None else max(0, total - pol_adj)
    _tiered('Financing Compatibility', fin,
            [(64, 'Strong', 'good'), (44, 'Eligible', 'moderate'),
             (28, 'Partial', 'elevated'), (0, 'Limited', 'critical')])

    # 4. Transparency Quality — transparency detail + audit
    _tiered('Transparency Quality',
            mean_of_known(profile.transparency_score_detail, profile.audit_quality_score),
            [(70, 'Institutional', 'good'), (54, 'Strong', 'moderate'),
             (38, 'Moderate', 'elevated'), (0, 'Poor', 'critical')])

    # 5. Industrial Complexity — driven by pollution level classification
    ic_map = {
        'severe': ('Critical',  'critical'),
        'high':   ('Complex',   'elevated'),
        'medium': ('Moderate',  'moderate'),
        'low':    ('Standard',  'good'),
    }
    ic_val, ic_level = ic_map.get(profile.pollution_level, ('Standard', 'good'))
    signals.append({'label': 'Industrial Complexity',      'value': ic_val,         'level': ic_level})

    # 6. Public Benefit Alignment — public_benefit_score
    _tiered('Public Benefit Alignment', clamp(profile.public_benefit_score),
            [(70, 'Exemplary', 'good'), (54, 'Aligned', 'moderate'),
             (38, 'Partial', 'elevated'), (0, 'Developing', 'critical')])

    return signals


def _get_confidence_label(ai_confidence: int, is_verified: bool) -> str:
    """
    Map an integer confidence score to a standardized confidence label class.
    Returns CSS class suffix: 'low' | 'medium' | 'high' | 'verified'
    """
    if is_verified:
        return 'verified'
    if ai_confidence >= 75:
        return 'high'
    if ai_confidence >= 45:
        return 'medium'
    return 'low'


# ── Company Directory ──────────────────────────────────────────────────────────

def directory(request):
    """
    /companies/ — searchable, filterable company directory.
    Shows all public CompanyProfile records with EcoIQ cards.
    """
    qs = CompanyProfile.objects.filter(
        status__in=('public', 'verified')
    ).select_related('company').order_by('-ecoiq_total_score')

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(company__name__icontains=q)

    # Filters
    sector    = request.GET.get('sector', '')
    country   = request.GET.get('country', '')
    label     = request.GET.get('label', '')
    verified  = request.GET.get('verified', '')
    funding   = request.GET.get('funding', '')
    pollution = request.GET.get('pollution', '')

    if sector:
        qs = qs.filter(company__sector=sector)
    if country:
        qs = qs.filter(company__country__icontains=country)
    if label:
        qs = qs.filter(moral_label=label)
    if verified == '1':
        qs = qs.filter(is_verified=True)
    if funding:
        qs = qs.filter(funding_status=funding)
    if pollution:
        qs = qs.filter(pollution_level=pollution)

    # Distinct countries for filter dropdown
    countries = (
        CompanyProfile.objects
        .filter(status__in=('public', 'verified'))
        .values_list('company__country', flat=True)
        .distinct()
        .order_by('company__country')
    )

    return render(request, 'companies/directory.html', {
        'profiles':       qs,
        'total_count':    CompanyProfile.objects.filter(status__in=('public','verified')).count(),
        'result_count':   qs.count(),
        'q':              q,
        'sector':         sector,
        'country':        country,
        'label':          label,
        'verified':       verified,
        'funding':        funding,
        'pollution':      pollution,
        'sector_choices': SECTOR_CHOICES,
        'moral_choices':  MORAL_LABEL_CHOICES,
        'countries':      countries,
        'disclaimer_light': DISCLAIMER_LIGHT,
    })


# ── Company Detail ─────────────────────────────────────────────────────────────

def company_detail(request, slug):
    """
    /companies/<slug>/ — full public EcoIQ company profile.
    """
    company = get_object_or_404(Company, slug=slug)
    profile = get_object_or_404(CompanyProfile, company=company,
                                status__in=('public', 'verified', 'draft'))

    # ── Public evidence gate (D1.5) ───────────────────────────────────────────
    # Fail closed. This page renders the composite score in seventeen places —
    # a counter, an arc, gauges, pillar cards, comparison bands, two inline
    # scripts, the meta description, the OpenGraph tags and schema.org
    # structured data. Gating each one individually would be seventeen chances
    # to miss one, and a number left in JSON-LD is still published even when the
    # visible one is hidden.
    #
    # So the decision is made once, here, and an organisation without evidence
    # gets a page that has no score in it at all rather than a page with the
    # score suppressed in seventeen places.
    #
    # The route, the profile and every stored value are untouched; only what is
    # rendered changes. Staff keep the full page — see the template.
    from companies.evidence import coverage_for, public_score_state

    score_state = public_score_state(profile)
    if not score_state.available and not request.user.is_staff:
        return render(request, 'companies/detail_evidence_pending.html', {
            'company': company,
            'profile': profile,
            'score_state': score_state,
            'coverage': coverage_for(profile),
        })

    # Score breakdown for display
    score_cards = [
        {
            'label':  'Public Benefit',
            'score':  profile.public_benefit_score,
            'weight': '25%',
            'icon':   '🌍',
            'desc':   'Employment quality, regional development, community investment, national value',
            'sub': [
                {'label': 'Employment Quality', 'val': profile.jobs_created_score},
                {'label': 'Regional Development', 'val': profile.regional_development_score},
                {'label': 'Infrastructure', 'val': profile.infrastructure_contribution_score},
                {'label': 'National Value', 'val': profile.national_value_score},
            ],
        },
        {
            'label':  'Environmental Stewardship',
            'score':  profile.environmental_responsibility_score,
            'weight': '25%',
            'icon':   '♻️',
            'desc':   'Pollution intensity, waste management, water stewardship, biodiversity',
            'sub': [
                {'label': 'Waste Management', 'val': profile.waste_management_score},
                {'label': 'Water Stewardship', 'val': profile.water_impact_score},
                {'label': 'Biodiversity', 'val': profile.biodiversity_impact_score},
            ],
        },
        {
            'label':  'Responsible Modernization',
            'score':  profile.modernization_score,
            'weight': '20%',
            'icon':   '⚡',
            'desc':   'Energy transition, digitalization, infrastructure upgrades, future readiness',
            'sub': [
                {'label': 'Energy Transition', 'val': profile.energy_transition_score},
                {'label': 'Digitalization', 'val': profile.digitalization_score},
                {'label': 'Infrastructure', 'val': profile.infrastructure_upgrade_score},
                {'label': 'Future Readiness', 'val': profile.future_readiness_score},
            ],
        },
        {
            'label':  'Transparent Governance',
            'score':  profile.transparency_anti_corruption_score,
            'weight': '15%',
            'icon':   '🔍',
            'desc':   'Reporting quality, audit standards, procurement transparency',
            'sub': [
                {'label': 'Reporting Quality', 'val': profile.transparency_score_detail},
                {'label': 'Audit Standards', 'val': profile.audit_quality_score},
                {'label': 'Procurement', 'val': profile.procurement_transparency_score},
            ],
        },
        {
            'label':  'Anti-Corruption',
            'score':  profile.anti_corruption_score,
            'weight': '10%',
            'icon':   '⚖️',
            'desc':   'Anti-corruption practices, ethical procurement, governance integrity',
            'sub': [
                {'label': 'AC Practices', 'val': profile.anti_corruption_score},
            ],
        },
        {
            'label':  'Ethical Alignment',
            'score':  profile.ethical_alignment_score,
            'weight': '5%',
            'icon':   '✦',
            'desc':   'Long-term ethical value creation, controversy management, stakeholder trust',
            'sub': [
                {'label': 'Controversy Control',
                 'val': None if profile.controversy_risk_score is None
                        else max(0, 100 - profile.controversy_risk_score)},
                {'label': 'Long-Term Value', 'val': profile.national_value_score},
            ],
        },
    ]

    # Path to 100%
    path_actions = get_path_to_100_actions(profile)

    # Guidance videos
    videos = CompanyGuidanceVideo.objects.filter(
        company=profile, status='published', visibility='public',
    ).order_by('-created_at')[:4]

    # Transition Engine integration
    roadmaps = []
    active_roadmap = None
    has_roadmap = False
    try:
        from transition.models import TransitionRoadmap
        roadmaps = list(company.roadmaps.order_by('-created_at')[:3])
        active_roadmap = roadmaps[0] if roadmaps else None
        has_roadmap = bool(roadmaps)
    except Exception:
        pass

    # Financing matches (from Transition Engine)
    financing_matches = []
    if active_roadmap:
        try:
            financing_matches = list(
                active_roadmap.financing_matches
                .select_related('opportunity')
                .order_by('-match_score')[:4]
            )
        except Exception:
            pass

    # AI briefing
    briefing = None
    try:
        from intelligence.models import ExecutiveBriefing
        briefing = ExecutiveBriefing.objects.filter(company=company).order_by('-created_at').first()
    except Exception:
        pass

    # Sources
    sources = profile.cited_sources.all()[:8]

    # Score evolution snapshots — chronological for Chart.js
    score_snapshots = list(profile.score_snapshots.order_by('date')[:8])
    import json as _json
    history_labels = _json.dumps([s.date.strftime('%b %Y') for s in score_snapshots])
    history_scores = _json.dumps([round(s.total_score, 1) for s in score_snapshots])

    # ── Intelligence layer ─────────────────────────────────────────────────────
    harm_signals       = _get_harm_signals(profile)
    ai_confidence      = _get_ai_confidence(profile)
    financing_eligibility = _get_financing_eligibility(profile)

    # Radar chart data (6 pillars, 0-100).
    #
    # An unassessed pillar is null, NOT zero. Chart.js skips a null point, so
    # the shape shows a gap where there is no evidence — which is the honest
    # picture. A zero would draw the polygon all the way to the centre and
    # read as "this company scored zero on governance".
    #
    # json.dumps, not str(): a Python None renders as `None` in a template and
    # is a syntax error in JavaScript. This list is injected with |safe.
    radar_scores = json.dumps([
        None if value is None else round(value, 1)
        for value in (
            profile.public_benefit_score,
            profile.environmental_responsibility_score,
            profile.modernization_score,
            profile.transparency_anti_corruption_score,
            profile.anti_corruption_score,
            profile.ethical_alignment_score,
        )
    ])

    # ── Ethical Intelligence layer (NEI / TSS / RVI) ───────────────────────────
    ethics_profile = None
    try:
        from ethics.scoring import get_or_compute
        ethics_profile = get_or_compute(profile)
    except Exception:
        pass

    # ── Financing Intelligence layer ────────────────────────────────────────────
    financing_profile       = None
    fin_matches             = []
    financing_eligible_count = 0
    financing_likely_count   = 0
    financing_total_count    = 0
    try:
        from financing.matching import get_or_compute as fin_compute
        financing_profile = fin_compute(profile)
        if financing_profile:
            qs = profile.financing_matches.select_related('opportunity').order_by('-match_score')
            financing_total_count    = qs.count()
            financing_eligible_count = qs.filter(match_tier='eligible').count()
            financing_likely_count   = qs.filter(match_tier='likely').count()
            fin_matches              = list(qs[:6])
    except Exception:
        pass

    # ── Improvement Pathway ─────────────────────────────────────────────────────
    improvement_pathway = get_improvement_pathway(profile)

    # ── Quranic Decision Filter (Decision Integrity) ────────────────────────────
    qdf_assessment = None
    try:
        from qdf.scoring import get_or_compute as qdf_compute
        qdf_assessment = qdf_compute(profile)
    except Exception:
        pass

    # ── Institutional Intelligence Signals ──────────────────────────────────────
    institutional_signals = _get_institutional_signals(profile)
    confidence_label      = _get_confidence_label(ai_confidence, profile.is_verified)

    # ── feat/company-halal-intelligence (PR 9) — Shariah screening + 114-KPI
    # stewardship alignment. Two distinct lenses, read-only on this GET view
    # (no state-changing GET actions) — see company_intelligence.services.
    from company_intelligence.services.kpi_engine import filter_rows, kpi_alignment_profile
    from company_intelligence.services.shariah_screening import latest_screen_for

    shariah_screen = latest_screen_for(profile)
    kpi_profile = kpi_alignment_profile(profile)
    kpi_filter = request.GET.get('kpi_filter', '')
    kpi_filtered_rows = filter_rows(kpi_profile['rows'], kpi_filter) if kpi_filter else kpi_profile['rows']
    controversies = list(profile.controversies.select_related('evidence').all())
    watchlist_entry = None
    if request.user.is_authenticated:
        watchlist_entry = profile.watchlist_entries.filter(user=request.user).first()

    # ── feat/company-evidence-ingestion (PR 10) — real source provenance,
    # data-origin honesty, freshness/staleness, per-metric financial
    # provenance. All read-only on this GET view, same discipline as above.
    from company_intelligence.services.data_origin import company_data_origin
    from company_intelligence.services.evidence_quality import company_evidence_quality_summary
    from company_intelligence.services.freshness import screening_freshness

    harvest_sources = list(profile.harvest_sources.select_related().all())
    data_origin = company_data_origin(profile)
    screening_freshness_info = screening_freshness(shariah_screen)
    evidence_quality_summary = company_evidence_quality_summary(profile)
    financial_fact_sources = (
        list(shariah_screen.financial_facts.metric_sources.select_related('evidence').all())
        if shariah_screen and shariah_screen.financial_facts else []
    )

    return render(request, 'companies/detail.html', {
        'company':               company,
        'profile':               profile,
        'score_cards':           score_cards,
        'path_actions':          path_actions,
        'videos':                videos,
        'roadmaps':              roadmaps,
        'active_roadmap':        active_roadmap,
        'has_roadmap':           has_roadmap,
        'briefing':              briefing,
        'sources':               sources,
        'disclaimer_full':       DISCLAIMER_FULL,
        'disclaimer_light':      DISCLAIMER_LIGHT,
        'moral_display':         profile.moral_label_display,
        # Score evolution
        'score_snapshots':       score_snapshots,
        'history_labels':        history_labels,
        'history_scores':        history_scores,
        # Intelligence layer
        'harm_signals':          harm_signals,
        'ai_confidence':         ai_confidence,
        'financing_eligibility': financing_eligibility,
        'radar_scores':          radar_scores,
        # Ethical Intelligence layer
        'ethics_profile':        ethics_profile,
        # Financing Intelligence layer
        'financing_profile':          financing_profile,
        'financing_matches':          fin_matches,
        'financing_eligible_count':   financing_eligible_count,
        'financing_likely_count':     financing_likely_count,
        'financing_total_count':      financing_total_count,
        # Improvement Pathway
        'improvement_pathway':        improvement_pathway,
        # Quranic Decision Filter
        'qdf_assessment':             qdf_assessment,
        # Institutional Intelligence layer
        'institutional_signals':      institutional_signals,
        'confidence_label':           confidence_label,
        # feat/company-halal-intelligence (PR 9) — kept explicitly separate
        # from qdf_assessment and every ecoiq_total_score/moral_label above:
        # neither lens here is ever combined with those existing scores.
        'shariah_screen':             shariah_screen,
        'kpi_profile':                kpi_profile,
        'kpi_filter':                 kpi_filter,
        'kpi_filtered_rows':          kpi_filtered_rows,
        'controversies':              controversies,
        'watchlist_entry':            watchlist_entry,
        'watchlist_statuses':         ResearchWatchlistEntry.STATUS_CHOICES,
        # feat/company-evidence-ingestion (PR 10)
        'harvest_sources':            harvest_sources,
        'data_origin':                data_origin,
        'screening_freshness':        screening_freshness_info,
        'evidence_quality_summary':   evidence_quality_summary,
        'financial_fact_sources':     financial_fact_sources,
    })


# ── PDF Report ─────────────────────────────────────────────────────────────────

def _tier_label_from_score(score: float) -> str:
    if score >= 85: return 'Regenerative Leader'
    if score >= 70: return 'Responsible Builder'
    if score >= 60: return 'Public-Benefit Oriented'
    if score >= 50: return 'Transitional Company'
    if score >= 30: return 'Profit-First Operator'
    return 'Extractive / Harmful'


def _tier_color_from_score(score: float) -> str:
    if score >= 85: return '#00e89a'
    if score >= 70: return '#58a6ff'
    if score >= 60: return '#8b5cf6'
    if score >= 50: return '#f4a261'
    if score >= 30: return '#e63946'
    return '#b91c1c'


@rate_limit('pdf_report')
@cache_response('pdf_report', timeout=600)
def company_pdf_report(request, slug):
    """
    GET /companies/<slug>/report.pdf
    Generates a 3-page A4 WeasyPrint PDF intelligence report.
    """
    import gc
    import weasyprint
    from datetime import date
    from django.template.loader import render_to_string
    from django.http import HttpResponse

    company = get_object_or_404(Company, slug=slug)
    profile = get_object_or_404(CompanyProfile, company=company,
                                status__in=('public', 'verified', 'draft'))

    # ── Public evidence gate (D1.5) ───────────────────────────────────────────
    # A downloadable PDF is the most quotable artefact EcoIQ produces: it leaves
    # the site, gets forwarded, and carries no context about when it was
    # generated or on what basis. Gating the HTML page while still emitting the
    # same scores as a document would defeat the containment entirely.
    #
    # 404 rather than a stub PDF: there is no report to give, and rendering an
    # empty one through WeasyPrint would spend the memory this route is already
    # rate-limited for.
    from companies.evidence import public_score_state

    if not public_score_state(profile).available and not request.user.is_staff:
        raise Http404('No published assessment for this organisation.')

    # Behind the D1.5 gate above, so an unpublishable score never reaches here;
    # the guard is belt-and-braces against a future caller that forgets it.
    score = clamp(profile.ecoiq_total_score)
    if score is None:
        raise Http404('No published assessment for this organisation.')

    # Score breakdown cards (reuse the same structure as company_detail)
    score_cards = [
        {
            'label':  'Public Benefit',
            'score':  profile.public_benefit_score,
            'weight': '25%',
            'icon':   '🌍',
            'desc':   'Employment quality, regional development, community investment, national value',
            'sub': [
                {'label': 'Employment Quality',   'val': profile.jobs_created_score},
                {'label': 'Regional Development', 'val': profile.regional_development_score},
                {'label': 'Infrastructure',       'val': profile.infrastructure_contribution_score},
                {'label': 'National Value',       'val': profile.national_value_score},
            ],
        },
        {
            'label':  'Environmental Stewardship',
            'score':  profile.environmental_responsibility_score,
            'weight': '25%',
            'icon':   '♻️',
            'desc':   'Pollution intensity, waste management, water stewardship, biodiversity',
            'sub': [
                {'label': 'Waste Management', 'val': profile.waste_management_score},
                {'label': 'Water Stewardship', 'val': profile.water_impact_score},
                {'label': 'Biodiversity',      'val': profile.biodiversity_impact_score},
            ],
        },
        {
            'label':  'Responsible Modernization',
            'score':  profile.modernization_score,
            'weight': '20%',
            'icon':   '⚡',
            'desc':   'Energy transition, digitalization, infrastructure upgrades, future readiness',
            'sub': [
                {'label': 'Energy Transition', 'val': profile.energy_transition_score},
                {'label': 'Digitalization',    'val': profile.digitalization_score},
                {'label': 'Infrastructure',    'val': profile.infrastructure_upgrade_score},
                {'label': 'Future Readiness',  'val': profile.future_readiness_score},
            ],
        },
        {
            'label':  'Transparent Governance',
            'score':  profile.transparency_anti_corruption_score,
            'weight': '15%',
            'icon':   '🔍',
            'desc':   'Reporting quality, audit standards, procurement transparency',
            'sub': [
                {'label': 'Reporting Quality', 'val': profile.transparency_score_detail},
                {'label': 'Audit Standards',   'val': profile.audit_quality_score},
                {'label': 'Procurement',       'val': profile.procurement_transparency_score},
            ],
        },
        {
            'label':  'Anti-Corruption',
            'score':  profile.anti_corruption_score,
            'weight': '10%',
            'icon':   '⚖️',
            'desc':   'Anti-corruption practices, ethical procurement, governance integrity',
            'sub': [
                {'label': 'AC Practices', 'val': profile.anti_corruption_score},
            ],
        },
        {
            'label':  'Ethical Alignment',
            'score':  profile.ethical_alignment_score,
            'weight': '5%',
            'icon':   '✦',
            'desc':   'Long-term ethical value creation, controversy management, stakeholder trust',
            'sub': [
                {'label': 'Ethical Alignment', 'val': profile.ethical_alignment_score},
            ],
        },
    ]

    # Score evolution snapshots
    score_snapshots = list(profile.score_snapshots.order_by('date')[:8])

    # Intelligence signals
    harm_signals  = _get_harm_signals(profile)
    ai_confidence = _get_ai_confidence(profile)

    # Financing matches
    fin_matches = []
    try:
        qs = profile.financing_matches.select_related('opportunity').order_by('-match_score')
        fin_matches = list(qs[:6])
    except Exception:
        pass

    # Sources
    sources = profile.cited_sources.all()[:8]

    # Executive briefing for AI summary
    briefing = None
    try:
        from intelligence.models import ExecutiveBriefing
        briefing = ExecutiveBriefing.objects.filter(company=company).order_by('-created_at').first()
    except Exception:
        pass

    context = {
        'company':          company,
        'profile':          profile,
        'score_cards':      score_cards,
        'score_snapshots':  score_snapshots,
        'harm_signals':     harm_signals,
        'ai_confidence':    ai_confidence,
        'financing_matches': fin_matches,
        'sources':          sources,
        'briefing':         briefing,
        'tier_label':       _tier_label_from_score(score),
        'tier_color':       _tier_color_from_score(score),
        'report_date':      date.today(),
    }

    base_url  = request.build_absolute_uri('/')
    html_str  = render_to_string('companies/report_pdf.html', context, request=request)
    # Explicit del + gc.collect() after write_pdf():
    # WeasyPrint holds a large internal tree (HTML→CSS layout boxes, cairocffi
    # surface objects). On 512 MB RAM this tree can be 60–100 MB.  Python's
    # refcount alone won't free it before the next request arrives on a busy server.
    _html_doc = weasyprint.HTML(string=html_str, base_url=base_url)
    try:
        pdf_bytes = _html_doc.write_pdf()
    finally:
        del _html_doc
        gc.collect()

    filename = f"ecoiq-report-{company.slug}.pdf"
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ── ML Insights endpoint ───────────────────────────────────────────────────────

@rate_limit('ml_insights', json=True)
@cache_response('ml_insights', timeout=300)
def company_ml_insights(request, slug):
    """
    JSON endpoint: /companies/<slug>/ml-insights.json

    Returns ML scoring, anomaly detection, clustering, and 12m prediction
    for a single company. Runs on-demand using saved model files; returns
    graceful error payload if models aren't trained yet.
    """
    company = get_object_or_404(
        __import__('league.models', fromlist=['Company']).Company,
        slug=slug,
    )

    payload: dict = {
        'company': company.name,
        'slug':    slug,
        'scoring':    None,
        'anomaly':    None,
        'cluster':    None,
        'prediction': None,
        'error':      None,
    }

    # ── Scoring ──────────────────────────────────────────────────────────
    try:
        from ml.scoring_model import EcoIQScoringModel
        scorer = EcoIQScoringModel()
        result = scorer.predict_company(company)
        if result:
            payload['scoring'] = result
    except Exception as exc:
        payload['error'] = f'scoring: {exc}'

    # ── Anomaly ──────────────────────────────────────────────────────────
    try:
        from ml.anomaly_detection import AnomalyDetector
        detector = AnomalyDetector()
        result   = detector.score_company(company)
        if result:
            payload['anomaly'] = result
    except Exception as exc:
        if not payload['error']:
            payload['error'] = f'anomaly: {exc}'

    # ── Clustering ────────────────────────────────────────────────────────
    try:
        from ml.clustering import CompanyClusterer
        clusterer = CompanyClusterer()
        result    = clusterer.assign_company(company)
        if result:
            payload['cluster'] = result
    except Exception as exc:
        if not payload['error']:
            payload['error'] = f'clustering: {exc}'

    # ── 12-month prediction ───────────────────────────────────────────────
    try:
        from ml.prediction import predict_12m
        pred = predict_12m(company)
        current = clamp(company.ecoiq_score)
        if pred is not None:
            payload['prediction'] = {
                'score_12m': round(pred, 1),
                # A delta is a comparison. Without a current score there is
                # nothing to compare against, so it is null rather than a
                # difference measured from an invented zero.
                'delta': None if current is None else round(pred - current, 1),
            }
    except Exception as exc:
        if not payload['error']:
            payload['error'] = f'prediction: {exc}'

    return JsonResponse(payload)


# ── Sector display labels ──────────────────────────────────────────────────────
_SECTOR_DISPLAY = {
    'oil_gas':     'Oil & Gas',
    'energy':      'Energy & Power',
    'mining':      'Mining & Metals',
    'metallurgy':  'Steel & Metallurgy',
    'chemical':    'Chemicals',
    'transport':   'Transport & Logistics',
    'agriculture': 'Agriculture',
    'other':       'Finance & Other',
}

# ── Sector PDF Report ──────────────────────────────────────────────────────────

@rate_limit('sector_report')
@cache_response('sector_report', timeout=600)
def sector_pdf_report(request, sector):
    """
    GET /companies/reports/sector/<sector>/

    Multi-chart Bloomberg-style PDF:
      - Bar chart: company rankings
      - Histogram: score distribution + stats box
      - Pie chart: pollution profile

    Free preview: top 5 only. Staff / Analyst plan: top 25.
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    import numpy as np
    from io import BytesIO
    from django.http import HttpResponse

    # ── Data ────────────────────────────────────────────────────────────────
    qs = CompanyProfile.objects.filter(
        company__sector=sector
    ).select_related('company').order_by('-ecoiq_total_score')

    if not qs.exists():
        return HttpResponse(f'No companies in sector: {sector}', status=404)

    # Preview gate: staff see full 25; everyone else sees top 5
    is_staff_or_analyst = (
        request.user.is_authenticated and request.user.is_staff
    )
    if is_staff_or_analyst:
        profiles_data = list(qs[:25])
        is_preview = False
    else:
        profiles_data = list(qs[:5])
        is_preview = True

    sector_label = _SECTOR_DISPLAY.get(sector, sector.replace('_', ' ').title())
    # Companies without a score are EXCLUDED from the chart rather than plotted
    # as a zero-length bar. A bar at 0 is a visual claim that the company scored
    # worst in its sector; an absent bar claims nothing.
    plotted = [p for p in profiles_data if p.ecoiq_total_score is not None]
    names   = [p.company.name[:22] for p in plotted]
    scores  = [float(p.ecoiq_total_score) for p in plotted]
    # `or 'medium'` invented a pollution classification for companies nobody
    # had classified, and coloured a bar with it. Unknown now gets its own
    # neutral colour rather than borrowing a real category's.
    poll_levels = [p.pollution_level or None for p in plotted]

    def _bar_color(s):
        if s >= 70: return '#10b981'
        if s >= 50: return '#fbbf24'
        return '#f87171'

    colors = [_bar_color(s) for s in scores]

    # ── Figure & Grid ────────────────────────────────────────────────────────
    BG, BG2 = '#070b0f', '#0d1117'
    EMERALD, AMBER, RED = '#10b981', '#fbbf24', '#f87171'
    GREY, WHITE, MONO = '#475569', '#e2e8f0', 'DejaVu Sans Mono'

    plt.style.use('dark_background')
    fig = plt.figure(figsize=(16, 10), facecolor=BG)
    fig.patch.set_facecolor(BG)

    gs = gridspec.GridSpec(
        2, 3, figure=fig,
        hspace=0.50, wspace=0.35,
        top=0.88, bottom=0.08, left=0.06, right=0.97,
    )

    # ── Header ──────────────────────────────────────────────────────────────
    fig.text(0.06, 0.95,
             f'EcoIQ — {sector_label} Sector Intelligence',
             fontsize=15, color=WHITE, fontweight='light',
             fontfamily='DejaVu Sans')
    fig.text(0.06, 0.91,
             f'{len(profiles_data)} companies · 2026 · ecoiq.uk',
             fontsize=9, color=GREY, fontfamily=MONO)
    fig.text(0.97, 0.91,
             'Indicative only · Not investment advice',
             fontsize=7, color=GREY, ha='right', fontfamily=MONO)
    if is_preview:
        fig.text(0.97, 0.95,
                 '⚠ PREVIEW — Top 5 only · Contact alizhan@ecoiq.uk for full report',
                 fontsize=8, color=AMBER, ha='right', fontfamily=MONO)

    # Accent line
    fig.add_artist(plt.Line2D(
        [0.06, 0.97], [0.895, 0.895],
        transform=fig.transFigure,
        color=EMERALD, linewidth=0.8, alpha=0.5,
    ))

    # ── PLOT 1: Rankings bar chart ──────────────────────────────────────────
    ax1 = fig.add_subplot(gs[:, 0:2])
    ax1.set_facecolor(BG2)

    bars = ax1.barh(range(len(names)), scores, color=colors, height=0.65, alpha=0.9)

    for bar, score in zip(bars, scores):
        ax1.text(score + 0.8, bar.get_y() + bar.get_height() / 2,
                 f'{score:.1f}', va='center', ha='left',
                 fontsize=8, color=WHITE, fontfamily=MONO)

    # No scores means no average. Drawing one at 50 put a labelled 'avg 50.0'
    # line on a chart of nothing — an invented sector benchmark.
    if scores:
        avg = float(np.mean(scores))
        ax1.axvline(x=avg, color=EMERALD, linestyle='--', alpha=0.6, linewidth=1)
        ax1.text(avg + 0.5, len(names) - 0.5, f'avg {avg:.1f}',
                 fontsize=7, color=EMERALD, fontfamily=MONO)

    # Tier zone lines
    for threshold, col in [(85, EMERALD), (70, '#38bdf8'), (55, AMBER), (40, '#f97316')]:
        ax1.axvline(x=threshold, color=col, linestyle=':', alpha=0.22, linewidth=0.7)

    ax1.set_yticks(range(len(names)))
    ax1.set_yticklabels(names, fontsize=8.5, fontfamily='DejaVu Sans', color=WHITE)
    ax1.set_xlabel('EcoIQ Score', fontsize=9, color=GREY, fontfamily=MONO)
    ax1.set_xlim(0, 105)
    ax1.tick_params(colors=GREY, labelsize=8)
    ax1.invert_yaxis()
    for spine in ax1.spines.values():
        spine.set_color('#1e293b')
    ax1.set_title(f'{sector_label} Rankings',
                  fontsize=11, color=WHITE, fontfamily='DejaVu Sans',
                  pad=12, fontweight='light', loc='left')

    # ── PLOT 2: Score distribution histogram ─────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 2])
    ax2.set_facecolor(BG2)

    ax2.hist(scores, bins=min(8, max(2, len(scores))),
             color=EMERALD, alpha=0.7, edgecolor=BG, linewidth=0.5)
    ax2.axvline(avg, color=AMBER, linestyle='--', linewidth=1, alpha=0.8)
    ax2.set_title('Distribution', fontsize=9, color=WHITE, loc='left',
                  fontfamily='DejaVu Sans', fontweight='light')
    ax2.set_xlabel('Score', fontsize=8, color=GREY, fontfamily=MONO)
    ax2.set_ylabel('Companies', fontsize=8, color=GREY, fontfamily=MONO)
    ax2.tick_params(colors=GREY, labelsize=7)
    for spine in ax2.spines.values():
        spine.set_color('#1e293b')

    stats_txt = (
        f'n   = {len(scores)}\n'
        f'avg = {np.mean(scores):.1f}\n'
        f'med = {float(np.median(scores)):.1f}\n'
        f'std = {float(np.std(scores)):.1f}\n'
        f'min = {min(scores):.1f}\n'
        f'max = {max(scores):.1f}'
    )
    ax2.text(0.97, 0.97, stats_txt, transform=ax2.transAxes,
             fontsize=7.5, color='#94a3b8', fontfamily=MONO,
             va='top', ha='right',
             bbox=dict(boxstyle='round', facecolor=BG, edgecolor='#1e293b', alpha=0.9))

    # ── PLOT 3: Pollution profile pie ────────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 2])
    ax3.set_facecolor(BG2)

    poll_count = {'low': 0, 'medium': 0, 'high': 0, 'severe': 0}
    for lvl in poll_levels:
        if lvl in poll_count:
            poll_count[lvl] += 1
    pie_labels = [k.title() for k, v in poll_count.items() if v > 0]
    pie_sizes  = [v for v in poll_count.values() if v > 0]
    pie_colors = {'Low': EMERALD, 'Medium': AMBER, 'High': '#f97316', 'Severe': RED}
    clrs = [pie_colors.get(l, GREY) for l in pie_labels]

    if pie_sizes:
        wedges, texts, autotexts = ax3.pie(
            pie_sizes, labels=pie_labels, colors=clrs,
            autopct='%1.0f%%', startangle=90,
            textprops={'fontsize': 7.5, 'color': WHITE, 'fontfamily': MONO},
            wedgeprops={'linewidth': 0.5, 'edgecolor': BG},
        )
        for at in autotexts:
            at.set_color(BG)
            at.set_fontsize(7)

    ax3.set_title('Pollution Profile', fontsize=9, color=WHITE, loc='left',
                  fontfamily='DejaVu Sans', fontweight='light')

    # ── Output ──────────────────────────────────────────────────────────────
    buf = BytesIO()
    fig.savefig(buf, format='pdf', facecolor=BG, dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)

    fname = f'ecoiq-{sector}-intelligence-report-2026.pdf'
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{fname}"'
    return response


# ── Report Index ───────────────────────────────────────────────────────────────

def report_index(request):
    """
    GET /companies/reports/
    Returns JSON list of all sectors with available PDF reports.
    """
    from league.models import Company as LeagueCompany
    from django.db.models import Avg, Count

    sector_rows = (
        LeagueCompany.objects
        .filter(profile__isnull=False)
        .values('sector')
        .annotate(count=Count('id'), avg=Avg('profile__ecoiq_total_score'))
        .order_by('-count')
    )

    sector_data = []
    for row in sector_rows:
        s = row['sector'] or 'other'
        sector_data.append({
            'slug':      s,
            'label':     _SECTOR_DISPLAY.get(s, s.replace('_', ' ').title()),
            'count':     row['count'],
            # Avg() returns None for a group with no scored members. Reporting
            # that as 0.0 would publish a sector average nobody computed.
            'avg_score': None if row['avg'] is None else round(float(row['avg']), 1),
            'pdf_url':   f'/companies/reports/sector/{s}/',
        })

    return JsonResponse({'sectors': sector_data, 'total': len(sector_data)})


# ── Verified Certificate ───────────────────────────────────────────────────────

@rate_limit('certificate')
@cache_response('certificate', timeout=600)
def generate_certificate(request, slug):
    """
    GET /companies/<slug>/certificate/
    Generate an EcoIQ Verified Intelligence Certificate for a verified company.

    Returns an HTML page suitable for printing / PDF-saving.
    For verified companies only.
    """
    import uuid
    from datetime import datetime

    profile  = get_object_or_404(CompanyProfile, company__slug=slug)
    company  = profile.company

    if not profile.is_verified:
        return HttpResponse(
            '<h2 style="font-family:sans-serif;color:#475569;padding:2rem">'
            'Certificate not available — company profile has not been verified.<br>'
            '<small>Contact <a href="mailto:alizhan@ecoiq.uk">alizhan@ecoiq.uk</a>'
            ' to request verification.</small></h2>',
            status=403,
        )

    cert_id  = f'ECOIQ-{slug[:6].upper()}-{uuid.uuid4().hex[:8].upper()}'
    issued   = datetime.now().strftime('%d %B %Y')
    score    = clamp(profile.ecoiq_total_score)
    if score is None:
        return HttpResponse(
            '<h2 style="font-family:sans-serif;color:#475569;padding:2rem">'
            'Certificate not available — no published assessment for this '
            'organisation.</h2>',
            status=404,
        )
    tier     = profile.moral_label_display
    color    = profile.moral_label_color

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>EcoIQ Certificate — {company.name}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700;900&display=swap');
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Inter',sans-serif;background:#070b0f;color:#e2e8f0;
        min-height:100vh;display:flex;align-items:center;justify-content:center;padding:2rem}}
  .cert{{border:1.5px solid #10b981;border-radius:16px;padding:3rem 3.5rem;
         max-width:680px;width:100%;background:linear-gradient(135deg,#080e1a,#0b1628);
         box-shadow:0 0 80px rgba(16,185,129,.08)}}
  .logo{{font-size:.8rem;color:#475569;margin-bottom:2rem;letter-spacing:.05em;
         text-transform:uppercase}}
  .cert-title{{font-size:1.6rem;font-weight:300;color:#10b981;margin-bottom:.4rem}}
  .company-name{{font-size:1.25rem;font-weight:700;color:#e2e8f0;margin-bottom:1.5rem}}
  .score-big{{font-size:5rem;font-weight:200;color:#10b981;line-height:1;
              font-variant-numeric:tabular-nums}}
  .score-sub{{font-size:.8rem;color:#475569;margin-top:.25rem;
              text-transform:uppercase;letter-spacing:.1em}}
  .tier-label{{font-size:.9rem;font-weight:700;margin-top:1rem;color:{color}}}
  .meta{{font-size:.75rem;color:#475569;margin-top:.5rem}}
  .divider{{border:none;border-top:1px solid #1e293b;margin:2rem 0}}
  .cert-id{{font-family:'Courier New',monospace;font-size:.75rem;color:#475569;
            line-height:1.9}}
  .cert-id strong{{color:#64748b}}
  .verify-note{{font-size:.7rem;color:#334155;margin-top:.8rem}}
  @media print{{body{{background:#fff;color:#000}}
    .cert{{border-color:#000;background:#fff;box-shadow:none}}
    .score-big{{color:#000}}.cert-title{{color:#000}}}}
</style>
</head>
<body>
<div class="cert">
  <div class="logo">EcoIQ Intelligence Platform · ecoiq.uk</div>
  <div class="cert-title">Certificate of Ethical Intelligence</div>
  <div class="company-name">{company.name}</div>
  <div class="score-big">{score:.1f}</div>
  <div class="score-sub">EcoIQ Score / 100</div>
  <div class="tier-label">{tier} · {company.get_sector_display() if hasattr(company,'get_sector_display') else company.sector}</div>
  <div class="meta">{company.country}</div>
  <hr class="divider">
  <div class="cert-id">
    <strong>Certificate ID:</strong>  {cert_id}<br>
    <strong>Issued:</strong>          {issued}<br>
    <strong>Verify at:</strong>       ecoiq.uk/verify/{cert_id}<br>
    <strong>Issuing entity:</strong>  Stoke Share Ltd · London, UK<br>
    <strong>Standard:</strong>        EcoIQ Ethical Intelligence Framework v1.0
  </div>
  <div class="verify-note">
    This certificate is indicative. Scores are AI-assisted from publicly available sources.
    Actual eligibility for financing or procurement requires independent due diligence.
  </div>
</div>
</body>
</html>"""

    return HttpResponse(html, content_type='text/html; charset=utf-8')


def company_stock_profile(request, slug):
    """
    /companies/<slug>/stock/ — EcoIQ stock-market profile: market data,
    a secondary TradingView chart link, and the EcoIQ Investment Relevance
    Report. Private companies / companies with no ticker get a friendly
    explanation instead of fabricated market data.
    """
    company = get_object_or_404(Company, slug=slug)
    profile = CompanyProfile.objects.filter(
        company=company, status__in=('public', 'verified', 'draft'),
    ).first()

    is_staff = request.user.is_authenticated and request.user.is_staff

    report = None
    report_history = []
    if profile is not None:
        reports_qs = profile.investment_reports.order_by('-version')
        if is_staff:
            report = reports_qs.first()
            report_history = list(reports_qs[:10])
        else:
            report = reports_qs.filter(status='published').first()

    return render(request, 'companies/stock_profile.html', {
        'company':              company,
        'profile':              profile,
        'report':               report,
        'report_history':       report_history,
        'is_staff':             is_staff,
        'disclaimer_financial': DISCLAIMER_FINANCIAL,
    })


@require_POST
def generate_investment_report(request, slug):
    """
    POST /companies/<slug>/stock/generate/ — staff/analyst-only. Generates a
    new draft version of the Investment Relevance Report; never overwrites
    a prior version. Regenerating is the same action — it just creates the
    next version.
    """
    if not (request.user.is_authenticated and request.user.is_staff):
        return HttpResponseForbidden('Only staff/analyst accounts can generate EcoIQ reports.')

    company = get_object_or_404(Company, slug=slug)
    profile = get_object_or_404(CompanyProfile, company=company)

    from companies.investment_report import generate_investment_relevance_report

    try:
        report = generate_investment_relevance_report(profile, user=request.user)
        if report.prohibited_language_flags:
            messages.warning(
                request,
                f'Report v{report.version} generated as draft, but flagged '
                f'{len(report.prohibited_language_flags)} prohibited-language finding(s) — '
                'it cannot be published until this is resolved (regenerate, or edit in admin).',
            )
        else:
            messages.success(request, f'Investment Relevance Report v{report.version} generated as draft.')
    except RuntimeError as exc:
        messages.error(request, f'Could not generate report: {exc}')

    return redirect('companies:stock', slug=slug)


@require_POST
def set_investment_report_status(request, slug, report_id):
    """
    POST /companies/<slug>/stock/<report_id>/status/ — staff-only. Moves a
    report through draft -> reviewed -> published. A report can never be
    published while it carries prohibited-language flags (mirrors the
    human-approval-before-publish pattern used elsewhere in EcoIQ for
    public-facing AI content).
    """
    if not (request.user.is_authenticated and request.user.is_staff):
        return HttpResponseForbidden('Only staff accounts can change report status.')

    from django.utils import timezone
    from companies.models import InvestmentRelevanceReport

    company = get_object_or_404(Company, slug=slug)
    report = get_object_or_404(InvestmentRelevanceReport, pk=report_id, company__company=company)
    action = request.POST.get('action')

    if action == 'mark_reviewed':
        report.status = 'reviewed'
        report.reviewed_by = request.user
        report.reviewed_at = timezone.now()
        report.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
        messages.success(request, f'Report v{report.version} marked reviewed.')
    elif action == 'publish':
        if not report.is_publishable:
            messages.error(request, f'Report v{report.version} cannot be published — it has prohibited-language flags.')
        else:
            report.status = 'published'
            if not report.reviewed_by:
                report.reviewed_by = request.user
                report.reviewed_at = timezone.now()
            report.published_at = timezone.now()
            report.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'published_at'])
            messages.success(request, f'Report v{report.version} published.')
    elif action == 'revert_to_draft':
        report.status = 'draft'
        report.published_at = None
        report.save(update_fields=['status', 'published_at'])
        messages.success(request, f'Report v{report.version} reverted to draft.')
    else:
        messages.error(request, 'Unknown action.')

    return redirect('companies:stock', slug=slug)
