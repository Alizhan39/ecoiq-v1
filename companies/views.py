"""
EcoIQ Company Intelligence — Public Views.

/companies/           → directory with search + filters
/companies/<slug>/    → full public company profile
"""
from django.shortcuts import render, get_object_or_404

from companies.models import CompanyProfile, CompanyGuidanceVideo, MORAL_LABEL_CHOICES
from companies.scoring import get_path_to_100_actions
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

    # Score evolution snapshots
    score_snapshots = list(profile.score_snapshots.order_by('date')[:8])

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
        # Intelligence layer
        'harm_signals':          harm_signals,
        'ai_confidence':         ai_confidence,
        'financing_eligibility': financing_eligibility,
        'radar_scores':          radar_scores,
    })
