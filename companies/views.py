"""
EcoIQ Company Intelligence — Public Views.

/companies/           → directory with search + filters
/companies/<slug>/    → full public company profile
"""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse

from companies.models import CompanyProfile, CompanyGuidanceVideo, MORAL_LABEL_CHOICES
from companies.scoring import get_path_to_100_actions
from companies.improvement_data import get_improvement_pathway
from league.models import Company, SECTOR_CHOICES


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
    cr = profile.controversy_risk_score or 0
    if cr >= 70:
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
    tr = profile.transparency_score_detail or 0
    if tr < 30:
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
    pe = profile.profit_extraction_score or 0
    pb = profile.public_benefit_score or 50
    if pe > 75 and pb < 50:
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
    mod = profile.modernization_score or 50
    if p in ('high', 'severe') and mod < 40:
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
    default_count = sum(1 for f in check_fields if abs(getattr(profile, f, 50) - 50.0) < 0.5)
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
    s = profile.ecoiq_total_score
    items = []

    if s >= 70 and profile.pollution_level in ('low', 'medium'):
        items.append({
            'type': 'Green Bond',
            'institution': 'International Capital Markets',
            'status': 'eligible',
            'color': '#00e89a',
            'detail': 'Responsible Builder tier meets indicative Green Bond use-of-proceeds criteria.',
        })

    if s >= 60 and profile.transparency_score_detail >= 50:
        items.append({
            'type': 'ESG Fund',
            'institution': 'ESG-Screened Portfolios',
            'status': 'eligible' if s >= 70 else 'partial',
            'color': '#58a6ff',
            'detail': 'Transparency and governance scores meet indicative ESG fund screening thresholds.',
        })

    if profile.transparency_score_detail >= 50 and s >= 50:
        items.append({
            'type': 'IFC / EBRD',
            'institution': 'Multilateral Development Banks',
            'status': 'eligible' if s >= 65 else 'partial',
            'color': '#8b5cf6',
            'detail': 'Governance and transparency standards meet MDB indicative assessment criteria.',
        })

    if profile.energy_transition_score >= 60 and profile.pollution_level in ('low', 'medium'):
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
    def _clamp(v): return max(0.0, min(100.0, float(v or 0)))

    signals = []

    # 1. Governance Risk — transparency + anti-corruption
    gov = (_clamp(profile.transparency_score_detail) + _clamp(profile.anti_corruption_score)) / 2
    if gov >= 68:
        signals.append({'label': 'Governance Risk',        'value': 'Low Risk',    'level': 'good'})
    elif gov >= 50:
        signals.append({'label': 'Governance Risk',        'value': 'Moderate',    'level': 'moderate'})
    elif gov >= 34:
        signals.append({'label': 'Governance Risk',        'value': 'Elevated',    'level': 'elevated'})
    else:
        signals.append({'label': 'Governance Risk',        'value': 'High Risk',   'level': 'critical'})

    # 2. Transition Readiness — energy + future + modernization
    trans = (_clamp(profile.energy_transition_score)
             + _clamp(profile.future_readiness_score)
             + _clamp(profile.modernization_score)) / 3
    if trans >= 68:
        signals.append({'label': 'Transition Readiness',   'value': 'Leading',     'level': 'good'})
    elif trans >= 52:
        signals.append({'label': 'Transition Readiness',   'value': 'Advancing',   'level': 'moderate'})
    elif trans >= 37:
        signals.append({'label': 'Transition Readiness',   'value': 'Developing',  'level': 'elevated'})
    else:
        signals.append({'label': 'Transition Readiness',   'value': 'Early Stage', 'level': 'critical'})

    # 3. Financing Compatibility — overall score adjusted for pollution
    pol_adj = {'low': 0, 'medium': 4, 'high': 14, 'severe': 24}.get(profile.pollution_level, 0)
    fin = max(0, _clamp(profile.ecoiq_total_score) - pol_adj)
    if fin >= 64:
        signals.append({'label': 'Financing Compatibility', 'value': 'Strong',     'level': 'good'})
    elif fin >= 44:
        signals.append({'label': 'Financing Compatibility', 'value': 'Eligible',   'level': 'moderate'})
    elif fin >= 28:
        signals.append({'label': 'Financing Compatibility', 'value': 'Partial',    'level': 'elevated'})
    else:
        signals.append({'label': 'Financing Compatibility', 'value': 'Limited',    'level': 'critical'})

    # 4. Transparency Quality — transparency detail + audit
    transp = (_clamp(profile.transparency_score_detail) + _clamp(profile.audit_quality_score)) / 2
    if transp >= 70:
        signals.append({'label': 'Transparency Quality',   'value': 'Institutional','level': 'good'})
    elif transp >= 54:
        signals.append({'label': 'Transparency Quality',   'value': 'Strong',      'level': 'moderate'})
    elif transp >= 38:
        signals.append({'label': 'Transparency Quality',   'value': 'Moderate',    'level': 'elevated'})
    else:
        signals.append({'label': 'Transparency Quality',   'value': 'Poor',        'level': 'critical'})

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
    pb = _clamp(profile.public_benefit_score)
    if pb >= 70:
        signals.append({'label': 'Public Benefit Alignment','value': 'Exemplary',  'level': 'good'})
    elif pb >= 54:
        signals.append({'label': 'Public Benefit Alignment','value': 'Aligned',    'level': 'moderate'})
    elif pb >= 38:
        signals.append({'label': 'Public Benefit Alignment','value': 'Partial',    'level': 'elevated'})
    else:
        signals.append({'label': 'Public Benefit Alignment','value': 'Developing', 'level': 'critical'})

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
                {'label': 'Controversy Control', 'val': max(0, 100 - profile.controversy_risk_score)},
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

    # Radar chart data (6 pillars, 0-100)
    radar_scores = [
        round(profile.public_benefit_score, 1),
        round(profile.environmental_responsibility_score, 1),
        round(profile.modernization_score, 1),
        round(profile.transparency_anti_corruption_score, 1),
        round(profile.anti_corruption_score, 1),
        round(profile.ethical_alignment_score, 1),
    ]

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

    # ── Institutional Intelligence Signals ──────────────────────────────────────
    institutional_signals = _get_institutional_signals(profile)
    confidence_label      = _get_confidence_label(ai_confidence, profile.is_verified)

    return render(request, 'companies/detail.html', {
        'company':               company,
        'profile':               profile,
        'score_cards':           score_cards,
        'path_actions':          path_actions,
        'videos':                videos,
        'roadmaps':              roadmaps,
        'active_roadmap':        active_roadmap,
        'has_roadmap':           has_roadmap,
        'financing_matches':     financing_matches,
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
        # Institutional Intelligence layer
        'institutional_signals':      institutional_signals,
        'confidence_label':           confidence_label,
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


def company_pdf_report(request, slug):
    """
    GET /companies/<slug>/report.pdf
    Generates a 3-page A4 WeasyPrint PDF intelligence report.
    """
    import weasyprint
    from datetime import date
    from django.template.loader import render_to_string
    from django.http import HttpResponse

    company = get_object_or_404(Company, slug=slug)
    profile = get_object_or_404(CompanyProfile, company=company,
                                status__in=('public', 'verified', 'draft'))

    score = float(profile.ecoiq_total_score or 0)

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

    base_url = request.build_absolute_uri('/')
    html_str  = render_to_string('companies/report_pdf.html', context, request=request)
    pdf_bytes = weasyprint.HTML(string=html_str, base_url=base_url).write_pdf()

    filename = f"ecoiq-report-{company.slug}.pdf"
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ── ML Insights endpoint ───────────────────────────────────────────────────────

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
        if pred is not None:
            payload['prediction'] = {
                'score_12m': round(pred, 1),
                'delta':     round(pred - float(company.ecoiq_score or 0), 1),
            }
    except Exception as exc:
        if not payload['error']:
            payload['error'] = f'prediction: {exc}'

    return JsonResponse(payload)


# ── Sector PDF Report ──────────────────────────────────────────────────────────

def sector_pdf_report(request, sector):
    """
    GET /companies/reports/sector/<sector>/
    Renders a horizontal bar-chart PDF for the top-20 companies in a sector.
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from io import BytesIO
    from django.http import HttpResponse

    qs = CompanyProfile.objects.filter(
        company__sector=sector
    ).select_related('company').order_by('-ecoiq_total_score')[:20]

    if not qs.exists():
        return HttpResponse('No data for this sector.', status=404)

    names  = [p.company.name[:20] for p in qs]
    scores = [float(p.ecoiq_total_score or 0) for p in qs]
    colors = ['#10b981' if s >= 70 else '#fbbf24' if s >= 50 else '#f87171' for s in scores]

    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, max(4, len(names) * 0.42)), facecolor='#070b0f')
    ax.set_facecolor('#0d1117')

    bars = ax.barh(names, scores, color=colors, height=0.6, edgecolor='none')

    # Sector average line
    avg = np.mean(scores)
    ax.axvline(x=avg, color='#00e89a', linestyle='--', linewidth=1, alpha=0.6,
               label=f'Avg {avg:.1f}')

    # Score labels on bars
    for bar, score in zip(bars, scores):
        ax.text(min(score + 1, 98), bar.get_y() + bar.get_height() / 2,
                f'{score:.1f}', va='center', ha='left',
                color='#94a3b8', fontsize=8, fontweight='600')

    ax.set_xlabel('EcoIQ Score', color='#475569', fontsize=10)
    ax.set_xlim(0, 105)
    ax.set_ylim(-0.6, len(names) - 0.4)
    ax.tick_params(colors='#475569', labelsize=8.5)
    ax.xaxis.label.set_color('#475569')
    ax.set_title(
        f'EcoIQ {sector.replace("_", " ").title()} Sector Intelligence Report',
        color='#e2e8f0', fontweight='300', fontsize=13, pad=14
    )
    ax.legend(loc='lower right', fontsize=8, framealpha=0.2)
    for spine in ax.spines.values():
        spine.set_color('#1e293b')

    # Watermark
    fig.text(0.99, 0.01, 'ecoiq.uk — Ethical Intelligence Platform',
             ha='right', va='bottom', color='#1e293b', fontsize=7)

    plt.tight_layout(pad=1.2)

    buf = BytesIO()
    fig.savefig(buf, format='pdf', facecolor='#070b0f', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)

    slug_sector = sector.replace(' ', '-').lower()
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ecoiq-{slug_sector}-sector-report.pdf"'
    return response
